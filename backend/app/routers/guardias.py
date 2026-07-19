"""Guardia CRUD router — phase dates, worker assignments."""
from datetime import date as _dd
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from ..core.database import get_db
from ..models import Guardia, WorkerGuardia, RacsWorker
from ..services.racs_service import get_worker_guardias, get_worker_cargos, get_all_workers

router = APIRouter(tags=["Guardias"])


@router.get("/api/guardias")
def guardia_list(db: Session = Depends(get_db)):
    guardias = db.query(Guardia).order_by(Guardia.id).all()
    wg = get_worker_guardias(db)
    cargos = get_worker_cargos(db)
    all_workers = get_all_workers(db)
    teams_dict = {}
    for w in all_workers:
        teams_dict.setdefault(w["group_name"], []).append(w["name"])
    workers = [
        {"group": g, "workers": [{"name": w, "guardia": wg.get((w, g), ""), "cargo": cargos.get((w, g), "")} for w in names]}
        for g, names in teams_dict.items()
    ]
    return {
        "guardias": [{"id": g.id, "name": g.name, "phase_start": g.phase_start.isoformat()} for g in guardias],
        "workers": workers,
    }


@router.post("/api/guardias/update")
def guardia_update(data: dict = Body(...), db: Session = Depends(get_db)):
    """Update guardia phase_start or worker guardia assignment. Protected by DNI."""
    action = data.get("action")
    if action == "update_phase":
        g = db.query(Guardia).filter(Guardia.name == data["guardia"]).first()
        if g:
            g.phase_start = _dd.fromisoformat(data["phase_start"])
            db.commit()
            return {"ok": True}
    elif action == "assign_worker":
        existing = db.query(WorkerGuardia).filter(
            WorkerGuardia.worker_name == data["worker_name"],
            WorkerGuardia.group_name == data["group_name"],
        ).first()
        if data.get("guardia"):
            guardia = db.query(Guardia).filter(Guardia.name == data["guardia"]).first()
            if not guardia:
                raise HTTPException(400, "Guardia no encontrada")
            if existing:
                existing.guardia_id = guardia.id
            else:
                db.add(WorkerGuardia(worker_name=data["worker_name"], group_name=data["group_name"], guardia_id=guardia.id))
        elif existing:
            db.delete(existing)
        if data.get("cargo") is not None and existing:
            existing.cargo = data["cargo"]
        if data.get("cargo") is not None:
            rw = db.query(RacsWorker).filter(RacsWorker.name == data["worker_name"], RacsWorker.group_name == data["group_name"], RacsWorker.active == True).first()
            if rw:
                rw.cargo = data["cargo"]
        db.commit()
        return {"ok": True}
    raise HTTPException(400, "Acción no válida")
