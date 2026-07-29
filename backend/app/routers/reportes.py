"""Reports router — main form, CRUD, export, images."""
import os, io, csv, uuid
from io import BytesIO
from datetime import date, time, datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, Request, Body
from fastapi.responses import HTMLResponse, StreamingResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional

from ..core.database import get_db
from ..core.config import settings, BASE_DIR
from ..models import Worker, Report, JobEntry, JobImage, RacsWorker, Guardia, WorkerGuardia
from ..schemas import ReportCreate, ReportResponse, WorkerResponse, JobImageResponse
from ..excel_export import build_excel
from ..daily_report import generate_daily_report, generate_daily_report_bytes, list_daily_reports
from ..services.racs_service import get_all_workers, get_worker_guardias, is_guardia_on_site
from ..services.telegram_service import send_telegram
from sqlalchemy import func as _sf

PROJECT_DIR = os.path.dirname(BASE_DIR)  # project root
TEMPLATE_DIR = os.path.join(BASE_DIR, "app", "templates")
STATIC_DIR = os.path.join(PROJECT_DIR, "static")

templates = Jinja2Templates(directory=TEMPLATE_DIR)
router = APIRouter(tags=["Reportes"])


# ─── Helpers ────────────────────────────────────────────────────────────


def parse_time(value):
    if isinstance(value, time): return value
    if isinstance(value, str):
        for fmt in ("%H:%M", "%H:%M:%S"):
            try: return datetime.strptime(value, fmt).time()
            except: pass
    return None


def parse_date(value):
    if isinstance(value, date): return value
    if isinstance(value, str):
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d"):
            try: return datetime.strptime(value, fmt).date()
            except: pass
    return None


# ─── Pages ──────────────────────────────────────────────────────────────


@router.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@router.get("/options/all")
@router.get("/api/options")
def get_options(db: Session = Depends(get_db)):
    """Return all select options for the form (frontend legacy format)."""
    from ..models import (
        EquipmentCategory, EquipmentSubitem, Collaborator, Macroprocess,
        WorkType, Action, Turno, Nivel, RacsWorker,
    )
    turnos = [t.name for t in db.query(Turno).order_by(Turno.position).all()]
    grupos = ["Mantt. Eq. Trackless", "Mantt. Eq. Convencional", "Mantt. Eq. Electrico"]
    colab = {}
    for c in db.query(Collaborator).order_by(Collaborator.position).all():
        colab.setdefault(c.group_name, []).append(c.name)
    for rw in db.query(RacsWorker).filter(RacsWorker.active == True, RacsWorker.group_name.in_(["Trackless", "Convencional", "Electrico"])).order_by(RacsWorker.name).all():
        g = rw.group_name
        if rw.name not in colab.get(g, []):
            colab.setdefault(g, []).append(rw.name)
    macro = {}
    for m in db.query(Macroprocess).order_by(Macroprocess.position).all():
        macro.setdefault(m.group_key, []).append(m.name)
    wt = {}
    for w in db.query(WorkType).order_by(WorkType.position).all():
        wt.setdefault(w.type_key, []).append({"name": w.name, "default_action": w.default_action or ""})
    acc = {}
    for a in db.query(Action).order_by(Action.position).all():
        acc.setdefault(a.group_key, []).append(a.name)
    niveles = [n.name for n in db.query(Nivel).order_by(Nivel.position).all()]
    equipos = {}
    for cat in db.query(EquipmentCategory).order_by(EquipmentCategory.position).all():
        subs = []
        for sub in cat.subitems:
            subs.append({"nombre": sub.name, "mide": sub.meters})
        equipos[cat.name] = {"subequipos": subs, "accion_grupo": cat.action_group or ""}
    return {
        "turnos": turnos, "grupos": grupos, "colaboradores": colab,
        "colab_max_select": 4, "macroprocesos": macro, "tipos_trabajo": wt,
        "acciones": acc, "niveles": niveles, "equipos": equipos,
    }


# ─── Workers ────────────────────────────────────────────────────────────


@router.get("/workers")
def list_workers(db: Session = Depends(get_db)):
    return db.query(Worker).order_by(Worker.name).all()


@router.post("/workers")
def create_worker(name: str = Form(...), db: Session = Depends(get_db)):
    w = Worker(name=name)
    db.add(w)
    db.commit()
    db.refresh(w)
    return w


