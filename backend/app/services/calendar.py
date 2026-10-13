"""Google Agenda da profissional: conexão e horários livres.

Como funciona:

1. Na tela Agenda, "Sincronizar com o Google Agenda" abre a janela de
   permissão do Google (no navegador). Ela devolve um código de uso
   único, que o painel manda para `POST /calendar/{slug}/connect`.
2. `connect` troca o código, com o segredo do cliente OAuth, por um
   código de longa duração (`refresh_token`), que fica cifrado em
   `CalendarConnection`. Com ele a SelenIA consulta a agenda mesmo com a
   profissional fora do painel.
3. Para **ler**, a permissão é só livre/ocupado (`calendar.freebusy`):
   a SelenIA vê os intervalos ocupados da agenda principal, nunca o
   título, a descrição ou os convidados de um evento, que podem ter
   nome de paciente. Para **reservar**, pede também `calendar.events`,
   usada só para criar, atualizar e apagar os eventos que ela mesma
   cria (`services/appointments.py`). Sem ela, a SelenIA só consulta.
4. `free_slots` cruza o horário de atendimento (`working_hours`), a
   duração da sessão e os intervalos ocupados. A SelenIA consulta isso
   por uma ferramenta, só quando a conversa pede horário
   (`describe_for_assistant`, usado em `services/pipeline.py`).

A reserva e a aprovação ficam em `services/appointments.py`.
"""

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

import requests
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from sqlalchemy.orm import Session

from app import models
from app.config import settings

SCOPE_FREEBUSY = "https://www.googleapis.com/auth/calendar.freebusy"
SCOPE_EVENTS = "https://www.googleapis.com/auth/calendar.events"
# `openid email` só para saber qual conta deu a permissão.
REQUESTED_SCOPES = f"openid email {SCOPE_FREEBUSY} {SCOPE_EVENTS}"

_TOKEN_URL = "https://oauth2.googleapis.com/token"
_REVOKE_URL = "https://oauth2.googleapis.com/revoke"
_FREEBUSY_URL = "https://www.googleapis.com/calendar/v3/freeBusy"
_EVENTS_URL = "https://www.googleapis.com/calendar/v3/calendars/primary/events"
_TIMEOUT = 10
# Folga para o relógio desta máquina estar alguns segundos atrás do
# Google: sem ela, um token recém-emitido é recusado como "do futuro".
GOOGLE_CLOCK_SKEW_SECONDS = 30

WEEKDAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
WEEKDAY_NAMES = ("segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo")

# Até onde olhar, a antecedência mínima e a grade dos inícios. A SelenIA
# recebe todos os horários livres e oferece no máximo 3 de cada vez,
# procurando na lista o que a pessoa pedir ("tem de manhã?", "e na quinta?").
HORIZON_DAYS = 14
MIN_NOTICE = timedelta(hours=12)
SLOT_STEP_MINUTES = 30


class CalendarError(Exception):
    """Falha ao falar com o Google. A mensagem pode ir para a tela."""


def _tz() -> ZoneInfo:
    return ZoneInfo(settings.agenda_timezone)


# ---------------------------------------------------------------------------
# Conexão
# ---------------------------------------------------------------------------


def is_configured() -> bool:
    return bool(settings.google_client_id and settings.google_client_secret)


def _exchange_code(code: str) -> dict:
    try:
        response = requests.post(
            _TOKEN_URL,
            data={
                "code": code,
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                # Valor fixo do fluxo em janela (popup) do Google.
                "redirect_uri": "postmessage",
                "grant_type": "authorization_code",
            },
            timeout=_TIMEOUT,
        )
    except requests.RequestException:
        raise CalendarError("Não foi possível falar com o Google. Tente de novo.")
    if response.status_code != 200:
        raise CalendarError("O Google não aceitou a permissão. Tente sincronizar de novo.")
    return response.json()


