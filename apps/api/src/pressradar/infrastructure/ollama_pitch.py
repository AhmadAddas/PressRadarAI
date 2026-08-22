import json

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from pressradar.application.pitches import PitchGenerationError
from pressradar.domain.clients import Client
from pressradar.domain.media import MediaItem
from pressradar.domain.pitches import GeneratedPitch


class _OllamaPitchResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content: str = Field(min_length=1, max_length=3_000)


class OllamaPitchGenerator:
    def __init__(self, *, base_url: str, model: str, timeout_seconds: float) -> None:
        self._url = f"{base_url.rstrip('/')}/api/generate"
        self._model = model
        self._timeout = timeout_seconds

    def generate(self, *, client: Client, media_item: MediaItem) -> GeneratedPitch:
        try:
            response = httpx.post(
                self._url,
                json={
                    "model": self._model,
                    "stream": False,
                    "format": _OllamaPitchResult.model_json_schema(),
                    "prompt": _prompt(client, media_item),
                },
                timeout=self._timeout,
            )
            response.raise_for_status()
            envelope = response.json()
            result = _OllamaPitchResult.model_validate_json(envelope["response"])
            return GeneratedPitch(content=result.content.strip())
        except (httpx.HTTPError, KeyError, TypeError, ValueError, ValidationError) as error:
            raise PitchGenerationError("Ollama pitch generation failed") from error


def _prompt(client: Client, media_item: MediaItem) -> str:
    known_facts = {
        "name": client.name,
        "company": client.company,
        "industry": client.industry,
        "description": client.description,
        "location": client.location,
        "expertise": client.expertise,
        "spokesperson_name": client.spokesperson_name,
        "spokesperson_title": client.spokesperson_title,
        "preferred_topics": client.preferred_topics,
        "tone": client.tone,
    }
    opportunity = {
        "source": media_item.source,
        "source_type": media_item.source_type,
        "headline": media_item.headline,
        "body": media_item.body,
        "journalist": media_item.journalist,
        "deadline": None if media_item.deadline is None else media_item.deadline.isoformat(),
        "topics": media_item.topics,
    }
    return (
        "KNOWN CLIENT FACTS\n"
        f"{json.dumps(known_facts)}\n\n"
        "MEDIA OPPORTUNITY\n"
        f"{json.dumps(opportunity)}\n\n"
        "TASK\nDraft expert commentary for human review. Address the actual request and use "
        "only the known client facts. Never invent revenue, funding, customers, partnerships, "
        "credentials, experience, titles, locations, statistics, quotes, or approvals. If the "
        "facts are limited, remain conservative.\n\n"
        "OUTPUT REQUIREMENTS\nReturn only JSON matching the schema. The content should be "
        "approximately three strong, concise, useful, human-sounding sentences without generic "
        "promotional language. Do not imply that it has been approved or sent."
    )
