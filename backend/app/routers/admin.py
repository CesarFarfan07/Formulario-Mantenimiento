"""Admin router — page, CRUD for config entities, password verification."""
import os, json
from fastapi import APIRouter, Depends, HTTPException, Body, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import Optional

from ..core.database import get_db, Base, SessionLocal, engine
from ..core.config import settings, BASE_DIR
from ..models import (
    Worker, Report, JobEntry, EquipmentCategory, EquipmentSubitem,
    Collaborator, Macroprocess, WorkType, Action, Turno, Nivel,
    RacsReport, Guardia, WorkerGuardia, RacsWorker,
)
from ..services.racs_service import get_racs_period, is_guardia_on_site, get_all_workers, get_worker_guardias

TEMPLATE_DIR = os.path.join(BASE_DIR, "app", "templates")
templates = Jinja2Templates(directory=TEMPLATE_DIR)

router = APIRouter(tags=["Admin"])

ENTITY_MAP = {
    "turnos": Turno, "niveles": Nivel, "colaboradores": Collaborator,
    "macroprocesos": Macroprocess, "tipos_trabajo": WorkType, "acciones": Action,
    "equipos": EquipmentCategory, "trabajadores": Worker,
}


@router.get("/admin", response_class=HTMLResponse)
def admin_page(request: Request):
    return templates.TemplateResponse("admin.html", {"request": request})


@router.post("/api/admin/verify")
def admin_verify(data: dict = Body(...)):
    if data.get("password") == settings.admin_password:
        return {"ok": True}
    raise HTTPException(401, "Contraseña incorrecta")


# ─── Generic CRUD helpers ──────────────────────────────────────────


def _model_from_entity(entity: str):
    model = ENTITY_MAP.get(entity)
    if not model:
        raise HTTPException(400, f"Entidad desconocida: {entity}")
    return model


# ─── GET /api/admin/{entity} — List all ────────────────────────────


@router.get("/api/admin/{entity}")
def admin_list(entity: str, db: Session = Depends(get_db)):
    model = _model_from_entity(entity)
    rows = db.query(model).order_by(model.id).all()
    data = []
    for r in rows:
        d = {c.name: getattr(r, c.name) for c in r.__table__.columns}
        if entity == "equipos":
            d["subitems"] = [
                {"id": si.id, "name": si.name, "meters": si.meters, "position": si.position}
                for si in r.subitems
            ]
        data.append(d)
    if entity == "colaboradores":
        racs_workers = db.query(RacsWorker).filter(RacsWorker.active == True, RacsWorker.group_name.in_(["Trackless", "Convencional", "Electrico"])).order_by(RacsWorker.name).all()
        existing_names = {(d["name"], d.get("group_name", "")) for d in data}
        for rw in racs_workers:
            if (rw.name, rw.group_name) not in existing_names:
                data.append({
                    "id": f"racs_{rw.id}",
                    "name": rw.name,
                    "group_name": rw.group_name,
                    "cargo": rw.cargo or "",
                    "position": 999,
                })
    return data


# ─── POST /api/admin/{entity} — Create ─────────────────────────────


@router.post("/api/admin/{entity}")
def admin_create(entity: str, data: dict = Body(...), db: Session = Depends(get_db)):
    model = _model_from_entity(entity)
    subitems_data = data.pop("subitems", None)
    obj = model(**data)
    db.add(obj)
    if subitems_data and entity == "equipos":
        db.flush()
        for si_data in subitems_data:
            if si_data.get("name", "").strip():
                db.add(EquipmentSubitem(
                    category_id=obj.id, name=si_data["name"],
                    meters=si_data.get("meters", "fin"), position=si_data.get("position", 0),
                ))
    db.commit()
    db.refresh(obj)
    return {"ok": True, "id": obj.id}


# ─── PUT /api/admin/{entity}/{id} — Update ─────────────────────────


@router.put("/api/admin/{entity}/{item_id}")
def admin_update(entity: str, item_id: int, data: dict = Body(...), db: Session = Depends(get_db)):
    model = _model_from_entity(entity)
    obj = db.query(model).filter(model.id == item_id).first()
    if not obj:
        raise HTTPException(404)
    subitems_data = data.pop("subitems", None)
    for k, v in data.items():
        if hasattr(obj, k):
            setattr(obj, k, v)
    if subitems_data is not None and entity == "equipos":
        db.query(EquipmentSubitem).filter(EquipmentSubitem.category_id == item_id).delete()
        for si_data in subitems_data:
            if si_data.get("name", "").strip():
                db.add(EquipmentSubitem(
                    category_id=item_id, name=si_data["name"],
                    meters=si_data.get("meters", "fin"), position=si_data.get("position", 0),
                ))
    db.commit()
    return {"ok": True}


# ─── DELETE /api/admin/{entity}/{id} — Delete ──────────────────────


@router.delete("/api/admin/{entity}/{item_id}")
def admin_delete(entity: str, item_id: int, db: Session = Depends(get_db)):
    model = _model_from_entity(entity)
    obj = db.query(model).filter(model.id == item_id).first()
    if not obj:
        raise HTTPException(404)
    db.delete(obj)
    db.commit()
    return {"ok": True}


# ─── PUT /api/admin/{entity}/reorder/{id} — Reorder ────────────────


@router.put("/api/admin/{entity}/reorder/{item_id}")
def admin_reorder(entity: str, item_id: int, direction: str = Query("up"), db: Session = Depends(get_db)):
    model = _model_from_entity(entity)
    obj = db.query(model).filter(model.id == item_id).first()
    if not obj:
        raise HTTPException(404)
    rows = db.query(model).order_by(model.position).all()
    idx = next((i for i, r in enumerate(rows) if r.id == obj.id), -1)
    swap_idx = idx - 1 if direction == "up" else idx + 1
    if 0 <= swap_idx < len(rows):
        rows[idx].position, rows[swap_idx].position = rows[swap_idx].position, rows[idx].position
        db.commit()
    return {"ok": True}
