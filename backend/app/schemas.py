import datetime
from typing import Optional, Any, List
from pydantic import BaseModel, field_validator


class JobImageBase(BaseModel):
    filename: str
    original_name: str


class JobImageResponse(JobImageBase):
    id: int
    entry_id: int
    uploaded_at: datetime.datetime

    class Config:
        from_attributes = True


class JobEntryBase(BaseModel):
    macroprocess: Optional[str] = None
    work_type: Optional[str] = None
    work_subtype: Optional[str] = None
    action: Optional[str] = None
    description: Optional[str] = None
    level: Optional[str] = None
    location: Optional[str] = None
    start_time_int: Optional[str] = None
    end_time_int: Optional[str] = None
    duration: Optional[str] = None
    equipment: Optional[str] = None
    horometer_motor: Optional[float] = None
    horometer_motor_jumbo: Optional[float] = None
    horometer_motor_volquetes: Optional[float] = None
    horometer_electric: Optional[float] = None
    horometer_percussion: Optional[float] = None
    kilometer: Optional[float] = None
    blanco: Optional[str] = None
    collaborators: Optional[str] = None


class JobEntryCreate(JobEntryBase):
    pass


class JobEntryResponse(JobEntryBase):
    id: int
    report_id: int
    images: List[JobImageResponse] = []

    @field_validator('start_time_int', 'end_time_int', mode='before')
    @classmethod
    def time_to_str(cls, v: Any) -> Optional[str]:
        if isinstance(v, datetime.time):
            return v.strftime('%H:%M')
        return v

    class Config:
        from_attributes = True


class ReportBase(BaseModel):
    date: str
    shift: str
    group_name: str
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    collaborators_trackless: Optional[str] = None
    collaborators_convencional: Optional[str] = None
    collaborators_electrico: Optional[str] = None


class ReportCreate(ReportBase):
    worker_name: str
    worker_email: str
    entries: List[JobEntryCreate]


class ReportResponse(BaseModel):
    id: int
    worker_id: int
    date: str
    shift: str
    group_name: str
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    collaborators_trackless: Optional[str] = None
    collaborators_convencional: Optional[str] = None
    collaborators_electrico: Optional[str] = None
    created_at: datetime.datetime
    entries: List[JobEntryResponse] = []

    @field_validator('date', mode='before')
    @classmethod
    def date_to_str(cls, v: Any) -> str:
        if isinstance(v, datetime.date):
            return v.isoformat()
        return v

    @field_validator('start_time', 'end_time', mode='before')
    @classmethod
    def time_to_str(cls, v: Any) -> Optional[str]:
        if isinstance(v, datetime.time):
            return v.strftime('%H:%M')
        return v

    class Config:
        from_attributes = True


class WorkerResponse(BaseModel):
    id: int
    name: str
    email: str
    group_name: Optional[str] = None

    class Config:
        from_attributes = True
