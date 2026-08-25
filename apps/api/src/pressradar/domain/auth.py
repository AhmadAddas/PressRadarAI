from dataclasses import dataclass
from enum import StrEnum


class WorkspaceKind(StrEnum):
    PROD = "prod"
    DEMO = "demo"


@dataclass(frozen=True)
class Identity:
    user_id: str
    workspace_id: str
    email: str
    name: str
    workspace_kind: WorkspaceKind = WorkspaceKind.PROD
    totp_enabled: bool = False
    onboarding_completed: bool = False
