from __future__ import annotations

from pydantic import BaseModel


class StartSessionResponse(BaseModel):
    thread_id: str


class StartConsultationRequest(BaseModel):
    patient_case: str
    thread_id: str | None = None


class ResumeConsultationRequest(BaseModel):
    thread_id: str
    answer: str


class ConsultationResponse(BaseModel):
    thread_id: str
    status: str
    interrupt: dict | None = None
    state: dict | None = None
    final_report: str | None = None
