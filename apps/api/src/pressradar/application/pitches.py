import re
from typing import Protocol

from pressradar.domain.clients import Client
from pressradar.domain.media import MediaItem
from pressradar.domain.pitches import GeneratedPitch


class PitchGenerationError(Exception):
    """Raised when a pitch provider cannot produce a valid grounded draft."""


class PitchGenerator(Protocol):
    def generate(
        self,
        *,
        client: Client,
        media_item: MediaItem,
    ) -> GeneratedPitch: ...


def validate_generated_pitch(
    pitch: GeneratedPitch, *, client: Client, media_item: MediaItem
) -> GeneratedPitch:
    content = pitch.content.strip()
    sentence_count = len(re.findall(r"[.!?](?:\s|$)", content))
    if not 2 <= sentence_count <= 4:
        raise PitchGenerationError("Generated pitch must contain approximately three sentences")

    client_terms = tuple(
        term
        for term in (
            client.name,
            client.company,
            client.spokesperson_name,
            *client.expertise,
            *client.preferred_topics,
            client.industry,
            client.location,
        )
        if term
    )
    normalized = content.casefold()
    if not any(term.casefold() in normalized for term in client_terms):
        raise PitchGenerationError("Generated pitch does not reference known client context")
    return GeneratedPitch(content=content)
