from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class GeneratedPitch:
    content: str

    def __post_init__(self) -> None:
        if not self.content.strip() or len(self.content) > 3_000:
            raise ValueError("Generated pitch must contain 1 to 3,000 characters")


@dataclass(frozen=True)
class Pitch:
    id: str
    opportunity_id: str
    content: str
    generated_at: datetime
    updated_at: datetime
