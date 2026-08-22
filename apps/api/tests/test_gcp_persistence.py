from datetime import UTC, datetime

import pytest

from pressradar.domain.clients import ClientDetails
from pressradar.domain.opportunities import OpportunityStatus
from pressradar.infrastructure.firestore import _client, _client_details, _datetime, _key


def test_firestore_client_document_round_trip() -> None:
    details = ClientDetails(
        name="Nadia Rahman",
        company="VertexAI Labs",
        website=None,
        industry="Technology",
        description="AI governance consultancy",
        location="Dubai",
        expertise=("AI governance",),
        spokesperson_name="Nadia Rahman",
        spokesperson_title="Founder",
        keywords=("AI policy",),
        excluded_keywords=(),
        preferred_topics=("regulation",),
        tone="authoritative",
        monitoring_rules=("AI governance",),
    )

    client = _client("client-1", {"workspace_id": "workspace-1", **_client_details(details)})

    assert client.id == "client-1"
    assert client.expertise == ("AI governance",)
    assert client.monitoring_rules == ("AI governance",)


def test_firestore_keys_are_deterministic_and_timestamps_require_datetime() -> None:
    assert _key("client:media") == _key("client:media")
    assert len(_key("client:media")) == 64
    assert _datetime(datetime(2026, 1, 1, tzinfo=UTC)).tzinfo is UTC
    with pytest.raises(ValueError):
        _datetime("2026-01-01")


def test_cloud_status_values_remain_domain_values() -> None:
    assert OpportunityStatus.SENDING.value == "sending"
