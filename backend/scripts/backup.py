"""Backup do banco e teste de restauração.

Fazer o backup (arquivo em `backend/backups/`, fora do git):
    python scripts/backup.py

Testar a restauração de um backup, numa base separada:
    python scripts/backup.py --restaurar backups/maria-AAAAMMDD-HHMM.dump

A restauração **nunca** escreve na base de verdade: cria (ou recria) a
base `<nome>_restauracao`, restaura o arquivo nela e compara a contagem
de linhas de cada tabela com a base original. Se tudo bater, o backup
serve. A base de teste pode ser apagada depois.

O conteúdo das mensagens e os dados de contato já estão cifrados no
banco, então continuam cifrados no arquivo; a chave
(`DATA_ENCRYPTION_KEY`) fica no `.env` e não vai no backup. Quem
restaurar precisa da mesma chave para ler as conversas. Guarde os dois
em lugares diferentes.

Usa o `pg_dump`/`pg_restore` da máquina se estiverem instalados; se não,
os do contêiner `postgres` do `docker-compose.yml`.
"""

import argparse
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
REPO = BACKEND.parent
sys.path.insert(0, str(BACKEND))

from sqlalchemy import create_engine, text  # noqa: E402
from sqlalchemy.engine import make_url  # noqa: E402

from app.config import settings  # noqa: E402

BACKUP_DIR = BACKEND / "backups"


def _pg(tool: str, url, args: list[str]) -> list[str]:
    """Comando de uma ferramenta do Postgres, local ou no contêiner."""
    if shutil.which(tool):
        return [tool, f"--dbname={url.render_as_string(hide_password=False)}", *args]
    return ["docker", "compose", "exec", "-T", "postgres", tool, "-U", url.username, f"--dbname={url.database}", *args]


def make_backup() -> Path:
    url = make_url(settings.database_url)
    BACKUP_DIR.mkdir(exist_ok=True)
    target = BACKUP_DIR / f"maria-{datetime.now():%Y%m%d-%H%M}.dump"
    with target.open("wb") as out:
        result = subprocess.run(_pg("pg_dump", url, ["--format=custom", "--no-owner"]), stdout=out, cwd=REPO)
    if result.returncode != 0 or target.stat().st_size == 0:
        target.unlink(missing_ok=True)
        sys.exit("Falha no pg_dump. O Postgres está rodando?")
    print(f"Backup feito: {target} ({target.stat().st_size / 1024:.0f} KB)")
    return target


def _counts(url) -> dict[str, int]:
    engine = create_engine(url)
    with engine.connect() as conn:
        tables = conn.execute(
            text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY 1")
        ).scalars()
        counts = {t: conn.execute(text(f'SELECT count(*) FROM "{t}"')).scalar() for t in list(tables)}
    engine.dispose()
    return counts


def test_restore(dump: Path) -> None:
    source = make_url(settings.database_url)
    restored = source.set(database=f"{source.database}_restauracao")
    if restored.database == source.database:
        sys.exit("A base de teste não pode ser a de verdade.")

    admin = create_engine(source.set(database="postgres"), isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        conn.execute(text(f'DROP DATABASE IF EXISTS "{restored.database}"'))
        conn.execute(text(f'CREATE DATABASE "{restored.database}"'))
    admin.dispose()

    with dump.open("rb") as data:
        result = subprocess.run(_pg("pg_restore", restored, ["--no-owner", "--exit-on-error"]), stdin=data, cwd=REPO)
    if result.returncode != 0:
        sys.exit("Falha no pg_restore: o backup não serve.")

    original, copy = _counts(source), _counts(restored)
    print(f"Restaurado em {restored.database}. Linhas por tabela (original x restaurado):")
    ok = True
    for table in sorted(set(original) | set(copy)):
        a, b = original.get(table), copy.get(table)
        mark = "ok" if a == b else "DIFERENTE"
        ok &= a == b
        print(f"  {table:28} {a!s:>6} x {b!s:<6} {mark}")
    if ok:
        print("Restauração conferida: todas as tabelas batem.")
    else:
        print("Há diferença. Se o sistema recebeu mensagens depois do backup, é esperado; senão, o backup falhou.")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Backup do banco e teste de restauração.")
    parser.add_argument("--restaurar", type=Path, help="arquivo .dump para testar a restauração")
    args = parser.parse_args()
    if args.restaurar:
        test_restore(args.restaurar)
    else:
        make_backup()


if __name__ == "__main__":
    main()
