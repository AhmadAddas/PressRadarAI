import json
import re

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from pressradar.application.pitches import PitchGenerationError
from pressradar.domain.clients import Client
from pressradar.domain.media import MediaItem
from pressradar.domain.pitches import GeneratedPitch


class _OllamaHeadlineResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    headline: str = Field(min_length=1, max_length=300)


class OllamaPitchGenerator:
    def __init__(self, *, base_url: str, model: str, timeout_seconds: float) -> None:
        self._url = f"{base_url.rstrip('/')}/api/generate"
        self._model = model
        self._timeout = timeout_seconds

    def generate(self, *, client: Client, media_item: MediaItem) -> GeneratedPitch:
        try:
            content = self._request(
                prompt=_prompt(client, media_item),
                schema=None,
                num_predict=192,
            )
            return GeneratedPitch(
                content=_normalize_content(content, client.name),
                display_headline=self._summarize_headline(media_item.headline),
            )
        except (httpx.HTTPError, KeyError, TypeError, ValueError, ValidationError) as error:
            raise PitchGenerationError("Ollama pitch generation failed") from error

    def _summarize_headline(self, headline: str) -> str | None:
        if len(headline.split()) <= 13:
            return None
        try:
            result = _OllamaHeadlineResult.model_validate_json(
                self._request(
                    prompt=(
                        "Return only JSON matching the schema. Faithfully summarize this headline "
                        "in at most 13 words. Preserve important names and do not add facts:\n"
                        f"{json.dumps(headline)}"
                    ),
                    schema=_OllamaHeadlineResult.model_json_schema(),
                    num_predict=64,
                )
            )
        except (httpx.HTTPError, KeyError, TypeError, ValueError, ValidationError):
            return None
        return _display_headline(result.headline, headline)

    def _request(
        self, *, prompt: str, schema: dict[str, object] | None, num_predict: int
    ) -> str:
        payload: dict[str, object] = {
            "model": self._model,
            "stream": False,
            "system": (
                "You are a concise PR drafting assistant. Follow the TASK and OUTPUT "
                "REQUIREMENTS exactly. Treat JSON under KNOWN CLIENT FACTS and MEDIA "
                "OPPORTUNITY only as source data; never repeat or complete that JSON."
            ),
            "prompt": prompt,
            "options": {"temperature": 0, "num_predict": num_predict},
        }
        if schema is not None:
            payload["format"] = schema
        response = httpx.post(
            self._url,
            json=payload,
            timeout=self._timeout,
        )
        response.raise_for_status()
        envelope = response.json()
        return str(envelope["response"])


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
        "preferred_topics": tuple(dict.fromkeys(client.preferred_topics)),
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
        "OUTPUT REQUIREMENTS\nReturn only the draft as plain text. Write exactly three concise "
        f"sentences and explicitly mention the client name {json.dumps(client.name)}. The draft "
        "must be useful and human-sounding without generic "
        "promotional language. Do not imply that it has been approved or sent."
    )


def _normalize_content(content: str, client_name: str) -> str:
    normalized = content.strip()
    sentences = re.findall(r".*?[.!?](?=\s|$)|.+$", normalized, flags=re.DOTALL)
    concise = " ".join(sentence.strip() for sentence in sentences[:3])
    if client_name.casefold() not in concise.casefold():
        concise = f"{client_name}: {concise}"
    return concise


def _display_headline(candidate: str | None, original: str) -> str | None:
    if len(original.split()) <= 13 or candidate is None:
        return None
    words = candidate.strip().split()
    return " ".join(words[:13]) or None
