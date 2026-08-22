import httpx

from pressradar.application.integrations import CRMSyncError, SentOpportunityActivity


class HubSpotCRMIntegration:
    def __init__(
        self,
        *,
        access_token: str,
        timeout_seconds: float,
        client: httpx.Client | None = None,
    ) -> None:
        self._access_token = access_token
        self._client = client or httpx.Client(timeout=timeout_seconds)

    def record_sent(self, activity: SentOpportunityActivity) -> None:
        try:
            response = self._client.post(
                "https://api.hubapi.com/crm/v3/objects/notes",
                headers={"Authorization": f"Bearer {self._access_token}"},
                json={
                    "properties": {
                        "hs_timestamp": activity.sent_at.isoformat(),
                        "hs_note_body": (
                            f"PressRadar sent opportunity {activity.opportunity_id} for "
                            f"{activity.client_name} at {activity.client_company}: "
                            f"{activity.headline}"
                        ),
                    }
                },
            )
            response.raise_for_status()
        except httpx.HTTPError as error:
            raise CRMSyncError("HubSpot synchronization failed") from error
