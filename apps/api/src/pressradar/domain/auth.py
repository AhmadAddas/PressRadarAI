from dataclasses import dataclass


@dataclass(frozen=True)
class Identity:
    user_id: str
    workspace_id: str
    email: str
    name: str
