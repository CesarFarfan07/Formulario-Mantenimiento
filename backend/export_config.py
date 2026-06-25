"""Export config tables from local DB to config_seed.json"""
import json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from app.database import SessionLocal
from app.models import (
    Turno, Nivel, Collaborator, Macroprocess,
    WorkType, Action, EquipmentCategory, EquipmentSubitem
)

CONFIG_FILE = os.path.join(os.path.dirname(__file__), "config_seed.json")

CONFIG_TABLES = [
    ("turnos", Turno, ["name", "position"]),
    ("niveles", Nivel, ["name", "position"]),
    ("colaboradores", Collaborator, ["group_name", "name", "position"]),
    ("macroprocesos", Macroprocess, ["group_key", "name", "position"]),
    ("tipos_trabajo", WorkType, ["type_key", "name", "default_action", "position"]),
    ("acciones", Action, ["group_key", "name", "position"]),
]

def export_config():
    db = SessionLocal()
    data = {}
    try:
        for name, model, fields in CONFIG_TABLES:
            rows = db.query(model).order_by(model.position).all()
            data[name] = [{f: getattr(r, f) for f in fields} for r in rows]

        # Equipment categories + subitems (special nested export)
        cats = db.query(EquipmentCategory).order_by(EquipmentCategory.position).all()
        data["equipos"] = []
        for cat in cats:
            entry = {"name": cat.name, "action_group": cat.action_group, "position": cat.position, "subitems": []}
            for sub in cat.subitems:
                entry["subitems"].append({"name": sub.name, "meters": sub.meters, "position": sub.position})
            data["equipos"].append(entry)

        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"[OK] Config exported to {CONFIG_FILE}")
        print(f"     {sum(len(v) for v in data.values())} total records")
    finally:
        db.close()

if __name__ == "__main__":
    export_config()
