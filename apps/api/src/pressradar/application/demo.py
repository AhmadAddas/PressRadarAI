from dataclasses import dataclass

from pressradar.application.clients import ClientService
from pressradar.application.media import MediaIngestionService
from pressradar.application.opportunities import OpportunityService
from pressradar.domain.clients import ClientDetails


@dataclass(frozen=True)
class DemoSetupResult:
    clients_created: int
    media_created: int
    opportunities_created: int


class DemoSetupService:
    def __init__(
        self,
        clients: ClientService,
        media: MediaIngestionService,
        opportunities: OpportunityService,
    ) -> None:
        self._clients = clients
        self._media = media
        self._opportunities = opportunities

    def setup(self, *, workspace_id: str) -> DemoSetupResult:
        self._opportunities.clear(workspace_id=workspace_id)
        self._media.clear(workspace_id=workspace_id)
        existing = {
            (client.name.casefold(), client.company.casefold())
            for client in self._clients.list(workspace_id=workspace_id)
        }
        clients_created = 0
        for details in _DEMO_CLIENTS:
            key = (details.name.casefold(), details.company.casefold())
            if key not in existing:
                self._clients.create(workspace_id=workspace_id, details=details)
                existing.add(key)
                clients_created += 1

        return DemoSetupResult(
            clients_created=clients_created,
            media_created=0,
            opportunities_created=0,
        )


_DEMO_CLIENTS = (
    ClientDetails(
        name="Nadia Rahman",
        company="VertexAI Labs",
        website=None,
        industry="Artificial Intelligence",
        description="Founder helping organizations adopt AI responsibly.",
        location="Dubai",
        expertise=("AI governance", "AI startup growth", "Enterprise AI adoption"),
        spokesperson_name="Nadia Rahman",
        spokesperson_title="Founder & CEO",
        keywords=("UAE technology ecosystem",),
        excluded_keywords=(),
        preferred_topics=("AI governance",),
        tone="Clear and practical",
        monitoring_rules=("Dubai AI founders",),
    ),
    ClientDetails(
        name="Mariam Al Noor",
        company="GulfFin Advisory",
        website=None,
        industry="Financial Services",
        description="Advises financial institutions on digital operating models.",
        location="Abu Dhabi",
        expertise=("digital banking",),
        spokesperson_name="Mariam Al Noor",
        spokesperson_title="Managing Director",
        keywords=(),
        excluded_keywords=(),
        preferred_topics=(),
        tone="Authoritative and concise",
        monitoring_rules=(),
    ),
    ClientDetails(
        name="Samir Qureshi",
        company="LaunchBridge",
        website=None,
        industry="Venture Capital",
        description="Supports early-stage enterprise technology companies.",
        location="Abu Dhabi",
        expertise=("startup funding", "enterprise technology"),
        spokesperson_name="Samir Qureshi",
        spokesperson_title="General Partner",
        keywords=(),
        excluded_keywords=(),
        preferred_topics=(),
        tone="Direct and evidence-led",
        monitoring_rules=(),
    ),
)
