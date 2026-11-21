import httpx
from app.platforms.base import BasePlatform
from app.schemas import PlatformResult
from app.config import settings


class DiscordPlatform(BasePlatform):
    """
    Discord Webhook API integration.
    API Docs: https://discord.com/developers/docs/resources/webhook#execute-webhook
    """

    name = "Discord"

    async def publish(self, client: httpx.AsyncClient, message: str, cta_url: str) -> PlatformResult:
        if settings.simulation_mode:
            return self.success_result(
                posted_url="https://discord.com/channels/1122334455/6677889900/1234567890123456",
                public_access=True
            )

        webhook_url = settings.discord_webhook_url
        if not webhook_url:
            return self.failure_result("DISCORD_WEBHOOK_URL not configured.")

        # Ensure ?wait=true parameter is present so Discord returns the created message ID
        target_url = webhook_url
        if "?" in target_url:
            if "wait=true" not in target_url:
                target_url += "&wait=true"
        else:
            target_url += "?wait=true"

        payload = {
            "content": message
        }

        try:
            response = await client.post(
                target_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=settings.request_timeout_seconds
            )

            if response.status_code in (200, 204):
                if response.status_code == 200:
                    data = response.json()
                    channel_id = data.get("channel_id")
                    message_id = data.get("id")
                    guild_id = data.get("guild_id", "@me")
                    posted_url = f"https://discord.com/channels/{guild_id}/{channel_id}/{message_id}"
                else:
                    # 204 No Content returned if wait parameter was omitted
                    posted_url = webhook_url.split("?")[0]

                return self.success_result(posted_url=posted_url, public_access=True)

            try:
                err_data = response.json()
                err_msg = err_data.get("message", f"Discord HTTP status {response.status_code}")
            except Exception:
                err_msg = f"Discord HTTP status {response.status_code}: {response.text[:120]}"

            return self.failure_result(err_msg)

        except httpx.RequestError as exc:
            return self.failure_result(f"Network error communicating with Discord: {str(exc)}")
        except Exception as exc:
            return self.failure_result(f"Unexpected Discord error: {str(exc)}")
