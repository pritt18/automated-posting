import httpx
from app.platforms.base import BasePlatform
from app.schemas import PlatformResult
from app.config import settings


class SlackPlatform(BasePlatform):
    """
    Slack Incoming Webhook integration.
    API Docs: https://api.slack.com/messaging/webhooks
    """

    name = "Slack"

    async def publish(self, client: httpx.AsyncClient, message: str, cta_url: str) -> PlatformResult:
        if settings.simulation_mode:
            return self.success_result(
                posted_url="https://app.slack.com/client/T012345678/C012345678",
                public_access=False
            )

        webhook_url = settings.slack_webhook_url
        if not webhook_url:
            return self.failure_result("SLACK_WEBHOOK_URL not configured.")

        payload = {
            "text": message
        }

        try:
            response = await client.post(
                webhook_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=settings.request_timeout_seconds
            )

            # Slack webhooks respond with HTTP 200 and raw body 'ok'
            if response.status_code == 200 and response.text.strip().lower() == "ok":
                # Slack workspaces are private team channels
                return self.success_result(
                    posted_url="https://app.slack.com/client",
                    public_access=False
                )

            return self.failure_result(f"Slack rejected payload: {response.text.strip()}")

        except httpx.RequestError as exc:
            return self.failure_result(f"Network error communicating with Slack: {str(exc)}")
        except Exception as exc:
            return self.failure_result(f"Unexpected Slack error: {str(exc)}")
