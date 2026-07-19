"""Dashboard router — KPIs, stats, OKRs."""
from datetime import date, time, datetime, timedelta
from collections import defaultdict
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func as _sf
import os

from ..core.database import get_db
from ..core.config import BASE_DIR
from ..models import Report, JobEntry, Worker

TEMPLATE_DIR = os.path.join(BASE_DIR, "app", "templates")
templates = Jinja2Templates(directory=TEMPLATE_DIR)

router = APIRouter(tags=["Dashboard"])


def _parse_date(ds):
    try: return datetime.strptime(ds, "%Y-%m-%d").date()
    except: return None


def _parse_duration_minutes(dur):
    if not dur: return None
    parts = str(dur).split(":")
    if len(parts) >= 2:
        try: return int(parts[0]) * 60 + int(parts[1])
        except: pass
    return None


def _build_filtered_query(db, date_from, date_to, group):
    q = db.query(JobEntry).join(JobEntry.report)
    if date_from: q = q.filter(Report.date >= _parse_date(date_from))
    if date_to: q = q.filter(Report.date <= _parse_date(date_to))
    if group: q = q.filter(Report.group_name == group)
    return q


def _compute_period_stats(db, date_from, date_to, group):
    q_base = _build_filtered_query(db, date_from, date_to, group)
    total_jobs = q_base.with_entities(_sf.count(JobEntry.id)).scalar() or 0

    workers = db.query(Worker.id, Worker.name, Worker.group_name).join(Report)
    if date_from: workers = workers.filter(Report.date >= _parse_date(date_from))
    if date_to: workers = workers.filter(Report.date <= _parse_date(date_to))
    if group: workers = workers.filter(Report.group_name == group)
    workers = workers.distinct().all()
    worker_count = len(workers)

    collab_q = q_base.with_entities(JobEntry.collaborators).filter(JobEntry.collaborators.isnot(None))
    collab_names = set()
    for (c,) in collab_q.all():
        for name in c.split(","):
            name = name.strip()
            if name: collab_names.add(name)

    dur_q = q_base.with_entities(JobEntry.duration).filter(JobEntry.duration.isnot(None), JobEntry.duration != "")
    total_minutes = 0
    for (d,) in dur_q.all():
        m = _parse_duration_minutes(d)
        if m is not None: total_minutes += m
    total_hours = round(total_minutes / 60, 1) if total_minutes else 0
    avg_minutes = round(total_minutes / total_jobs, 1) if total_jobs else 0

    equip_data = q_base.with_entities(JobEntry.equipment, JobEntry.duration).filter(
        JobEntry.equipment.isnot(None), JobEntry.equipment != ""
    ).all()
    equip_durs = defaultdict(list)
    for equip, dur in equip_data:
        if dur: equip_durs[equip].append(dur)
    jobs_by_equipment = []
    for equip, durs in sorted(equip_durs.items(), key=lambda x: -len(x[1])):
        cnt = len(durs)
        mins = [_parse_duration_minutes(d) for d in durs]
        valid = [m for m in mins if m is not None]
        avg = round(sum(valid) / len(valid), 1) if valid else None
        equip_hours = round(sum(valid) / 60, 1) if valid else 0
        jobs_by_equipment.append({"equipment": equip, "count": cnt, "avg_duration_min": avg, "total_hours": equip_hours})

    team_q = q_base.with_entities(Report.group_name, _sf.count(JobEntry.id)).group_by(Report.group_name).order_by(_sf.count(JobEntry.id).desc()).all()
    jobs_by_team = [{"team": g, "count": c} for g, c in team_q]

    team_dur_q = q_base.with_entities(Report.group_name, JobEntry.duration).filter(
        JobEntry.duration.isnot(None), JobEntry.duration != ""
    ).all()
    team_durs = defaultdict(list)
    for g, dur in team_dur_q:
        m = _parse_duration_minutes(dur)
        if m is not None: team_durs[g].append(m)
    avg_duration_by_team = [{"team": g, "avg_min": round(sum(v) / len(v), 1)} for g, v in sorted(team_durs.items())]

    shift_q = q_base.with_entities(Report.shift, JobEntry.duration).filter(
        JobEntry.duration.isnot(None), JobEntry.duration != ""
    ).all()
    shift_data = {"Dia": {"jobs": 0, "hours": 0.0}, "Noche": {"jobs": 0, "hours": 0.0}}
    for s, dur in shift_q:
        sk = "Dia" if s and "Dia" in s else "Noche"
        shift_data[sk]["jobs"] += 1
        m = _parse_duration_minutes(dur)
        if m: shift_data[sk]["hours"] += round(m / 60, 1)

    top_equip_q = q_base.with_entities(JobEntry.equipment, _sf.count(JobEntry.id)).filter(
        JobEntry.equipment.isnot(None), JobEntry.equipment != ""
    ).group_by(JobEntry.equipment).order_by(_sf.count(JobEntry.id).desc()).limit(10).all()
    top_equipment = [{"equipment": e, "count": c} for e, c in top_equip_q]

    action_q = q_base.with_entities(JobEntry.action).filter(JobEntry.action.isnot(None)).all()
    pm_count = cm_count = other_count = 0
    for (a,) in action_q:
        al = a.lower()
        if "preventivo" in al: pm_count += 1
        elif "correctivo" in al: cm_count += 1
        else: other_count += 1
    total_actions = pm_count + cm_count + other_count
    pm_pct = round(pm_count / total_actions * 100, 1) if total_actions else 0
    cm_pct = round(cm_count / total_actions * 100, 1) if total_actions else 0

    macro_q = q_base.with_entities(JobEntry.macroprocess, _sf.count(JobEntry.id)).filter(
        JobEntry.macroprocess.isnot(None)
    ).group_by(JobEntry.macroprocess).order_by(_sf.count(JobEntry.id).desc()).all()
    macroprocess_dist = [{"macroprocess": m, "count": c} for m, c in macro_q]

    daily_q = q_base.with_entities(Report.date, _sf.count(JobEntry.id)).group_by(Report.date).order_by(Report.date).all()
    jobs_per_day = [{"date": d.isoformat(), "count": c} for d, c in daily_q]

    collab_count_q = q_base.with_entities(JobEntry.collaborators).filter(JobEntry.collaborators.isnot(None)).all()
    collab_counter = defaultdict(int)
    for (c,) in collab_count_q:
        for name in c.split(","):
            name = name.strip()
            if name: collab_counter[name] += 1
    top_collaborators = [{"name": n, "count": c} for n, c in sorted(collab_counter.items(), key=lambda x: -x[1])[:20]]

    worker_list = [{"name": w.name, "team": w.group_name} for w in workers]

    return {
        "kpis": {
            "total_jobs": total_jobs, "total_hours": total_hours,
            "worker_count": worker_count, "collaborator_count": len(collab_names),
            "avg_duration_min": avg_minutes, "pm_pct": pm_pct, "cm_pct": cm_pct,
        },
        "workers": worker_list,
        "jobs_by_team": jobs_by_team,
        "shift_comparison": shift_data,
        "top_equipment": top_equipment,
        "pm_cm_ratio": {"pm": pm_count, "cm": cm_count, "other": other_count, "pm_pct": pm_pct, "cm_pct": cm_pct},
        "macroprocess_dist": macroprocess_dist,
        "jobs_per_day": jobs_per_day,
        "avg_duration_by_team": avg_duration_by_team,
        "top_collaborators": top_collaborators,
        "jobs_by_equipment": jobs_by_equipment,
    }


