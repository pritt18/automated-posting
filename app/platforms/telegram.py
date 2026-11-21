import httpx
from app.platforms.base import BasePlatform
from app.schemas import PlatformResult
from app.config import settings


class TelegramPlatform(BasePlatform):
    """
    Telegram Bot API integration.
    API Docs: https://core.telegram.org/bots/api#sendmessage
    """

    name = "Telegram"

    async def publish(self, client: httpx.AsyncClient, message: str, cta_url: str) -> PlatformResult:
        if settings.simulation_mode:
            return self.success_result(
                posted_url=f"https://t.me/{settings.telegram_channel_username or 'dx_broadcast'}/1042",
                public_access=True
            )

        token = settings.telegram_bot_token
        chat_id = settings.telegram_chat_id

        if not token or not chat_id:
            return self.failure_result("TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not configured.")

        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": message,
            "disable_web_page_preview": False
        }

        try:
            response = await client.post(url, json=payload, timeout=settings.request_timeout_seconds)
            data = response.json()

            if response.status_code == 200 and data.get("ok"):
                result_obj = data.get("result", {})
                message_id = result_obj.get("message_id")
                chat_info = result_obj.get("chat", {})
                username = chat_info.get("username") or settings.telegram_channel_username

                if username:
                    posted_url = f"https://t.me/{username}/{message_id}"
                    is_public = True
                else:
                    posted_url = f"https://web.telegram.org/a/#{chat_id}"
                    is_public = False

                return self.success_result(posted_url=posted_url, public_access=is_public)

            description = data.get("description", f"Telegram API error {response.status_code}")
            return self.failure_result(description)

        except httpx.RequestError as exc:
            return self.failure_result(f"Network error communicating with Telegram: {str(exc)}")
        except Exception as exc:
            return self.failure_result(f"Unexpected Telegram error: {str(exc)}")