def connect(db: Session, professional: models.Professional, code: str) -> models.CalendarConnection:
    if not is_configured():
        raise CalendarError("A agenda ainda não foi configurada no servidor (GOOGLE_CLIENT_SECRET).")
    tokens = _exchange_code(code)

    granted = set(tokens.get("scope", "").split())
    if SCOPE_FREEBUSY not in granted:
        # Na janela do Google dá para desmarcar a permissão da agenda.
        raise CalendarError("Para a SelenIA ver seus horários livres, marque a permissão da agenda na janela do Google.")
    try:
        claims = id_token.verify_oauth2_token(
            tokens.get("id_token", ""),
            google_requests.Request(),
            settings.google_client_id,
            clock_skew_in_seconds=GOOGLE_CLOCK_SKEW_SECONDS,
        )
    except ValueError:
        raise CalendarError("Não foi possível confirmar a conta Google da agenda.")
    email = claims.get("email", "").lower()

    connection = professional.calendar_connection
    same_account = connection is not None and connection.google_email == email
    refresh_token = tokens.get("refresh_token")
    if not refresh_token and same_account:
        # Reconexão da mesma conta (ex.: para liberar a reserva): o Google
        # nem sempre manda um código novo, e o antigo passa a valer com
        # as permissões novas.
        refresh_token = connection.refresh_token
    if not refresh_token:
        # O Google só manda o código de longa duração na primeira
        # permissão. Se já havia uma antiga, ela precisa ser removida.
        raise CalendarError(
            "O Google não enviou o acesso completo. Remova a SelenIA em "
            "myaccount.google.com/permissions e sincronize de novo."
        )

    if connection is None:
        connection = models.CalendarConnection(professional=professional)
        db.add(connection)
    elif connection.refresh_token != refresh_token and not same_account:
        # Troca de conta: a permissão antiga deixa de valer no Google também.
        _revoke(connection.refresh_token)
    connection.google_email = email
    connection.refresh_token = refresh_token
    connection.scopes = " ".join(sorted(granted))
    connection.connected_at = models._now()
    db.commit()
    db.refresh(connection)
    return connection


def disconnect(db: Session, professional: models.Professional) -> None:
    connection = professional.calendar_connection
    if connection is None:
        return
    _revoke(connection.refresh_token)
    db.delete(connection)
    db.commit()


def _revoke(refresh_token: str) -> None:
    """Retira a permissão no Google. Se falhar, a conexão sai do banco
    mesmo assim: sem o código guardado, a SelenIA já não tem acesso."""
    try:
        requests.post(_REVOKE_URL, data={"token": refresh_token}, timeout=_TIMEOUT)
    except requests.RequestException:
        pass


def _access_token(connection: models.CalendarConnection) -> str:
    try:
        response = requests.post(
            _TOKEN_URL,
            data={
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "refresh_token": connection.refresh_token,
                "grant_type": "refresh_token",
            },
            timeout=_TIMEOUT,
        )
    except requests.RequestException:
        raise CalendarError("Não foi possível falar com o Google agora.")
    if response.status_code != 200:
        raise CalendarError("A permissão da agenda não vale mais. Sincronize com o Google Agenda de novo.")
    return response.json()["access_token"]


def busy_intervals(connection: models.CalendarConnection, start: datetime, end: datetime) -> list[tuple[datetime, datetime]]:
    """Intervalos ocupados da agenda principal. Só horários, sem detalhes."""
    try:
        response = requests.post(
            _FREEBUSY_URL,
            headers={"Authorization": f"Bearer {_access_token(connection)}"},
            json={"timeMin": start.isoformat(), "timeMax": end.isoformat(), "items": [{"id": "primary"}]},
            timeout=_TIMEOUT,
        )
    except requests.RequestException:
        raise CalendarError("Não foi possível ler a agenda agora.")
    if response.status_code != 200:
        raise CalendarError("Não foi possível ler a agenda agora.")
    calendar = response.json().get("calendars", {}).get("primary", {})
    if calendar.get("errors"):
        raise CalendarError("Não foi possível ler a agenda agora.")
    return [
        (datetime.fromisoformat(b["start"].replace("Z", "+00:00")), datetime.fromisoformat(b["end"].replace("Z", "+00:00")))
        for b in calendar.get("busy", [])
    ]


def _events_call(connection: models.CalendarConnection, method: str, url: str, body: dict | None = None) -> dict:
    try:
        response = requests.request(
            method,
            url,
            headers={"Authorization": f"Bearer {_access_token(connection)}"},
            json=body,
            timeout=_TIMEOUT,
        )
    except requests.RequestException:
        raise CalendarError("Não foi possível falar com o Google Agenda agora.")
    if method == "DELETE" and response.status_code in (404, 410):
        return {}  # já tinha sido apagado na agenda
    if response.status_code in (404, 410):
        raise CalendarError("O evento não existe mais no Google Agenda.")
    if response.status_code == 403:
        raise CalendarError("A SelenIA não tem permissão para mexer na agenda. Reconecte o Google Agenda.")
    if response.status_code >= 300:
        raise CalendarError("O Google Agenda recusou a alteração agora. Tente de novo.")
    return response.json() if response.content else {}


def create_event(connection: models.CalendarConnection, body: dict) -> str:
    return _events_call(connection, "POST", _EVENTS_URL, body)["id"]


def update_event(connection: models.CalendarConnection, event_id: str, body: dict) -> None:
    _events_call(connection, "PATCH", f"{_EVENTS_URL}/{event_id}", body)


