import httpx
from app.platforms.base import BasePlatform
from app.schemas import PlatformResult
from app.config import settings


class DevToPlatform(BasePlatform):
    """
    Dev.to / Forem Publishing API.
    API Docs: https://developers.forem.com/api/v1#tag/articles/operation/createArticle
    """

    name = "Dev.to"

    async def publish(self, client: httpx.AsyncClient, message: str, cta_url: str) -> PlatformResult:
        if settings.simulation_mode:
            return self.success_result(
                posted_url="https://dev.to/community/announcement-update-29384",
                public_access=True
            )

        api_key = settings.devto_api_key
        if not api_key:
            return self.failure_result("DEVTO_API_KEY not configured.")

        url = "https://dev.to/api/articles"
        headers = {
            "api-key": api_key,
            "Content-Type": "application/json"
        }

        # Formulate a clean broadcast post title and body
        title = message[:50].rsplit(" ", 1)[0] if len(message) > 50 else message
        title = title.replace("\n", " ").strip()
        if not title:
            title = "Platform Broadcast Announcement"

        body_markdown = f"{message}\n\nCTA: [{cta_url}]({cta_url})"

        payload = {
            "article": {
                "title": title,
                "published": True,
                "body_markdown": body_markdown,
                "tags": ["updates", "broadcast"]
            }
        }

        try:
            response = await client.post(
                url,
                json=payload,
                headers=headers,
                timeout=settings.request_timeout_seconds
            )

            if response.status_code in (200, 201):
                data = response.json()
                article_url = data.get("url") or f"https://dev.to/articles/{data.get('id')}"
                return self.success_result(posted_url=article_url, public_access=True)

            try:
                err_data = response.json()
                err_msg = err_data.get("error", f"Dev.to API error {response.status_code}")
            except Exception:
                err_msg = f"Dev.to HTTP {response.status_code}: {response.text[:120]}"

            return self.failure_result(err_msg)

        except httpx.RequestError as exc:
            return self.failure_result(f"Network error communicating with Dev.to: {str(exc)}")
        except Exception as exc:
            return self.failure_result(f"Unexpected Dev.to error: {str(exc)}")
