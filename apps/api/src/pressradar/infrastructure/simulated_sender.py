from pressradar.domain.delivery import DeliveryReceipt, DeliveryRequest


class SimulatedPitchSender:
    def send(self, request: DeliveryRequest) -> DeliveryReceipt:
        return DeliveryReceipt(
            provider="simulated",
            reference=f"simulated:{request.opportunity_id}",
        )