def delete_event(connection: models.CalendarConnection, event_id: str) -> None:
    _events_call(connection, "DELETE", f"{_EVENTS_URL}/{event_id}")


def list_events(connection: models.CalendarConnection, start: datetime, end: datetime) -> list[dict]:
    """Eventos da agenda principal entre `start` e `end`, para o calendário
    do painel. Só a profissional vê: nada é gravado nem vai para a SelenIA.

    Devolve dicionários com id, título, início, fim e se é de dia inteiro.
    """
    params = (
        f"?timeMin={start.isoformat().replace('+', '%2B')}&timeMax={end.isoformat().replace('+', '%2B')}"
        "&singleEvents=true&orderBy=startTime&maxResults=250"
    )
    data = _events_call(connection, "GET", _EVENTS_URL + params)
    tz = _tz()
    events = []
    for item in data.get("items", []):
        if item.get("status") == "cancelled":
            continue
        start_info, end_info = item.get("start", {}), item.get("end", {})
        if "dateTime" in start_info:
            starts = datetime.fromisoformat(start_info["dateTime"].replace("Z", "+00:00"))
            ends = datetime.fromisoformat(end_info["dateTime"].replace("Z", "+00:00"))
            all_day = False
        else:
            starts = datetime.combine(date.fromisoformat(start_info["date"]), time(0), tzinfo=tz)
            ends = datetime.combine(date.fromisoformat(end_info["date"]), time(0), tzinfo=tz)
            all_day = True
        events.append(
            {
                "id": item["id"],
                "title": item.get("summary") or "(sem título)",
                "starts_at": starts,
                "ends_at": ends,
                "all_day": all_day,
                # Evento marcado como "livre" no Google não ocupa horário.
                "busy": item.get("transparency") != "transparent",
            }
        )
    return events


# ---------------------------------------------------------------------------
# Horários livres
# ---------------------------------------------------------------------------


def _parse_time(value: str) -> time:
    hours, minutes = value.split(":")
    return time(int(hours), int(minutes))


def free_slots(
    working_hours: dict | None,
    session_minutes: int,
    busy: list[tuple[datetime, datetime]],
    now: datetime,
    tz: ZoneInfo,
    days: int = HORIZON_DAYS,
    booked_per_day: dict[date, int] | None = None,
    max_per_day: int | None = None,
) -> list[datetime]:
    """Todos os inícios de sessão livres, dentro do horário de atendimento.

    Um horário vale se começa na grade de 30 minutos, a sessão inteira
    cabe no intervalo de atendimento do dia, começa com pelo menos
    `MIN_NOTICE` de antecedência e não encosta em nada ocupado da agenda.
    Dias que já têm `max_per_day` sessões (`booked_per_day`) ficam de fora.
    """
    duration = timedelta(minutes=session_minutes)
    step = timedelta(minutes=SLOT_STEP_MINUTES)
    earliest = now + MIN_NOTICE
    today = now.astimezone(tz).date()

    result = []
    for offset in range(days + 1):
        day: date = today + timedelta(days=offset)
        if max_per_day and (booked_per_day or {}).get(day, 0) >= max_per_day:
            continue
        for interval in (working_hours or {}).get(WEEKDAYS[day.weekday()], []):
            start = datetime.combine(day, _parse_time(interval["start"]), tzinfo=tz)
            end = datetime.combine(day, _parse_time(interval["end"]), tzinfo=tz)
            slot = start
            while slot + duration <= end:
                slot_end = slot + duration
                if slot >= earliest and not any(b0 < slot_end and slot < b1 for b0, b1 in busy):
                    result.append(slot)
                slot += step
    return result


def _holds(appointment: models.Appointment, now: datetime) -> bool:
    """Confirmado, ou provisório ainda no prazo de 24h."""
    if appointment.status == models.AppointmentStatus.CONFIRMED:
        return True
    return (
        appointment.status == models.AppointmentStatus.TENTATIVE
        and appointment.expires_at is not None
        and appointment.expires_at > now
    )


def sessions_per_day(professional: models.Professional, now: datetime) -> dict[date, int]:
    """Sessões que já ocupam cada dia (pedidos no prazo, confirmadas e as
    marcadas pelo painel), para o limite por dia."""
    tz = _tz()
    counts: dict[date, int] = {}
    for a in professional.appointments:
        if _holds(a, now):
            day = a.starts_at.astimezone(tz).date()
            counts[day] = counts.get(day, 0) + 1
    return counts


def has_events_permission(professional: models.Professional) -> bool:
    """A conexão tem a permissão de criar eventos (independe do horário)."""
    connection = professional.calendar_connection
    return connection is not None and SCOPE_EVENTS in (connection.scopes or "").split()


