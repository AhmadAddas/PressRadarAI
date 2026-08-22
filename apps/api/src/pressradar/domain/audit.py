from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class AuditAction(StrEnum):
    OPPORTUNITY_DETECTED = "opportunity_detected"
    ANALYSIS_STARTED = "analysis_started"
    ANALYSIS_COMPLETED = "analysis_completed"
    PITCH_GENERATED = "pitch_generated"
    PITCH_EDITED = "pitch_edited"
    PITCH_APPROVED = "pitch_approved"
    PITCH_SENT = "pitch_sent"
    OPPORTUNITY_DISMISSED = "opportunity_dismissed"
    PROCESSING_FAILED = "processing_failed"
    SEND_FAILED = "send_failed"
    INTEGRATION_SYNC_FAILED = "integration_sync_failed"


@dataclass(frozen=True)
class AuditEvent:
    id: str
    opportunity_id: str
    action: AuditAction
    occurred_at: datetime
    detail: str | None
