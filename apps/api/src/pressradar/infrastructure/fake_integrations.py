from pressradar.application.integrations import OpportunityAlert, SentOpportunityActivity


class FakeNotificationSender:
    def send(self, alert: OpportunityAlert) -> None:
        pass


class FakeCRMIntegration:
    def record_sent(self, activity: SentOpportunityActivity) -> None:
        pass
