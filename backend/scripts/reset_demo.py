"""Limpa as conversas de uma profissional, para gravar uma demonstração do zero.

Apaga os **contatos** dela e, em cascata, as conversas, mensagens,
alertas (com a trilha de eventos) e os pré-agendamentos nascidos nessas
conversas. Os eventos desses agendamentos na Google Agenda também são
apagados. A conta, o perfil, os documentos, a agenda conectada e os
agendamentos marcados pelo painel ficam como estão. O registro de custo
(`llm_usage`) também fica: o banco só zera o vínculo com a conversa.

Sem `--apagar`, só mostra o que seria apagado.

Uso (de dentro de backend/):
    python scripts/reset_demo.py camila            # só lista
    python scripts/reset_demo.py camila --apagar   # apaga de verdade
    python scripts/reset_demo.py camila --contato pedro --apagar   # só os contatos com "pedro" no nome

O primeiro argumento é parte do nome ou do slug da profissional; se
corresponder a mais de uma, o script para sem apagar nada.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import or_  # noqa: E402

from app import models  # noqa: E402
from app.database import SessionLocal  # noqa: E402
from app.services import calendar  # noqa: E402


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("profissional", help="parte do nome ou do slug")
    parser.add_argument("--contato", help="só os contatos com este trecho no nome")
    parser.add_argument("--apagar", action="store_true", help="apaga de verdade (sem isto, só lista)")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        pattern = f"%{args.profissional}%"
        found = (
            db.query(models.Professional)
            .filter(or_(models.Professional.name.ilike(pattern), models.Professional.slug.ilike(pattern)))
            .all()
        )
        if len(found) != 1:
            print(f"Esperava 1 profissional, achei {len(found)}: {[p.name for p in found]}. Nada foi apagado.")
            return
        prof = found[0]

        contacts = db.query(models.Contact).filter_by(professional_id=prof.id).all()
        if args.contato:
            # O nome é cifrado no banco, então o filtro é feito aqui.
            wanted = args.contato.casefold()
            contacts = [c for c in contacts if wanted in (c.display_name or "").casefold()]
        contact_ids = [c.id for c in contacts]
        conversations = db.query(models.Conversation).filter(models.Conversation.contact_id.in_(contact_ids)).all()
        conv_ids = [c.id for c in conversations]
        n_messages = db.query(models.Message).filter(models.Message.conversation_id.in_(conv_ids)).count()
        n_alerts = db.query(models.SafetyAlert).filter(models.SafetyAlert.conversation_id.in_(conv_ids)).count()
        appointments = db.query(models.Appointment).filter(models.Appointment.conversation_id.in_(conv_ids)).all()
        n_panel = (
            db.query(models.Appointment)
            .filter_by(professional_id=prof.id)
            .filter(models.Appointment.conversation_id.is_(None))
            .count()
        )

        print(f"Profissional: {prof.name} ({prof.slug})")
        print(f"  contatos:      {len(contacts)}")
        for c in contacts:
            print(f"    - {c.display_name or '(sem nome)'} [{c.channel}]")
        print(f"  conversas:     {len(conversations)}")
        print(f"  mensagens:     {n_messages}")
        print(f"  alertas:       {n_alerts}")
        print(f"  agendamentos das conversas: {len(appointments)}")
        for a in appointments:
            print(f"    - {a.starts_at:%d/%m %H:%M} {a.status} {'(com evento na agenda)' if a.calendar_event_id else ''}")
        print(f"  agendamentos do painel (ficam): {n_panel}")

        if not args.apagar:
            print("\nNada foi apagado. Rode de novo com --apagar para apagar.")
            return

        connection = db.query(models.CalendarConnection).filter_by(professional_id=prof.id).first()
        events_failed = 0
        for a in appointments:
            if connection and a.calendar_event_id:
                try:
                    calendar.delete_event(connection, a.calendar_event_id)
                except calendar.CalendarError:
                    events_failed += 1

        for c in contacts:
            db.delete(c)  # cascata: conversas → mensagens, alertas, agendamentos
        db.commit()
        print(f"\nApagados {len(contacts)} contato(s) e {len(conversations)} conversa(s).")
        if events_failed:
            print(f"{events_failed} evento(s) não saíram da Google Agenda; apague à mão.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