# ─── Reports CRUD ───────────────────────────────────────────────────────


@router.post("/api/reports", response_model=ReportResponse)
@router.post("/reports", response_model=ReportResponse, include_in_schema=False)
def create_report(data: ReportCreate, db: Session = Depends(get_db)):
    worker = db.query(Worker).filter(
        Worker.name == data.worker_name,
        Worker.email == data.worker_email
    ).first()
    if not worker:
        worker = Worker(name=data.worker_name, email=data.worker_email)
        db.add(worker)
        db.flush()

    r = Report(
        worker_id=worker.id,
        date=parse_date(data.date), shift=data.shift, group_name=data.group_name,
        start_time=parse_time(data.start_time) if data.start_time else None,
        end_time=parse_time(data.end_time) if data.end_time else None,
        collaborators_trackless=data.collaborators_trackless,
        collaborators_convencional=data.collaborators_convencional,
        collaborators_electrico=data.collaborators_electrico,
    )
    db.add(r)
    db.flush()
    for entry_data in data.entries:
        e = JobEntry(
            report_id=r.id, macroprocess=entry_data.macroprocess,
            work_type=entry_data.work_type, work_subtype=entry_data.work_subtype,
            action=entry_data.action, description=entry_data.description,
            level=entry_data.level, location=entry_data.location,
            start_time_int=parse_time(entry_data.start_time_int) if entry_data.start_time_int else None,
            end_time_int=parse_time(entry_data.end_time_int) if entry_data.end_time_int else None,
            duration=entry_data.duration, equipment=entry_data.equipment,
            horometer_motor=entry_data.horometer_motor,
            horometer_motor_jumbo=entry_data.horometer_motor_jumbo,
            horometer_motor_volquetes=entry_data.horometer_motor_volquetes,
            horometer_electric=entry_data.horometer_electric,
            horometer_percussion=entry_data.horometer_percussion,
            kilometer=entry_data.kilometer,
            collaborators=entry_data.collaborators,
        )
        db.add(e)
    db.commit()
    db.refresh(r)
    return r


