"""A profissional está em consulta agora? Até quando?

Duas fontes, nesta ordem (decisão do Pedro, 03/11/2026):

1. **O botão "Em consulta"** do painel (`in_session_since`/`until`).
   Vale primeiro: é a profissional dizendo, e serve para sessão fora da
   agenda ou para estender.
2. **O Google Agenda**: um compromisso ocupado acontecendo agora deixa a
   profissional em consulta até o fim dele. Assim o recurso funciona sem
   ela lembrar de apertar o botão antes de cada sessão (no teste de
   03/11/2026 ela ligou o botão depois que as pessoas já tinham pedido).

Da agenda vem só livre/ocupado (`calendar.busy_intervals`), nunca o
título do evento. Bloco ocupado de `MAX_CALENDAR_BLOCK` ou mais (evento
de dia inteiro, férias) não conta como consulta: seria dizer "em
atendimento até amanhã".

Quem usa: a mensagem fixa do pedido para falar com a profissional
(`services/handoff.py`), o prompt da SelenIA (`services/llm.py`), os
avisos por e-mail, que ficam guardados até a consulta acabar
(`services/notifications.py`), e o painel.

A leitura da agenda fica em memória por `CACHE_SECONDS`: a conversa e o
painel perguntam isso várias vezes por minuto, e o Google não precisa
ser chamado a cada vez. Se o Google falhar, a resposta é "não está em
consulta": é melhor avisar a profissional na hora do que segurar um
aviso por engano.
"""

import logging
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timedelta

from app import models
from app.services import calendar

logger = logging.getLogger(__name__)

MAX_CALENDAR_BLOCK = timedelta(hours=12)
CACHE_SECONDS = 60

SOURCE_MANUAL = "manual"
SOURCE_AGENDA = "agenda"


@dataclass(frozen=True)
class Availability:
    in_session: bool
    # Fim previsto. Nulo com `in_session` = botão ligado "até eu desligar".
    until: datetime | None = None
    source: str | None = None


NOT_IN_SESSION = Availability(False)

_cache: dict[str, tuple[float, list[tuple[datetime, datetime]]]] = {}
_cache_lock = threading.Lock()


def clear_cache() -> None:
    with _cache_lock:
        _cache.clear()


def _busy_around(professional: models.Professional, now: datetime) -> list[tuple[datetime, datetime]]:
    connection = professional.calendar_connection
    if connection is None:
        return []
    with _cache_lock:
        hit = _cache.get(professional.id)
    if hit and time.monotonic() - hit[0] < CACHE_SECONDS:
        return hit[1]
    try:
        busy = calendar.busy_intervals(connection, now - MAX_CALENDAR_BLOCK, now + MAX_CALENDAR_BLOCK)
    except calendar.CalendarError:
        # Guarda a falha também, para não chamar o Google a cada mensagem
        # enquanto ele estiver fora.
        logger.warning("agenda indisponível ao conferir se a profissional está em consulta")
        busy = []
    with _cache_lock:
        _cache[professional.id] = (time.monotonic(), busy)
    return busy


def session_end_from_busy(busy: list[tuple[datetime, datetime]], now: datetime) -> datetime | None:
    """Fim da consulta em andamento segundo a agenda, ou None.

    Sessões coladas (uma começa quando a outra acaba) contam como uma só:
    a profissional só fica livre no fim da última.
    """
    blocks = [(start, end) for start, end in busy if end - start < MAX_CALENDAR_BLOCK]
    current = [end for start, end in blocks if start <= now < end]
    if not current:
        return None
    until = max(current)
    extended = True
    while extended:
        extended = False
        for start, end in blocks:
            if start <= until < end:
                until, extended = end, True
    return until


def current(professional: models.Professional, now: datetime | None = None) -> Availability:
    now = now or models._now()
    if professional.is_in_session:
        return Availability(True, professional.in_session_until, SOURCE_MANUAL)
    until = session_end_from_busy(_busy_around(professional, now), now)
    if until is not None:
        return Availability(True, until, SOURCE_AGENDA)
    return NOT_IN_SESSION


def format_until(until: datetime) -> str:
    """"22:19", no fuso da agenda."""
    return until.astimezone(calendar._tz()).strftime("%H:%M")