def _calc_progress(condition_on_track, condition_needs):
    if condition_on_track: return "on_track"
    if condition_needs: return "needs_attention"
    return "critical"

def _collab_target(collabs):
    return min(collabs + 5, 40)


def _compute_okrs(stats):
    k = stats["kpis"]
    pct = k["pm_pct"]
    cm_pct = k["cm_pct"]
    avg_min = k["avg_duration_min"]
    total_jobs = k["total_jobs"]
    total_hours = k["total_hours"]
    workers = k["worker_count"]
    collabs = k["collaborator_count"]
    jobs_per_worker = round(total_jobs / workers, 1) if workers else 0
    return [
        {
            "objective": "Mejorar la Calidad del Mantenimiento",
            "key_results": [
                {"kr": f"Aumentar mantenimiento preventivo de {pct}% a ≥70%", "current": f"{pct}%", "target": "≥70%", "progress": _calc_progress(pct >= 50, pct >= 30)},
                {"kr": f"Reducir mantenimiento correctivo de {cm_pct}% a ≤30%", "current": f"{cm_pct}%", "target": "≤30%", "progress": _calc_progress(cm_pct <= 30, cm_pct <= 50)},
                {"kr": f"Reducir tiempo promedio por trabajo de {avg_min} min a ≤60 min", "current": f"{avg_min} min", "target": "≤60 min", "progress": _calc_progress(avg_min <= 60, avg_min <= 90)},
            ]
        },
        {
            "objective": "Optimizar la Productividad del Equipo",
            "key_results": [
                {"kr": f"Mantener ≥4 trabajos por trabajador ({jobs_per_worker} actual)", "current": f"{jobs_per_worker}", "target": "≥4", "progress": _calc_progress(jobs_per_worker >= 4, jobs_per_worker >= 2.5)},
                {"kr": f"Aumentar colaboradores activos de {collabs} a ≥{_collab_target(collabs)}", "current": f"{collabs}", "target": f"≥{_collab_target(collabs)}", "progress": _calc_progress(collabs >= 15, collabs >= 8)},
            ]
        },
        {
            "objective": "Fortalecer la Gestión Basada en Datos",
            "key_results": [
                {"kr": "Registrar 100% de trabajos en plataforma digital", "current": "Activo", "target": "100%", "progress": "on_track"},
                {"kr": f"Completar {total_jobs}+ registros en el período", "current": f"{total_jobs}", "target": "Creciente", "progress": _calc_progress(total_jobs >= 20, total_jobs >= 10)},
                {"kr": f"Mantener {total_hours} horas hombre registradas con precisión", "current": f"{total_hours} hrs", "target": "≥100 hrs", "progress": _calc_progress(total_hours >= 100, total_hours >= 50)},
            ]
        },
    ]


