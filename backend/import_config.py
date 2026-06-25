"""Import config_seed.json into the database (upsert)."""
import json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from app.database import SessionLocal
from app.models import (
    Turno, Nivel, Collaborator, Macroprocess,
    WorkType, Action, EquipmentCategory, EquipmentSubitem
)

CONFIG_FILE = os.path.join(os.path.dirname(__file__), "config_seed.json")

IMPORT_ORDER = [
    ("turnos", Turno, ["name", "position"], "name"),
    ("niveles", Nivel, ["name", "position"], "name"),
    ("colaboradores", Collaborator, ["group_name", "name", "position"], None),
    ("macroprocesos", Macroprocess, ["group_key", "name", "position"], None),
    ("tipos_trabajo", WorkType, ["type_key", "name", "default_action", "position"], None),
    ("acciones", Action, ["group_key", "name", "position"], None),
]

def _find_existing(db, model, row, unique_fields):
    """Find existing record by unique_fields or all fields."""
    if unique_fields:
        filters = {k: row[k] for k in unique_fields if k in row}
        if filters:
            return db.query(model).filter_by(**filters).first()
    # Fallback: match by all non-position fields
    others = {k: v for k, v in row.items() if k != "position"}
    return db.query(model).filter_by(**others).first()


def import_config():
    if not os.path.exists(CONFIG_FILE):
        print("[WARN] config_seed.json not found - skipping import")
        return

    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    db = SessionLocal()
    try:
        # Import flat tables first
        for name, model, fields, unique_on in IMPORT_ORDER:
            rows = data.get(name, [])
            for i, row in enumerate(rows):
                row["position"] = i
                existing = _find_existing(db, model, row, unique_on)
                if existing:
                    for f in fields:
                        setattr(existing, f, row.get(f, getattr(existing, f)))
                else:
                    db.add(model(**{f: row.get(f) for f in fields}))
            print(f"   {name}: {len(rows)} registros")

        # Import equipment categories + subitems (special nested)
        equipos = data.get("equipos", [])
        for i, cat_data in enumerate(equipos):
            existing_cat = db.query(EquipmentCategory).filter_by(name=cat_data["name"]).first()
            if existing_cat:
                existing_cat.action_group = cat_data.get("action_group", existing_cat.action_group)
                existing_cat.position = i
                cat = existing_cat
            else:
                cat = EquipmentCategory(
                    name=cat_data["name"],
                    action_group=cat_data.get("action_group", ""),
                    position=i,
                )
                db.add(cat)
                db.flush()

            # Upsert subitems
            existing_subs = {s.name: s for s in cat.subitems}
            for j, sub in enumerate(cat_data.get("subitems", [])):
                sub_name = sub["name"]
                if sub_name in existing_subs:
                    s = existing_subs[sub_name]
                    s.meters = sub.get("meters", s.meters)
                    s.position = j
                else:
                    db.add(EquipmentSubitem(
                        category_id=cat.id,
                        name=sub_name,
                        meters=sub.get("meters", "fin"),
                        position=j,
                    ))

        print(f"   equipos: {len(equipos)} categorias")
        db.commit()
        print("[OK] Config importado correctamente")
    except Exception as e:
        db.rollback()
        print(f"❌ Error importando config: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    import_config()
