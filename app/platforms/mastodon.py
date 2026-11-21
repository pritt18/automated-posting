import httpx
from app.platforms.base import BasePlatform
from app.schemas import PlatformResult
from app.config import settings


class MastodonPlatform(BasePlatform):
    """
    Mastodon ActivityPub / REST Statuses API.
    API Docs: https://docs.joinmastodon.org/methods/statuses/#create
    """

    name = "Mastodon"

    async def publish(self, client: httpx.AsyncClient, message: str, cta_url: str) -> PlatformResult:
        if settings.simulation_mode:
            return self.success_result(
                posted_url=f"{settings.mastodon_instance_url.rstrip('/')}/@broadcaster/1119827364510",
                public_access=True
            )

        token = settings.mastodon_access_token
        instance = settings.mastodon_instance_url.rstrip("/")

        if not token:
            return self.failure_result("MASTODON_ACCESS_TOKEN not configured.")

        url = f"{instance}/api/v1/statuses"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        payload = {
            "status": message,
            "visibility": "public"
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
                post_url = data.get("url") or f"{instance}/statuses/{data.get('id')}"
                is_public = data.get("visibility") == "public"
                return self.success_result(posted_url=post_url, public_access=is_public)

            try:
                err_data = response.json()
                err_msg = err_data.get("error", f"Mastodon API error {response.status_code}")
            except Exception:
                err_msg = f"Mastodon HTTP {response.status_code}: {response.text[:120]}"

            return self.failure_result(err_msg)

        except httpx.RequestError as exc:
            return self.failure_result(f"Network error communicating with Mastodon: {str(exc)}")
        except Exception as exc:
            return self.failure_result(f"Unexpected Mastodon error: {str(exc)}")
