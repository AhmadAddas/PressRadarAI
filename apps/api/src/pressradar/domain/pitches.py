from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class GeneratedPitch:
    content: str
    display_headline: str | None = None

    def __post_init__(self) -> None:
        if not self.content.strip() or len(self.content) > 3_000:
            raise ValueError("Generated pitch must contain 1 to 3,000 characters")
        if self.display_headline is not None and not self.display_headline.strip():
            raise ValueError("Display headline cannot be blank")


@dataclass(frozen=True)
class Pitch:
    id: str
    opportunity_id: str
    content: str
    generated_at: datetime
    updated_at: datetime