@router.get("/api/reports")
@router.get("/reports", include_in_schema=False)
def list_reports(
    cursor_id: Optional[int] = Query(None, alias="cursor"),
    cursor_date: Optional[str] = Query(None, alias="cursor_date"),
    limit: int = Query(50),
    worker_name: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    q = db.query(Report).options(joinedload(Report.worker))
    if worker_name:
        q = q.join(Worker).filter(Worker.name.ilike(f"%{worker_name}%"))
    if date_from:
        q = q.filter(Report.date >= parse_date(date_from))
    if date_to:
        q = q.filter(Report.date <= parse_date(date_to))
    if cursor_id is not None and cursor_date is not None:
        try:
            dt = datetime.fromisoformat(cursor_date)
        except Exception:
            dt = None
        if dt is not None:
            q = q.filter(Report.created_at < dt).filter(Report.id < cursor_id)
    reports = q.order_by(Report.created_at.desc(), Report.id.desc()).limit(limit + 1).all()
    has_more = len(reports) > limit
    reports = reports[:limit]
    result = []
    for rp in reports:
        result.append({
            "id": rp.id,
            "worker_id": rp.worker_id,
            "worker_name": rp.worker.name if rp.worker else None,
            "date": rp.date.isoformat() if rp.date else None,
            "shift": rp.shift,
            "group_name": rp.group_name,
            "start_time": rp.start_time.strftime("%H:%M") if rp.start_time else None,
            "end_time": rp.end_time.strftime("%H:%M") if rp.end_time else None,
            "collaborators_trackless": rp.collaborators_trackless,
            "collaborators_convencional": rp.collaborators_convencional,
            "collaborators_electrico": rp.collaborators_electrico,
            "created_at": rp.created_at.isoformat() if rp.created_at else None,
            "entries": [{
                "id": e.id,
                "macroprocess": e.macroprocess, "work_type": e.work_type,
                "work_subtype": e.work_subtype, "action": e.action,
                "description": e.description, "level": e.level, "location": e.location,
                "start_time_int": e.start_time_int.strftime("%H:%M") if e.start_time_int else None,
                "end_time_int": e.end_time_int.strftime("%H:%M") if e.end_time_int else None,
                "duration": e.duration, "equipment": e.equipment,
                "horometer_motor": e.horometer_motor,
                "horometer_motor_jumbo": e.horometer_motor_jumbo,
                "horometer_motor_volquetes": e.horometer_motor_volquetes,
                "horometer_electric": e.horometer_electric,
                "horometer_percussion": e.horometer_percussion,
                "kilometer": e.kilometer, "collaborators": e.collaborators,
            } for e in rp.entries],
        })
    next_cursor = None
    if has_more and reports:
        last = reports[-1]
        if last.created_at:
            next_cursor = [last.id, last.created_at.isoformat()]
    return {"data": result, "has_more": has_more, "next_cursor": next_cursor}


def _report_to_dict(r):
    """Serialize Report ORM -> dict for build_excel."""
    return {
        "id": r.id, "date": r.date,
        "shift": r.shift, "group_name": r.group_name,
        "worker_name": r.worker.name if r.worker else None,
        "entries": [
            {
                "macroprocess": e.macroprocess, "work_type": e.work_type,
                "work_subtype": e.work_subtype, "action": e.action,
                "description": e.description, "level": e.level,
                "location": e.location,
                "start_time_int": e.start_time_int, "end_time_int": e.end_time_int,
                "duration": e.duration, "equipment": e.equipment,
                "horometer_motor": e.horometer_motor,
                "horometer_motor_jumbo": e.horometer_motor_jumbo,
                "horometer_motor_volquetes": e.horometer_motor_volquetes,
                "horometer_electric": e.horometer_electric,
                "horometer_percussion": e.horometer_percussion,
                "kilometer": e.kilometer, "collaborators": e.collaborators,
            }
            for e in (r.entries or [])
        ],
    }


@router.get("/api/reports/export/excel")
@router.get("/reports/export", include_in_schema=False)
def export_reports_excel(
    date_from: Optional[str] = Query(None), date_to: Optional[str] = Query(None),
    worker: Optional[str] = Query(None), db: Session = Depends(get_db),
):
    q = db.query(Report).options(joinedload(Report.entries), joinedload(Report.worker))
    if date_from: q = q.filter(Report.date >= parse_date(date_from))
    if date_to: q = q.filter(Report.date <= parse_date(date_to))
    if worker: q = q.join(Worker).filter(Worker.name.ilike(f"%{worker}%"))
    q = q.order_by(Report.date.asc(), Report.id.asc())
    data = [_report_to_dict(r) for r in q.all()]
    wb = build_excel(data)
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return Response(
        content=buf.getvalue(), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=reportes.xlsx"},
    )


@router.get("/api/reports/export/csv")
@router.get("/reports/export-csv", include_in_schema=False)
def export_reports_csv(
    date_from: Optional[str] = Query(None), date_to: Optional[str] = Query(None),
    worker: Optional[str] = Query(None), db: Session = Depends(get_db),
):
    q = db.query(Report).options(joinedload(Report.entries), joinedload(Report.worker))
    if date_from: q = q.filter(Report.date >= parse_date(date_from))
    if date_to: q = q.filter(Report.date <= parse_date(date_to))
    if worker: q = q.join(Worker).filter(Worker.name.ilike(f"%{worker}%"))
    q = q.order_by(Report.date.asc(), Report.id.asc())
    data = q.all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Fecha", "Turno", "Grupo", "Trabajador", "Macroproceso", "Tipo Trabajo", "Acción", "Descripción", "Equipo"])
    for r in data:
        worker_name = r.worker.name if r.worker else ""
        for e in r.entries:
            date_str = r.date.strftime("%d-%m-%Y") if r.date else ""
            writer.writerow([r.id, date_str, r.shift, r.group_name, worker_name, e.macroprocess, e.work_type, e.action, e.description, e.equipment])
    return StreamingResponse(iter([output.getvalue()]), media_type="text/csv",
                             headers={"Content-Disposition": "attachment; filename=reportes.csv"})


@router.get("/api/daily-reports")
@router.get("/reports/dates", include_in_schema=False)
def get_daily_reports(db: Session = Depends(get_db)):
    rows = db.query(Report.date).distinct().order_by(Report.date.desc()).limit(30).all()
    return [{"date": r[0].isoformat()} for r in rows]


@router.post("/api/daily-reports/generate")
def generate_daily_report_api(data: dict = Body(...), db: Session = Depends(get_db)):
    report_date = data.get("target_date", "")
    try: d = parse_date(report_date) or date.today() - timedelta(days=1)
    except: d = date.today() - timedelta(days=1)
    reports = db.query(Report).options(joinedload(Report.entries), joinedload(Report.worker)).filter(Report.date == d).all()
    grouped = {}
    for rp in reports:
        entries = [{
            "macroprocess": e.macroprocess, "work_type": e.work_type,
            "work_subtype": e.work_subtype, "action": e.action,
            "description": e.description, "level": e.level, "location": e.location,
            "start_time_int": e.start_time_int.strftime("%H:%M") if e.start_time_int else None,
            "end_time_int": e.end_time_int.strftime("%H:%M") if e.end_time_int else None,
            "duration": e.duration, "equipment": e.equipment,
            "horometer_motor": e.horometer_motor,
            "horometer_motor_jumbo": e.horometer_motor_jumbo,
            "horometer_motor_volquetes": e.horometer_motor_volquetes,
            "horometer_electric": e.horometer_electric,
            "horometer_percussion": e.horometer_percussion,
            "kilometer": e.kilometer, "collaborators": e.collaborators,
        } for e in rp.entries]
        group = rp.group_name; shift = rp.shift
        grouped.setdefault(group, {}).setdefault(shift, []).append({
            "group_name": group, "shift": shift, "entries": entries,
        })
    excel_data = generate_daily_report_bytes(d, grouped)
    return StreamingResponse(
        BytesIO(excel_data.read()), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="Reporte_Diario_{d.isoformat()}.xlsx"'},
    )


@router.get("/reports/daily/{report_date}")
def generate_daily(report_date: str, db: Session = Depends(get_db)):
    try: d = parse_date(report_date) or date.today() - timedelta(days=1)
    except: d = date.today() - timedelta(days=1)
    reports = db.query(Report).options(joinedload(Report.entries), joinedload(Report.worker)).filter(Report.date == d).all()
    grouped = {}
    for rp in reports:
        entries = [{
            "macroprocess": e.macroprocess, "work_type": e.work_type,
            "work_subtype": e.work_subtype, "action": e.action,
            "description": e.description, "level": e.level, "location": e.location,
            "start_time_int": e.start_time_int.strftime("%H:%M") if e.start_time_int else None,
            "end_time_int": e.end_time_int.strftime("%H:%M") if e.end_time_int else None,
            "duration": e.duration, "equipment": e.equipment,
            "horometer_motor": e.horometer_motor,
            "horometer_motor_jumbo": e.horometer_motor_jumbo,
            "horometer_motor_volquetes": e.horometer_motor_volquetes,
            "horometer_electric": e.horometer_electric,
            "horometer_percussion": e.horometer_percussion,
            "kilometer": e.kilometer, "collaborators": e.collaborators,
        } for e in rp.entries]
        group = rp.group_name; shift = rp.shift
        grouped.setdefault(group, {}).setdefault(shift, []).append({
            "group_name": group, "shift": shift, "entries": entries,
        })
    excel_data = generate_daily_report_bytes(d, grouped)
    return StreamingResponse(
        BytesIO(excel_data.read()), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="Reporte_Diario_{d.isoformat()}.xlsx"'},
    )


# ─── Daily compliance (must be before {report_id} routes) ──────────


MAINT_GROUPS = ["Trackless", "Convencional", "Electrico"]


def _collect_collaborators(reports):
    names = []
    for r in reports:
        for e in (r.entries or []):
            if e.collaborators:
                for n in e.collaborators.split(","):
                    n = n.strip()
                    if n:
                        names.append(n)
    return names


def _normalize(name):
    return name.strip().lower()


@router.get("/api/reports/daily-compliance")
def daily_compliance(
    notify: Optional[bool] = Query(False),
    db: Session = Depends(get_db),
):
    today = date.today()
    yesterday = today - timedelta(days=1)
    day_before = today - timedelta(days=2)

    ayer_reports = db.query(Report).options(joinedload(Report.entries)).filter(Report.date == yesterday).all()
    anteayer_reports = db.query(Report).options(joinedload(Report.entries)).filter(Report.date == day_before).all()

    def split_by_shift(reports):
        dia = []
        noche = []
        for r in reports:
            if not r.shift:
                continue
            s = r.shift.lower().replace("\u00ed", "i")  # Día -> Dia
            if "dia" in s:
                dia.append(r)
            elif "noche" in s:
                noche.append(r)
        return dia, noche

    ayer_dia, ayer_noche = split_by_shift(ayer_reports)
    anteayer_dia, anteayer_noche = split_by_shift(anteayer_reports)

    def unique_names(reports):
        return sorted(set(_collect_collaborators(reports)))

    ayer_dia_raw = unique_names(ayer_dia)
    ayer_noche_raw = unique_names(ayer_noche)
    anteayer_dia_raw = unique_names(anteayer_dia)
    anteayer_noche_raw = unique_names(anteayer_noche)

    # Master list: RacsWorker activos de Trackless/Convencional/Electrico
    master = db.query(RacsWorker).filter(
        RacsWorker.active == True,
        RacsWorker.group_name.in_(MAINT_GROUPS),
    ).all()
    master_lookup = {}  # normalized -> canonical name
    worker_groups = {}  # canonical name -> group
    for w in master:
        key = _normalize(w.name)
        master_lookup[key] = w.name
        worker_groups[w.name] = w.group_name

    wg_map = get_worker_guardias(db)

    def match_to_master(raw_names):
        matched = []
        seen = set()
        for n in raw_names:
            key = _normalize(n)
            canonical = master_lookup.get(key)
            if canonical and canonical not in seen:
                seen.add(canonical)
                matched.append(canonical)
        return sorted(matched)

    def calc_on_site_rest(worker_name_list):
        on_site = []
        on_rest = []
        for name in worker_name_list:
            g = wg_map.get((name, worker_groups.get(name, "")), "")
            if is_guardia_on_site(g, check_date=yesterday, db=db):
                on_site.append(name)
            else:
                on_rest.append(name)
        return on_site, on_rest

    ayer_dia_reported = match_to_master(ayer_dia_raw)
    ayer_noche_reported = match_to_master(ayer_noche_raw)
    anteayer_dia_reported = match_to_master(anteayer_dia_raw)
    anteayer_noche_reported = match_to_master(anteayer_noche_raw)

    all_master_names = list(master_lookup.values())
    on_site_all, on_rest_all = calc_on_site_rest(all_master_names)
    on_site_set = set(on_site_all)

    ayer_reported_all = set(ayer_dia_reported + ayer_noche_reported)
    reported_yesterday = sorted(ayer_reported_all & on_site_set)
    missing_yesterday = sorted(on_site_set - ayer_reported_all)
    faltaron_global_yesterday = sorted(on_site_set - ayer_reported_all)
    faltaron_global_anteayer = sorted(on_site_set - set(anteayer_dia_reported + anteayer_noche_reported))

    data = {
        "fecha": today.strftime("%d-%m-%Y"),
        "ayer": {
            "Dia": {"reportaron": ayer_dia_reported, "faltaron": faltaron_global_yesterday},
            "Noche": {"reportaron": ayer_noche_reported, "faltaron": faltaron_global_yesterday},
        },
        "anteayer": {
            "Dia": {"reportaron": anteayer_dia_reported, "faltaron": faltaron_global_anteayer},
            "Noche": {"reportaron": anteayer_noche_reported, "faltaron": faltaron_global_anteayer},
        },
        "en_descanso": sorted(on_rest_all),
        "total_mina": len(on_site_all),
        "total_master": len(all_master_names),
        "total_reportaron_ayer": len(reported_yesterday),
        "total_faltaron_ayer": len(missing_yesterday),
    }

    if notify:
        def bullet(names, empty_text="---"):
            return ", ".join(names) if names else empty_text

        lines = []
        lines.append(f"\U0001f4ca <b>CONTROL DIARIO DE REPORTES</b>")
        lines.append(f"{today.strftime('%d/%m/%Y')}")
        lines.append("")

        lines.append(f"\U0001f539 <b>AYER</b> ({yesterday.strftime('%d/%m')})")
        lines.append("")
        lines.append(f"  \U0001f31e <b>DIA</b>")
        lines.append(f"  \u2705 Reportaron ({len(ayer_dia_reported)}):")
        lines.append(f"     {bullet(ayer_dia_reported)}")
        lines.append("")
        lines.append(f"  \U0001f319 <b>NOCHE</b>")
        lines.append(f"  \u2705 Reportaron ({len(ayer_noche_reported)}):")
        lines.append(f"     {bullet(ayer_noche_reported)}")
        if faltaron_global_yesterday:
            lines.append("")
            lines.append(f"  \u274c <b>NO REPORTARON</b> ({len(faltaron_global_yesterday)}):")
            lines.append(f"     {bullet(faltaron_global_yesterday)}")

        lines.append("")
        lines.append(f"\U0001f539 <b>ANTEAYER</b> ({day_before.strftime('%d/%m')})")
        lines.append(f"  \U0001f31e DIA: {len(anteayer_dia_reported)} reportaron")
        lines.append(f"  \U0001f319 NOCHE: {len(anteayer_noche_reported)} reportaron")
        if faltaron_global_anteayer:
            lines.append(f"  \u274c No reportaron: {len(faltaron_global_anteayer)} ({bullet(faltaron_global_anteayer)})")

        if on_rest_all:
            lines.append("")
            lines.append(f"\U0001f634 <b>EN DESCANSO</b> ({len(on_rest_all)})")
            lines.append(f"  {bullet(on_rest_all)}")

        lines.append("")
        lines.append(f"\U0001f4ca <b>RESUMEN</b>")
        lines.append(f"  Total personal en mina: {len(on_site_all)}")
        pct = round(len(reported_yesterday) / len(on_site_all) * 100) if on_site_all else 0
        lines.append(f"  Reportaron ayer: {len(reported_yesterday)}/{len(on_site_all)} ({pct}%)")
        lines.append(f"  Faltan ayer: {len(missing_yesterday)}")

        message = "\n".join(lines)
        sent = send_telegram(message)
        data["telegram_enviado"] = sent

    return data


@router.get("/api/reports/{report_id}")
@router.get("/reports/{report_id}", include_in_schema=False)
def get_report(report_id: int, db: Session = Depends(get_db)):
    r = db.query(Report).options(
        joinedload(Report.entries).joinedload(JobEntry.images),
        joinedload(Report.worker),
    ).filter(Report.id == report_id).first()
    if not r: raise HTTPException(404)
    return {
        "id": r.id, "worker_id": r.worker_id,
        "worker_name": r.worker.name if r.worker else None,
        "date": r.date.isoformat() if r.date else None,
        "shift": r.shift, "group_name": r.group_name,
        "start_time": r.start_time.strftime("%H:%M") if r.start_time else None,
        "end_time": r.end_time.strftime("%H:%M") if r.end_time else None,
        "collaborators_trackless": r.collaborators_trackless,
        "collaborators_convencional": r.collaborators_convencional,
        "collaborators_electrico": r.collaborators_electrico,
        "created_at": r.created_at.isoformat() if r.created_at else None,
        "entries": [{
            "id": e.id, "report_id": e.report_id,
            "macroprocess": e.macroprocess, "work_type": e.work_type,
            "work_subtype": e.work_subtype, "action": e.action,
            "description": e.description, "level": e.level, "location": e.location,
            "start_time_int": e.start_time_int.strftime("%H:%M") if e.start_time_int else None,
            "end_time_int": e.end_time_int.strftime("%H:%M") if e.end_time_int else None,
            "duration": e.duration, "equipment": e.equipment,
            "horometer_motor": e.horometer_motor,
            "horometer_motor_jumbo": e.horometer_motor_jumbo,
            "horometer_motor_volquetes": e.horometer_motor_volquetes,
            "horometer_electric": e.horometer_electric,
            "horometer_percussion": e.horometer_percussion,
            "kilometer": e.kilometer, "collaborators": e.collaborators,
            "images": [{"id": img.id, "filename": img.filename, "original_name": img.original_name} for img in e.images],
        } for e in r.entries],
    }


@router.delete("/api/reports/{report_id}")
@router.delete("/reports/{report_id}", include_in_schema=False)
def delete_report(report_id: int, password: str = Query(...), db: Session = Depends(get_db)):
    from ..core.config import settings
    if password != settings.admin_dni: raise HTTPException(401, "DNI incorrecto")
    r = db.query(Report).filter(Report.id == report_id).first()
    if not r: raise HTTPException(404)
    db.query(JobEntry).filter(JobEntry.report_id == report_id).delete()
    db.delete(r)
    db.commit()
    return {"ok": True}


@router.post("/api/reports/batch-delete")
@router.post("/reports/batch-delete", include_in_schema=False)
def batch_delete_reports(data: dict = Body(...), db: Session = Depends(get_db)):
    from ..core.config import settings
    if data.get("password") != settings.admin_dni: raise HTTPException(401, "DNI incorrecto")
    ids = data.get("ids", [])
    if not ids: raise HTTPException(400, "No IDs provided")
    db.query(JobEntry).filter(JobEntry.report_id.in_(ids)).delete(synchronize_session=False)
    db.query(Report).filter(Report.id.in_(ids)).delete(synchronize_session=False)
    db.commit()
    return {"ok": True, "deleted": len(ids)}


@router.post("/api/reports/delete-verify")
def verify_delete_password(data: dict = Body(...)):
    from ..core.config import settings
    if data.get("password") == settings.admin_dni:
        return {"ok": True}
    raise HTTPException(401, "Contraseña incorrecta")


@router.put("/api/reports/{report_id}")
@router.put("/reports/{report_id}", include_in_schema=False)
def update_report(report_id: int, data: dict = Body(...), db: Session = Depends(get_db)):
    from ..core.config import settings
    if data.get("password") != settings.admin_dni: raise HTTPException(401, "DNI incorrecto")
    r = db.query(Report).filter(Report.id == report_id).first()
    if not r: raise HTTPException(404)
    if "date" in data: r.date = parse_date(data["date"])
    if "shift" in data: r.shift = data["shift"]
    if "group_name" in data: r.group_name = data["group_name"]
    db.commit()
    return {"ok": True}


# ─── Images ─────────────────────────────────────────────────────────────


@router.post("/upload-image/{job_entry_id}")
def upload_image(job_entry_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
    je = db.query(JobEntry).filter(JobEntry.id == job_entry_id).first()
    if not je: raise HTTPException(404, "Job entry not found")
    ext = os.path.splitext(file.filename or "img.jpg")[1].lower()
    if ext not in (".jpg", ".jpeg", ".png", ".gif", ".webp"):
        raise HTTPException(400, "Formato no soportado")
    content = file.file.read()
    if len(content) > settings.max_image_size_mb * 1024 * 1024:
        raise HTTPException(400, f"Imagen muy grande (máx {settings.max_image_size_mb}MB)")
    date_folder = je.report.date.isoformat()
    rel_dir = os.path.join("uploads", "images", date_folder)
    abs_dir = os.path.join(STATIC_DIR, rel_dir)
    os.makedirs(abs_dir, exist_ok=True)
    fname = f"{uuid.uuid4().hex[:12]}{ext}"
    with open(os.path.join(abs_dir, fname), "wb") as f:
        f.write(content)
    ji = JobImage(job_entry_id=job_entry_id, filename=f"/static/{rel_dir}/{fname}")
    db.add(ji)
    db.commit()
    db.refresh(ji)
    return ji


@router.delete("/image/{image_id}")
def delete_image(image_id: int, db: Session = Depends(get_db)):
    ji = db.query(JobImage).filter(JobImage.id == image_id).first()
    if not ji: raise HTTPException(404)
    path = os.path.join(STATIC_DIR, ji.filename.replace("/static/", ""))
    if os.path.exists(path): os.remove(path)
    db.delete(ji)
    db.commit()
    return {"ok": True}


@router.get("/api/equipment/{equipment_name}/last-reading")
@router.get("/api/equipment/last-reading/{equipment_name}", include_in_schema=False)
def get_equipment_last_reading(equipment_name: str, db: Session = Depends(get_db)):
    j = db.query(JobEntry).filter(
        JobEntry.equipment == equipment_name,
        JobEntry.horometer_motor.isnot(None),
    ).order_by(JobEntry.id.desc()).first()
    if j:
        return {"horometer_motor": j.horometer_motor, "horometer_electric": j.horometer_electric, "kilometer": j.kilometer}
    return {}
