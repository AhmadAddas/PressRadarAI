import json
import re
from collections.abc import Iterator
from dataclasses import dataclass
from threading import RLock
from typing import Any

import httpx
from pydantic import BaseModel, ConfigDict, ValidationError

from pressradar.application.pitches import PitchGenerationError
from pressradar.application.relevance import RelevanceAnalysisError
from pressradar.domain.clients import Client
from pressradar.domain.media import MediaItem
from pressradar.domain.pitches import GeneratedPitch
from pressradar.domain.relevance import RelevanceAnalysis
from pressradar.infrastructure.ollama_pitch import OllamaPitchGenerator
from pressradar.infrastructure.ollama_relevance import OllamaRelevanceAnalyzer

MODEL_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]*(?::[A-Za-z0-9][A-Za-z0-9._-]*)?$")
RECOMMENDED_MODEL = "qwen2.5:0.5b-instruct"
RECOMMENDATION = (
    "Qwen2.5 0.5B Instruct is about 398 MB in Ollama and is a practical starting "
    "point for a low-power VPS. Smaller models trade accuracy for lower memory use."
)


class LocalAIError(Exception):
    """Raised when local model management cannot complete safely."""


class _TranslationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    translations: list[str]


@dataclass(frozen=True)
class LicenseDetails:
    name: str
    summary: str
    source_url: str | None
    known: bool


@dataclass(frozen=True)
class LocalAIStatus:
    enabled: bool
    reachable: bool
    model_available: bool
    installed_models: tuple[str, ...]
    model: str
    license: LicenseDetails
    recommended_model: str = RECOMMENDED_MODEL
    recommendation: str = RECOMMENDATION


