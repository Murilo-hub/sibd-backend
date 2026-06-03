"""
migrate.py
──────────────────────────────────────────────────────────────────────────────
Script utilitário para rodar as migrations do Alembic.
Usado pelo Render no start command antes de subir o servidor.

Uso:
  python migrate.py              → aplica todas as migrations pendentes
  python migrate.py downgrade    → reverte a última migration
──────────────────────────────────────────────────────────────────────────────
"""
import sys
from alembic.config import Config
from alembic import command

def main():
    alembic_cfg = Config("alembic.ini")   # lê as configurações do alembic.ini

    action = sys.argv[1] if len(sys.argv) > 1 else "upgrade"

    if action == "upgrade":
        print("Aplicando migrations...")
        command.upgrade(alembic_cfg, "head")   # aplica tudo até a última versão
        print("Migrations aplicadas com sucesso.")

    elif action == "downgrade":
        print("Revertendo última migration...")
        command.downgrade(alembic_cfg, "-1")   # reverte uma migration
        print("Downgrade concluído.")

    elif action == "current":
        command.current(alembic_cfg)   # mostra a versão atual do banco

    elif action == "history":
        command.history(alembic_cfg)   # lista todas as migrations

    else:
        print(f"Ação desconhecida: {action}")
        sys.exit(1)

if __name__ == "__main__":
    main()
