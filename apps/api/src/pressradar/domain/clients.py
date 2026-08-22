from dataclasses import dataclass


@dataclass(frozen=True)
class Client:
    id: str
    workspace_id: str
    name: str
    company: str
    website: str | None
    industry: str | None
    description: str | None
    location: str | None
    expertise: tuple[str, ...]
    spokesperson_name: str | None
    spokesperson_title: str | None
    keywords: tuple[str, ...]
    excluded_keywords: tuple[str, ...]
    preferred_topics: tuple[str, ...]
    tone: str | None
    monitoring_rules: tuple[str, ...]


@dataclass(frozen=True)
class ClientDetails:
    name: str
    company: str
    website: str | None
    industry: str | None
    description: str | None
    location: str | None
    expertise: tuple[str, ...]
    spokesperson_name: str | None
    spokesperson_title: str | None
    keywords: tuple[str, ...]
    excluded_keywords: tuple[str, ...]
    preferred_topics: tuple[str, ...]
    tone: str | None
    monitoring_rules: tuple[str, ...]