# ─── Routes ────────────────────────────────────────────────────────


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard_page(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})


@router.get("/api/dashboard/summary")
def dashboard_summary(
    date_from: str = Query(None), date_to: str = Query(None),
    group: str = Query(None), compare_from: str = Query(None),
    compare_to: str = Query(None), db: Session = Depends(get_db),
):
    today = date.today()
    if not date_from or not date_to:
        if today.day >= 26:
            period_start = today.replace(day=26)
        else:
            period_start = (today.replace(day=1) - timedelta(days=1)).replace(day=26)
        period_end = (period_start + timedelta(days=32)).replace(day=25)
        if not date_from: date_from = period_start.isoformat()
        if not date_to: date_to = period_end.isoformat()

    current = _compute_period_stats(db, date_from, date_to, group)
    current["label"] = f"{_parse_date(date_from).strftime('%d/%m/%Y') if _parse_date(date_from) else date_from} – {_parse_date(date_to).strftime('%d/%m/%Y') if _parse_date(date_to) else date_to}"
    current["date_from"] = date_from
    current["date_to"] = date_to

    result = {"current": current, "comparison": None, "okrs": _compute_okrs(current)}

    if compare_from and compare_to:
        comp = _compute_period_stats(db, compare_from, compare_to, group)
        comp["label"] = f"{_parse_date(compare_from).strftime('%d/%m/%Y') if _parse_date(compare_from) else compare_from} – {_parse_date(compare_to).strftime('%d/%m/%Y') if _parse_date(compare_to) else compare_to}"
        comp["date_from"] = compare_from
        comp["date_to"] = compare_to
        result["comparison"] = comp

    return result


@router.get("/api/dashboard/kpi-detail")
def kpi_detail(
    kpi: str = Query(...), date_from: str = Query(None),
    date_to: str = Query(None), group: str = Query(None),
    db: Session = Depends(get_db),
):
    q_base = _build_filtered_query(db, date_from, date_to, group)

    if kpi in ("pm_pct", "cm_pct"):
        action_filter = "Preventivo" if kpi == "pm_pct" else "Correctivo"
        rows = q_base.filter(JobEntry.action.ilike(f"%{action_filter}%")).order_by(JobEntry.id.desc()).limit(200).all()
        return {"title": f"Trabajos con acción «{action_filter}»", "headers": ["#", "Fecha", "Grupo", "Macroproceso", "Tipo", "Acción", "Equipo", "Duración"], "rows": [[i+1, str(e.report.date), e.report.group_name, e.macroprocess, e.work_type, e.action, e.equipment, e.duration] for i, e in enumerate(rows)]}

    if kpi == "worker_count":
        rows = db.query(Worker.id, Worker.name, Worker.group_name).join(Report)
        if date_from: rows = rows.filter(Report.date >= _parse_date(date_from))
        if date_to: rows = rows.filter(Report.date <= _parse_date(date_to))
        if group: rows = rows.filter(Report.group_name == group)
        rows = rows.distinct().order_by(Worker.name).all()
        return {"title": "Trabajadores que reportaron", "headers": ["ID", "Nombre", "Grupo"], "rows": [[w.id, w.name, w.group_name] for w in rows]}

    if kpi == "collaborator_count":
        rows = q_base.filter(JobEntry.collaborators.isnot(None)).order_by(JobEntry.id.desc()).limit(300).all()
        names = set()
        data = []
        for e in rows:
            if e.collaborators:
                for n in e.collaborators.split(","):
                    n = n.strip()
                    if n and n not in names:
                        names.add(n)
                        data.append([len(data) + 1, n])
        return {"title": "Colaboradores únicos en labor", "headers": ["#", "Nombre"], "rows": data}

    if kpi == "total_hours":
        rows = q_base.filter(JobEntry.duration.isnot(None), JobEntry.duration != "").order_by(JobEntry.id.desc()).limit(300).all()
        return {"title": "Detalle de horas hombre", "headers": ["#", "Fecha", "Grupo", "Macroproceso", "Equipo", "Duración"], "rows": [[i+1, str(e.report.date), e.report.group_name, e.macroprocess, e.equipment, e.duration] for i, e in enumerate(rows)]}

    rows = q_base.order_by(JobEntry.id.desc()).limit(300).all()
    return {"title": "Todos los trabajos del período", "headers": ["#", "Fecha", "Grupo", "Macroproceso", "Tipo", "Acción", "Equipo", "Duración"], "rows": [[i+1, str(e.report.date), e.report.group_name, e.macroprocess, e.work_type, e.action, e.equipment, e.duration] for i, e in enumerate(rows)]}
