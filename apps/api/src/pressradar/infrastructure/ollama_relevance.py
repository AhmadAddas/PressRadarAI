import json

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from pressradar.application.relevance import RelevanceAnalysisError
from pressradar.domain.clients import Client
from pressradar.domain.media import MediaItem
from pressradar.domain.relevance import RelevanceAnalysis


class _OllamaResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    score: int = Field(ge=0, le=100)
    reason: str = Field(min_length=1, max_length=2_000)


def _ollama_format_schema() -> dict[str, object]:
    schema = _OllamaResult.model_json_schema()
    properties = schema.get("properties", {})
    if isinstance(properties, dict):
        for value in properties.values():
            if not isinstance(value, dict):
                continue
            for constraint in ("minLength", "maxLength", "minItems", "maxItems"):
                value.pop(constraint, None)
    return schema


class OllamaRelevanceAnalyzer:
    def __init__(self, *, base_url: str, model: str, timeout_seconds: float) -> None:
        self._url = f"{base_url.rstrip('/')}/api/generate"
        self._model = model
        self._timeout = timeout_seconds

    def analyze(
        self,
        *,
        client: Client,
        media_item: MediaItem,
        matched_topics: tuple[str, ...],
    ) -> RelevanceAnalysis:
        try:
            response = httpx.post(
                self._url,
                json={
                    "model": self._model,
                    "stream": False,
                    # Ollama converts this schema to a grammar. Large repetition
                    # bounds are rejected by some versions before inference, so
                    # length limits remain enforced when parsing the response.
                    "format": _ollama_format_schema(),
                    "prompt": _prompt(client, media_item, matched_topics),
                },
                timeout=self._timeout,
            )
            response.raise_for_status()
            envelope = response.json()
            result = _OllamaResult.model_validate_json(envelope["response"])
            return RelevanceAnalysis(
                score=result.score,
                reason=result.reason.strip(),
                matched_topics=matched_topics,
            )
        except (httpx.HTTPError, KeyError, TypeError, ValueError, ValidationError) as error:
            raise RelevanceAnalysisError("Ollama relevance analysis failed") from error


def _prompt(client: Client, media_item: MediaItem, matched_topics: tuple[str, ...]) -> str:
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
    }
    opportunity = {
        "source": media_item.source,
        "source_type": media_item.source_type,
        "headline": media_item.headline,
        "body": media_item.body,
        "journalist": media_item.journalist,
        "deadline": None if media_item.deadline is None else media_item.deadline.isoformat(),
        "candidate_matched_topics": matched_topics,
    }
    return (
        "KNOWN CLIENT FACTS\n"
        f"{json.dumps(known_facts)}\n\n"
        "MEDIA OPPORTUNITY\n"
        f"{json.dumps(opportunity)}\n\n"
        "TASK\nScore how relevant and actionable this media opportunity is for the client. "
        "Use only the known client facts. Never invent credentials, customers, funding, "
        "experience, statistics, or quotes.\n\n"
        "OUTPUT REQUIREMENTS\nReturn only JSON matching the provided schema with a 0-100 "
        "score and a concise factual reason. PressRadar retains the supplied candidate topics."
    )
