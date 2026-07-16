import datetime
from sqlalchemy import Column, Integer, String, Text, Date, Time, DateTime, ForeignKey, Float, Index, Boolean
from sqlalchemy.orm import relationship
from .database import Base


class Worker(Base):
    __tablename__ = "workers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    email = Column(String(200), nullable=False)
    group_name = Column(String(100), nullable=True)

    reports = relationship("Report", back_populates="worker")


class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)
    worker_id = Column(Integer, ForeignKey("workers.id"), nullable=False)
    date = Column(Date, nullable=False, default=datetime.date.today)
    shift = Column(String(50), nullable=False)
    group_name = Column(String(100), nullable=False)
    start_time = Column(Time, nullable=True)
    end_time = Column(Time, nullable=True)
    collaborators_trackless = Column(Text, nullable=True)
    collaborators_convencional = Column(Text, nullable=True)
    collaborators_electrico = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    worker = relationship("Worker", back_populates="reports")
    entries = relationship("JobEntry", back_populates="report", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_reports_date_id", "date", "id"),
        Index("ix_reports_group_shift_date", "group_name", "shift", "date"),
        Index("ix_reports_created_at_id", "created_at", "id"),
    )


class JobEntry(Base):
    __tablename__ = "job_entries"

    __table_args__ = (
        Index("ix_job_entries_report_id", "report_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(Integer, ForeignKey("reports.id"), nullable=False)
    macroprocess = Column(String(100), nullable=True)
    work_type = Column(String(100), nullable=True)
    work_subtype = Column(String(100), nullable=True)
    action = Column(String(200), nullable=True)
    description = Column(Text, nullable=True)
    level = Column(String(100), nullable=True)
    location = Column(String(200), nullable=True)
    start_time_int = Column(Time, nullable=True)
    end_time_int = Column(Time, nullable=True)
    duration = Column(String(50), nullable=True)
    equipment = Column(String(200), nullable=True)
    horometer_motor = Column(Float, nullable=True)
    horometer_motor_jumbo = Column(Float, nullable=True)
    horometer_motor_volquetes = Column(Float, nullable=True)
    horometer_electric = Column(Float, nullable=True)
    horometer_percussion = Column(Float, nullable=True)
    kilometer = Column(Float, nullable=True)
    blanco = Column(String(100), nullable=True)
    collaborators = Column(Text, nullable=True)

    report = relationship("Report", back_populates="entries")
    images = relationship("JobImage", back_populates="entry", cascade="all, delete-orphan")


class JobImage(Base):
    __tablename__ = "job_images"

    id = Column(Integer, primary_key=True, index=True)
    entry_id = Column(Integer, ForeignKey("job_entries.id"), nullable=False)
    filename = Column(String(255), nullable=False)
    original_name = Column(String(255), nullable=False)
    uploaded_at = Column(DateTime, default=datetime.datetime.utcnow)

    entry = relationship("JobEntry", back_populates="images")


# ─── Admin / Config tables ────────────────────────────────────────────────────

class EquipmentCategory(Base):
    __tablename__ = "equipment_categories"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False, unique=True)
    action_group = Column(String(50), nullable=True)  # Trackless / Convencional
    position = Column(Integer, default=0)
    subitems = relationship("EquipmentSubitem", back_populates="category", cascade="all, delete-orphan", order_by="EquipmentSubitem.position")


class EquipmentSubitem(Base):
    __tablename__ = "equipment_subitems"
    id = Column(Integer, primary_key=True, index=True)
    category_id = Column(Integer, ForeignKey("equipment_categories.id"), nullable=False)
    name = Column(String(200), nullable=False)
    meters = Column(String(100), default="fin")  # comma-separated: horometro_motor,kilometraje
    position = Column(Integer, default=0)
    category = relationship("EquipmentCategory", back_populates="subitems")


class Collaborator(Base):
    __tablename__ = "collaborators"
    id = Column(Integer, primary_key=True, index=True)
    group_name = Column(String(50), nullable=False)  # Trackless / Convencional / Electrico
    name = Column(String(200), nullable=False)
    position = Column(Integer, default=0)


class Macroprocess(Base):
    __tablename__ = "macroprocesses"
    id = Column(Integer, primary_key=True, index=True)
    group_key = Column(String(50), nullable=False)  # Trackless / Convencional / Electrico
    name = Column(String(200), nullable=False)
    position = Column(Integer, default=0)


class WorkType(Base):
    __tablename__ = "work_types"
    id = Column(Integer, primary_key=True, index=True)
    type_key = Column(String(100), nullable=False)  # Trackless_Mecánico, Convencional_Eléctrico, etc
    name = Column(String(200), nullable=False)
    default_action = Column(String(200), nullable=True)  # Default action name for this work type
    position = Column(Integer, default=0)


class Action(Base):
    __tablename__ = "actions"
    id = Column(Integer, primary_key=True, index=True)
    group_key = Column(String(50), nullable=False)  # Trackless / Convencional_Electrico
    name = Column(String(200), nullable=False)
    position = Column(Integer, default=0)


class Nivel(Base):
    __tablename__ = "niveles"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)
    position = Column(Integer, default=0)


class Turno(Base):
    __tablename__ = "turnos"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False, unique=True)
    position = Column(Integer, default=0)


class RacsReport(Base):
    __tablename__ = "racs_reports"

    id = Column(Integer, primary_key=True, index=True)
    worker_name = Column(String(200), nullable=False)
    group_name = Column(String(100), nullable=False)
    categoria = Column(String(50), nullable=True)
    tipo = Column(String(50), nullable=False)
    descripcion = Column(Text, nullable=True)
    ubicacion = Column(String(200), nullable=True)
    referencia = Column(String(300), nullable=True)
    nivel = Column(String(100), nullable=True)
    fecha_reporte = Column(Date, nullable=True)
    riesgo = Column(String(20), nullable=True)
    turno = Column(String(10), nullable=True)
    accion_correctiva = Column(Text, nullable=True)
    tipo_descripcion = Column(String(300), nullable=True)
    foto = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)


class Guardia(Base):
    __tablename__ = "guardias"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False, unique=True)
    phase_start = Column(Date, nullable=False)


class WorkerGuardia(Base):
    __tablename__ = "worker_guardias"
    id = Column(Integer, primary_key=True, index=True)
    worker_name = Column(String(200), nullable=False)
    group_name = Column(String(100), nullable=False)
    guardia_id = Column(Integer, ForeignKey("guardias.id"), nullable=False)
    cargo = Column(String(200), nullable=True)


class RacsWorker(Base):
    __tablename__ = "racs_workers"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    group_name = Column(String(100), nullable=False)
    cargo = Column(String(200), nullable=True)
    active = Column(Boolean, default=True)
