import asyncio
import logging
from typing import List
import httpx

from app.platforms.base import BasePlatform
from app.platforms.telegram import TelegramPlatform
from app.platforms.discord import DiscordPlatform
from app.platforms.slack import SlackPlatform
from app.platforms.mastodon import MastodonPlatform
from app.platforms.devto import DevToPlatform
from app.schemas import PlatformResult, PostingResponse
from app.config import settings

logger = logging.getLogger("automated_posting.service")


class PostingService:
    """
    Orchestrates broadcast distribution across multiple third-party platforms concurrently.
    Guarantees isolation: failure in any single platform does not interrupt the rest.
    """

    def __init__(self, platforms: List[BasePlatform] = None):
        self.platforms: List[BasePlatform] = platforms or [
            TelegramPlatform(),
            DiscordPlatform(),
            SlackPlatform(),
            MastodonPlatform(),
            DevToPlatform(),
        ]

    async def _safe_publish(
        self,
        platform: BasePlatform,
        client: httpx.AsyncClient,
        message: str,
        cta_url: str
    ) -> PlatformResult:
        try:
            return await platform.publish(client, message, cta_url)
        except Exception as exc:
            logger.error("Unhandled exception publishing to %s: %s", platform.name, exc, exc_info=True)
            return platform.failure_result(f"Internal publishing error: {str(exc)}")

    async def broadcast(self, message: str, cta_url: str) -> PostingResponse:
        limits = httpx.Limits(max_keepalive_connections=10, max_connections=20)
        timeout = httpx.Timeout(settings.request_timeout_seconds)

        async with httpx.AsyncClient(limits=limits, timeout=timeout) as client:
            tasks = [
                self._safe_publish(platform, client, message, cta_url)
                for platform in self.platforms
            ]
            # Run all platform posts concurrently
            raw_results = await asyncio.gather(*tasks, return_exceptions=True)

        results: List[PlatformResult] = []
        for i, res in enumerate(raw_results):
            if isinstance(res, Exception):
                platform_name = self.platforms[i].name
                results.append(
                    PlatformResult(
                        platform=platform_name,
                        status="failed",
                        posted_url=None,
                        public_access=False,
                        date=None,
                        time=None,
                        error=str(res)
                    )
                )
            else:
                results.append(res)

        overall_success = any(r.status == "success" for r in results)

        return PostingResponse(
            success=overall_success,
            results=results
        )


posting_service = PostingService()
