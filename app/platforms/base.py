from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional
import httpx

from app.schemas import PlatformResult
from app.config import settings


class BasePlatform(ABC):
    """
    Abstract base class for third-party publishing integrations.
    Each platform implements its own API protocol and payload structures.
    """

    name: str = "BasePlatform"

    @abstractmethod
    async def publish(self, client: httpx.AsyncClient, message: str, cta_url: str) -> PlatformResult:
        """
        Send the broadcast message to the target platform.
        Must return a structured PlatformResult.
        """
        pass

    def get_timestamp(self) -> tuple[str, str]:
        """Returns current date (YYYY-MM-DD) and time (HH:MM:SS)."""
        now = datetime.now()
        return now.strftime("%Y-%m-%d"), now.strftime("%H:%M:%S")

    def success_result(self, posted_url: str, public_access: bool = True) -> PlatformResult:
        post_date, post_time = self.get_timestamp()
        return PlatformResult(
            platform=self.name,
            status="success",
            posted_url=posted_url,
            public_access=public_access,
            date=post_date,
            time=post_time,
            error=None
        )

    def failure_result(self, error_message: str) -> PlatformResult:
        return PlatformResult(
            platform=self.name,
            status="failed",
            posted_url=None,
            public_access=False,
            date=None,
            time=None,
            error=error_message
        )