def can_book(professional: models.Professional) -> bool:
    """Pronta para consultar e com a permissão de criar eventos."""
    return is_ready(professional) and has_events_permission(professional)


def is_ready(professional: models.Professional) -> bool:
    """A SelenIA só consulta a agenda com tudo o que precisa para isso."""
    return bool(
        professional.calendar_connection
        and professional.session_minutes
        and any((professional.working_hours or {}).values())
    )


def available_slots(professional: models.Professional, now: datetime | None = None) -> list[datetime]:
    """Horários livres de verdade (lendo o Google). Levanta `CalendarError`."""
    if not is_ready(professional):
        raise CalendarError("Conecte a agenda e preencha o horário de atendimento.")
    now = now or models._now()
    busy = busy_intervals(professional.calendar_connection, now, now + timedelta(days=HORIZON_DAYS + 1))
    # Os pedidos da SelenIA também ocupam, mesmo antes de o Google refletir.
    busy = busy + [(a.starts_at, a.ends_at) for a in professional.appointments if _holds(a, now)]
    return free_slots(
        professional.working_hours,
        professional.session_minutes,
        busy,
        now,
        _tz(),
        booked_per_day=sessions_per_day(professional, now),
        max_per_day=professional.max_sessions_per_day,
    )


def group_by_day(slots: list[datetime]) -> list[tuple[date, list[datetime]]]:
    tz = _tz()
    days: dict[date, list[datetime]] = {}
    for slot in slots:
        days.setdefault(slot.astimezone(tz).date(), []).append(slot)
    return list(days.items())


# ---------------------------------------------------------------------------
# Textos para a SelenIA
# ---------------------------------------------------------------------------


def format_slot(slot: datetime) -> str:
    local = slot.astimezone(_tz())
    return f"{WEEKDAY_NAMES[local.weekday()]}, {local:%d/%m} às {local:%H:%M}"


def slot_code(slot: datetime) -> str:
    """Código do horário que a SelenIA devolve para reservar (2026-09-29T10:00)."""
    return slot.astimezone(_tz()).strftime("%Y-%m-%dT%H:%M")


def parse_slot_code(code: str) -> datetime | None:
    try:
        return datetime.strptime(code.strip(), "%Y-%m-%dT%H:%M").replace(tzinfo=_tz())
    except (ValueError, AttributeError):
        return None


def working_hours_text(working_hours: dict | None) -> str:
    """"segunda: 10:00 às 16:00" por linha; vazio se não preenchido."""
    lines = []
    for key, name in zip(WEEKDAYS, WEEKDAY_NAMES):
        intervals = (working_hours or {}).get(key) or []
        if intervals:
            ranges = " e ".join(f"{i['start']} às {i['end']}" for i in intervals)
            lines.append(f"- {name}: {ranges}")
    return "\n".join(lines)


def describe_for_assistant(
    professional: models.Professional, now: datetime | None = None, pending: str | None = None
) -> str:
    """Resposta da ferramenta de horários: data de hoje e os horários livres.

    Nunca levanta exceção: se o Google falhar, diz isso, e a SelenIA
    responde que vai confirmar com a profissional.
    """
    now = now or models._now()
    local_now = now.astimezone(_tz())
    today = f"Agora é {WEEKDAY_NAMES[local_now.weekday()]}, {local_now:%d/%m/%Y}, {local_now:%H:%M}."
    if pending:
        today += f"\n{pending}"
    try:
        slots = available_slots(professional, now)
    except CalendarError:
        return f"{today}\nNão foi possível consultar a agenda agora. Não ofereça horários: diga que vai confirmar com {professional.name}."
    if not slots:
        return f"{today}\nNenhum horário livre nos próximos {HORIZON_DAYS} dias."
    lines = []
    for day, day_slots in group_by_day(slots):
        times = ", ".join(f"{slot.astimezone(_tz()):%H:%M}" for slot in day_slots)
        lines.append(f"- {WEEKDAY_NAMES[day.weekday()]}, {day:%d/%m} ({day:%Y-%m-%d}): {times}")
    header = (
        f"{today}\nHorários livres para começar uma sessão de {professional.session_minutes} minutos, "
        f"nos próximos {HORIZON_DAYS} dias:"
    )
    if can_book(professional):
        # O código de `pedir_agendamento` junta a data entre parênteses e
        # o horário: 2026-09-29 + 10:00 = 2026-09-29T10:00.
        header += " (para reservar, o código é a data entre parênteses, a letra T e o horário, ex.: 2026-09-29T10:00)"
    return header + "\n" + "\n".join(lines)