class OllamaRuntime:
    """Switchable Ollama adapter for AI execution and model management."""

    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        timeout_seconds: float,
        enabled: bool,
        client: httpx.Client | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = validate_model_name(model)
        self._timeout_seconds = timeout_seconds
        self._enabled = enabled
        self._client = client or httpx.Client(timeout=timeout_seconds)
        self._lock = RLock()

    def analyze(
        self,
        *,
        client: Client,
        media_item: MediaItem,
        matched_topics: tuple[str, ...],
    ) -> RelevanceAnalysis:
        with self._lock:
            if not self._enabled:
                raise RelevanceAnalysisError("Local AI is deactivated")
            model = self._model
        return OllamaRelevanceAnalyzer(
            base_url=self._base_url,
            model=model,
            timeout_seconds=self._timeout_seconds,
        ).analyze(client=client, media_item=media_item, matched_topics=matched_topics)

    def generate(self, *, client: Client, media_item: MediaItem) -> GeneratedPitch:
        with self._lock:
            if not self._enabled:
                raise PitchGenerationError("Local AI is deactivated")
            model = self._model
        return OllamaPitchGenerator(
            base_url=self._base_url,
            model=model,
            timeout_seconds=self._timeout_seconds,
        ).generate(client=client, media_item=media_item)

    def translate(self, *, texts: tuple[str, ...], language_code: str) -> tuple[str, ...]:
        with self._lock:
            if not self._enabled:
                raise LocalAIError("Activate Local AI before translating")
            model = self._model
        try:
            response = self._client.post(
                f"{self._base_url}/api/generate",
                json={
                    "model": model,
                    "stream": False,
                    "format": _TranslationResult.model_json_schema(),
                    "prompt": (
                        f"Translate each JSON string into language code {language_code}. "
                        "Preserve names, numbers, placeholders, punctuation, and item order. "
                        "Return only JSON matching the schema with exactly one translation per "
                        f"input. INPUT: {json.dumps(texts)}"
                    ),
                },
                timeout=self._timeout_seconds,
            )
            response.raise_for_status()
            envelope = response.json()
            result = _TranslationResult.model_validate_json(envelope["response"])
            translations = tuple(value.strip() for value in result.translations)
            if len(translations) != len(texts) or any(not value for value in translations):
                raise LocalAIError("Local AI returned an incomplete translation")
            return translations
        except (httpx.HTTPError, KeyError, TypeError, ValueError, ValidationError) as error:
            raise LocalAIError("Local AI translation failed") from error

    def status(self) -> LocalAIStatus:
        with self._lock:
            enabled = self._enabled
            model = self._model
        reachable, installed_models = self._ollama_status()
        return LocalAIStatus(
            enabled=enabled,
            reachable=reachable,
            model_available=model in installed_models,
            installed_models=installed_models,
            model=model,
            license=self.inspect_license(model),
        )

    def inspect_license(self, model: str) -> LicenseDetails:
        model = validate_model_name(model)
        ollama_license = self._ollama_license(model)
        try:
            response = self._client.get(
                "https://huggingface.co/api/models",
                params={"search": _model_family(model), "limit": 10, "full": "true"},
                timeout=self._timeout_seconds,
            )
            response.raise_for_status()
            match = _select_hugging_face_model(model, response.json())
            if match is not None:
                license_name = _license_from_hugging_face(match)
                if license_name:
                    repository = str(match.get("id", ""))
                    return license_details(
                        license_name,
                        f"https://huggingface.co/{repository}" if repository else None,
                    )
        except (httpx.HTTPError, TypeError, ValueError):
            pass
        if ollama_license:
            return license_details(ollama_license, None)
        return license_details("Unknown", None)

    def pull_model(self, model: str, accepted_license: str, *, activate: bool) -> LocalAIStatus:
        model = validate_model_name(model)
        license_info = self.inspect_license(model)
        if accepted_license != license_info.name:
            raise LocalAIError("The model license changed; review it again before downloading")
        try:
            response = self._client.post(
                f"{self._base_url}/api/pull",
                json={"model": model, "stream": False},
                timeout=max(self._timeout_seconds, 900),
            )
            response.raise_for_status()
        except httpx.HTTPError as error:
            raise LocalAIError("Ollama could not download this model") from error
        with self._lock:
            if activate:
                self._model = model
                self._enabled = True
        return self.status()

    def validate_pull(self, model: str, accepted_license: str) -> str:
        model = validate_model_name(model)
        if accepted_license != self.inspect_license(model).name:
            raise LocalAIError("The model license changed; review it again before downloading")
        return model

    def pull_model_events(self, model: str, *, activate: bool) -> Iterator[dict[str, Any]]:
        try:
            with self._client.stream(
                "POST",
                f"{self._base_url}/api/pull",
                json={"model": model, "stream": True},
                timeout=max(self._timeout_seconds, 900),
            ) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    if not line:
                        continue
                    event = json.loads(line)
                    if isinstance(event, dict):
                        yield event
                        if event.get("error"):
                            return
        except (httpx.HTTPError, json.JSONDecodeError):
            yield {"error": "Ollama could not download this model"}
            return
        with self._lock:
            if activate:
                self._model = model
                self._enabled = True
        yield {"done": True}

    def activate_model(self, model: str) -> LocalAIStatus:
        model = validate_model_name(model)
        reachable, installed = self._ollama_status()
        if not reachable or model not in installed:
            raise LocalAIError("Clone this Ollama model before activating it")
        with self._lock:
            self._model = model
            self._enabled = True
        return self.status()

    def delete_model(self, model: str) -> LocalAIStatus:
        model = validate_model_name(model)
        try:
            response = self._client.request(
                "DELETE",
                f"{self._base_url}/api/delete",
                json={"model": model},
                timeout=self._timeout_seconds,
            )
            response.raise_for_status()
        except httpx.HTTPError as error:
            raise LocalAIError("Ollama could not delete this model") from error
        with self._lock:
            if self._model == model:
                self._enabled = False
        return self.status()

    def activate(self) -> LocalAIStatus:
        reachable, installed = self._ollama_status()
        with self._lock:
            if not reachable or self._model not in installed:
                raise LocalAIError("Clone the configured Ollama model before activating Local AI")
            self._enabled = True
        return self.status()

    def deactivate(self) -> LocalAIStatus:
        with self._lock:
            self._enabled = False
        return self.status()

    def _ollama_status(self) -> tuple[bool, tuple[str, ...]]:
        try:
            response = self._client.get(f"{self._base_url}/api/tags", timeout=self._timeout_seconds)
            response.raise_for_status()
            models = response.json().get("models", [])
            installed = tuple(
                name
                for item in models
                if isinstance(item, dict)
                for name in (item.get("name") or item.get("model"),)
                if isinstance(name, str)
            )
            return True, installed
        except (httpx.HTTPError, TypeError, ValueError):
            return False, ()

    def _ollama_license(self, model: str) -> str | None:
        try:
            response = self._client.post(
                f"{self._base_url}/api/show",
                json={"model": model},
                timeout=self._timeout_seconds,
            )
            if response.status_code == 404:
                return None
            response.raise_for_status()
            value = response.json().get("license")
            return _license_heading(value) if isinstance(value, str) else None
        except (httpx.HTTPError, TypeError, ValueError):
            return None


