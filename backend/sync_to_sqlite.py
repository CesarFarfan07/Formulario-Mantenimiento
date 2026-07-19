"""Sync PostgreSQL -> SQLite for local backup."""
import sys
import os
import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, text, MetaData
from app.core.config import settings
from app.core.database import Base
import app.models  # noqa: register models on Base.metadata

PG_URL = settings.database_url
SQLITE_URL = "sqlite:///./mantenimiento.db"

TABLES = [
    "workers", "reports", "job_entries", "job_images",
    "equipment_categories", "equipment_subitems",
    "collaborators", "macroprocesses", "work_types",
    "actions", "niveles", "turnos",
    "racs_reports", "guardias", "worker_guardias", "racs_workers",
]


def _serialize(val):
    """Convert non-serializable types (time, date, datetime, etc.) to string."""
    if isinstance(val, (datetime.time, datetime.date, datetime.datetime)):
        return val.isoformat()
    if isinstance(val, bytes):
        return val.decode("utf-8", errors="replace")
    return val


def sync():
    pg_engine = create_engine(PG_URL)
    sqlite_engine = create_engine(SQLITE_URL)

    Base.metadata.create_all(bind=sqlite_engine)

    meta = MetaData()
    meta.reflect(bind=pg_engine)

    with pg_engine.connect() as pg_conn, sqlite_engine.connect() as sqlite_conn:
        trans = sqlite_conn.begin()
        try:
            sqlite_conn.execute(text("PRAGMA foreign_keys = OFF"))

            for table_name in TABLES:
                table = meta.tables.get(table_name)
                if table is None:
                    print(f"  ATENCION: Tabla '{table_name}' no existe en PostgreSQL, saltando")
                    continue

                sqlite_conn.execute(text(f"DELETE FROM {table_name}"))

                rows = pg_conn.execute(table.select()).mappings().all()
                if not rows:
                    print(f"  {table_name}: 0 filas")
                    continue

                columns = list(rows[0].keys())
                placeholders = ", ".join([f":{c}" for c in columns])
                cols_str = ", ".join(columns)
                stmt = text(f"INSERT INTO {table_name} ({cols_str}) VALUES ({placeholders})")

                serialized = [{k: _serialize(v) for k, v in dict(r).items()} for r in rows]
                sqlite_conn.execute(stmt, serialized)
                print(f"  {table_name}: {len(rows)} filas copiadas")

            sqlite_conn.execute(text("PRAGMA foreign_keys = ON"))
            trans.commit()
            print("\nSincronizacion completada.")

        except Exception as e:
            trans.rollback()
            print(f"\nERROR durante sincronizacion: {e}")
            raise


if __name__ == "__main__":
    print("Sincronizando PostgreSQL -> SQLite...")
    sync()
    print("\nNota: Las imagenes (fotos) no se copian porque son archivos en disco.")
