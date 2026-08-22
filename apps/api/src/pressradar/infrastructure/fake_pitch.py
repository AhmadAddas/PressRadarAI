from pressradar.domain.clients import Client
from pressradar.domain.media import MediaItem
from pressradar.domain.pitches import GeneratedPitch


class FakePitchGenerator:
    def generate(self, *, client: Client, media_item: MediaItem) -> GeneratedPitch:
        spokesperson = client.spokesperson_name or client.name
        expertise = (
            client.expertise[0]
            if client.expertise
            else (client.monitoring_rules[0] if client.monitoring_rules else "the requested topic")
        )
        headline = media_item.headline.rstrip(".!?")
        article = "an" if expertise[0].casefold() in "aeiou" else "a"
        return GeneratedPitch(
            content=(
                f"{headline} raises practical questions for organizations responding to change. "
                f"From {article} {expertise} perspective, clear ownership and proportionate "
                "processes can help teams keep implementation practical. "
                f"{spokesperson} of {client.company} can tailor this draft with verified examples "
                "before it is shared."
            )
        )
