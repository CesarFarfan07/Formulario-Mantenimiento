"""RACS business logic — period, guardia, worker helpers."""
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from ..models import Guardia, WorkerGuardia, RacsWorker


def get_racs_period(dt=None):
    """Return (period_start, period_end) for the current RACS period.
    Period: Sunday 20:00 → next Sunday 18:00.
    """
    if dt is None:
        dt = datetime.now()
    days_back = (dt.weekday() + 1) % 7
    cand_start = (dt - timedelta(days=days_back)).replace(
        hour=20, minute=0, second=0, microsecond=0
    )
    if cand_start > dt:
        cand_start -= timedelta(days=7)
    cand_end = cand_start + timedelta(days=6, hours=22)
    if cand_end <= dt:
        cand_start = cand_end.replace(hour=20, minute=0)
        cand_end = cand_start + timedelta(days=6, hours=22)
    return cand_start, cand_end


def is_guardia_on_site(guardia_name: str, check_date=None, db=None):
    """Return True if the guardia is currently working (on-site)."""
    if not guardia_name:
        return True
    if check_date is None:
        check_date = datetime.now().date()
    elif isinstance(check_date, datetime):
        check_date = check_date.date()
    if db is None:
        return True
    g = db.query(Guardia).filter(Guardia.name == guardia_name).first()
    if not g:
        return True
    elapsed = (check_date - g.phase_start).days
    if elapsed < 0:
        return True
    return (elapsed % 30) < 20


def get_worker_guardias(db):
    """Return dict: (worker_name, group_name) -> guardia_name"""
    rows = (
        db.query(WorkerGuardia.worker_name, WorkerGuardia.group_name, Guardia.name)
        .join(Guardia, WorkerGuardia.guardia_id == Guardia.id)
        .all()
    )
    return {(r.worker_name, r.group_name): r.name for r in rows}


def get_worker_cargos(db):
    """Return dict: (worker_name, group_name) -> cargo"""
    rows = (
        db.query(RacsWorker.name, RacsWorker.group_name, RacsWorker.cargo)
        .filter(RacsWorker.active == True)
        .all()
    )
    return {(r.name, r.group_name): r.cargo for r in rows}


def get_all_workers(db):
    """Return list of dicts: {name, group_name, cargo} from DB."""
    q = db.query(RacsWorker).filter(RacsWorker.active == True)
    return [{"name": r.name, "group_name": r.group_name, "cargo": r.cargo} for r in q.all()]


def get_guardia_cycle_info(phase_start, today=None):
    """Return cycle day, on_site, formatted ranges for a guardia phase start."""
    if today is None:
        today = datetime.now().date()
    elif isinstance(today, datetime):
        today = today.date()
    elapsed = (today - phase_start).days
    cycle_day = ((elapsed % 30) + 30) % 30
    on_site = cycle_day < 20
    from datetime import timedelta as td
    work_end = phase_start + td(days=19)
    rest_start = phase_start + td(days=20)
    rest_end = phase_start + td(days=29)
    fmt = lambda d: d.strftime("%d %b")
    return {
        "cycle_day": cycle_day,
        "on_site": on_site,
        "work_range": f"{fmt(phase_start)} → {fmt(work_end)}",
        "rest_range": f"{fmt(rest_start)} → {fmt(rest_end)}",
    }