def validate_model_name(model: str) -> str:
    normalized = model.strip()
    if len(normalized) > 200 or not MODEL_PATTERN.fullmatch(normalized):
        raise LocalAIError("Enter a valid Ollama model name, such as qwen2.5:0.5b-instruct")
    return normalized


def license_details(name: str, source_url: str | None) -> LicenseDetails:
    normalized = name.strip()
    key = normalized.casefold().replace("_", "-")
    summaries = {
        "apache-2.0": (
            "Apache 2.0 generally permits commercial use, modification, and distribution, "
            "with notice and patent-license obligations."
        ),
        "mit": (
            "The MIT license broadly permits use, modification, and distribution when the "
            "copyright and license notice are retained."
        ),
        "llama3.2": (
            "The Llama 3.2 Community License permits many uses but includes attribution, "
            "acceptable-use, and scale-related conditions that should be reviewed."
        ),
    }
    summary = summaries.get(key)
    if summary is None:
        return LicenseDetails(
            name=normalized or "Unknown",
            summary=(
                "No recognized license summary is available. Search the model publisher's "
                "page and review the full license before downloading or using it."
            ),
            source_url=source_url,
            known=False,
        )
    return LicenseDetails(
        name=normalized,
        summary=summary,
        source_url=source_url,
        known=True,
    )


def _model_family(model: str) -> str:
    return model.split(":", 1)[0].split("/", 1)[-1]


def _select_hugging_face_model(model: str, payload: Any) -> dict[str, Any] | None:
    if not isinstance(payload, list):
        return None
    family = _model_family(model).casefold().replace(".", "")
    size = model.partition(":")[2].split("-", 1)[0].casefold().replace(".", "")
    candidates = [item for item in payload if isinstance(item, dict)]
    for item in candidates:
        identifier = str(item.get("id", "")).casefold().replace(".", "")
        if family in identifier and (not size or size in identifier):
            return item
    return None


def _license_from_hugging_face(model: dict[str, Any]) -> str | None:
    card_data = model.get("cardData")
    if isinstance(card_data, dict) and isinstance(card_data.get("license"), str):
        return str(card_data["license"])
    tags = model.get("tags")
    if isinstance(tags, list):
        for tag in tags:
            if isinstance(tag, str) and tag.startswith("license:"):
                return tag.removeprefix("license:")
    return None


def _license_heading(value: str) -> str | None:
    first_line = next((line.strip() for line in value.splitlines() if line.strip()), "")
    if "apache" in first_line.casefold():
        return "apache-2.0"
    if first_line.casefold() == "mit license" or first_line.casefold() == "mit":
        return "mit"
    return first_line[:100] or None
