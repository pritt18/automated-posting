import pytest
from unittest.mock import AsyncMock
import httpx
from app.schemas import PlatformResult, PostingRequest
from app.platforms.telegram import TelegramPlatform
from app.platforms.discord import DiscordPlatform
from app.platforms.slack import SlackPlatform
from app.platforms.mastodon import MastodonPlatform
from app.platforms.devto import DevToPlatform
from app.services.posting_service import PostingService


class TestInputValidation:
    """Verifies input validation constraints on the /posting endpoint."""

    def test_valid_request(self, client, enable_simulation):
        payload = {
            "message": "Check out our latest business platform and grow your online visibility. https://example.com"
        }
        response = client.post("/posting", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["results"]) == 5

    def test_message_exceeds_200_characters(self, client):
        long_message = (
            "This is an intentionally long announcement message that clearly exceeds the maximum allowed length of two "
            "hundred characters by appending extra descriptive sentences and repetitive text phrases to test limits. https://example.com"
        )
        assert len(long_message) > 200

        response = client.post("/posting", json={"message": long_message})
        assert response.status_code == 422
        body = response.json()
        assert "must not exceed 200 characters" in str(body)

    def test_message_without_cta_link(self, client):
        message = "Check out our latest business platform and grow your online visibility."
        response = client.post("/posting", json={"message": message})
        assert response.status_code == 422
        body = response.json()
        assert "exactly one CTA link" in str(body)

    def test_message_with_multiple_cta_links(self, client):
        message = "Visit https://platform-one.com and also check https://platform-two.com today!"
        response = client.post("/posting", json={"message": message})
        assert response.status_code == 422
        body = response.json()
        assert "2 were found" in str(body)

    def test_message_with_invalid_url(self, client):
        message = "Check out our tool at ftp://invalid-server"
        response = client.post("/posting", json={"message": message})
        assert response.status_code == 422
        body = response.json()
        assert "Invalid URL scheme" in str(body)

    def test_message_empty(self, client):
        response = client.post("/posting", json={"message": "   "})
        assert response.status_code == 422

    def test_trailing_punctuation_in_cta_link(self):
        req = PostingRequest(message="Explore our platform at https://example.com/demo.")
        assert req.get_cta_url() == "https://example.com/demo"


class TestPlatformIntegrations:
    """Verifies platform execution, response schema compliance, and resilience."""

    def test_simulation_mode_schema_compliance(self, client, enable_simulation):
        response = client.post(
            "/posting",
            json={"message": "Announcing our new developer toolkit! https://example.com/tools"}
        )
        assert response.status_code == 200
        data = response.json()

        assert "success" in data
        assert "results" in data
        assert len(data["results"]) == 5

        expected_platforms = {"Telegram", "Discord", "Slack", "Mastodon", "Dev.to"}
        received_platforms = set()

        for item in data["results"]:
            received_platforms.add(item["platform"])
            assert item["status"] in ("success", "failed")
            assert isinstance(item["public_access"], bool)
            if item["status"] == "success":
                assert item["posted_url"] is not None
                assert item["date"] is not None
                assert item["time"] is not None
                assert item["error"] is None

        assert received_platforms == expected_platforms

    def test_unconfigured_credentials_return_failure(self, client, disable_simulation):
        """When credentials are not set, each platform handles it gracefully without crashing."""
        response = client.post(
            "/posting",
            json={"message": "Test announcement without API credentials. https://example.com"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False

        for item in data["results"]:
            assert item["status"] == "failed"
            assert item["posted_url"] is None
            assert item["error"] is not None

    @pytest.mark.asyncio
    async def test_platform_isolation_resilience(self):
        """
        Verify that if one platform fails with an unhandled exception or network fault,
        the other platforms continue and complete successfully.
        """
        mock_telegram = TelegramPlatform()
        mock_discord = DiscordPlatform()
        mock_slack = SlackPlatform()
        mock_mastodon = MastodonPlatform()
        mock_devto = DevToPlatform()

        # Simulate Discord failing with a network timeout
        mock_discord.publish = AsyncMock(side_effect=httpx.ConnectTimeout("Connection timed out"))

        # The other 4 platforms succeed
        mock_telegram.publish = AsyncMock(return_value=PlatformResult(
            platform="Telegram", status="success", posted_url="https://t.me/channel/1",
            public_access=True, date="2026-11-21", time="12:00:00", error=None
        ))
        mock_slack.publish = AsyncMock(return_value=PlatformResult(
            platform="Slack", status="success", posted_url="https://app.slack.com/client",
            public_access=False, date="2026-11-21", time="12:00:00", error=None
        ))
        mock_mastodon.publish = AsyncMock(return_value=PlatformResult(
            platform="Mastodon", status="success", posted_url="https://mastodon.social/@user/123",
            public_access=True, date="2026-11-21", time="12:00:00", error=None
        ))
        mock_devto.publish = AsyncMock(return_value=PlatformResult(
            platform="Dev.to", status="success", posted_url="https://dev.to/user/post-1",
            public_access=True, date="2026-11-21", time="12:00:00", error=None
        ))

        service = PostingService(platforms=[
            mock_telegram, mock_discord, mock_slack, mock_mastodon, mock_devto
        ])

        response = await service.broadcast(
            message="Resilience test message. https://example.com",
            cta_url="https://example.com"
        )

        assert response.success is True
        results_by_name = {r.platform: r for r in response.results}

        assert results_by_name["Telegram"].status == "success"
        assert results_by_name["Discord"].status == "failed"
        assert "Connection timed out" in results_by_name["Discord"].error
        assert results_by_name["Slack"].status == "success"
        assert results_by_name["Mastodon"].status == "success"
        assert results_by_name["Dev.to"].status == "success"


class TestGeneralEndpoints:
    """Verifies general info and health endpoints."""

    def test_root_endpoint(self, client):
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["endpoint"] == "/posting"
        assert data["status"] == "operational"

    def test_health_endpoint(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["platforms_loaded"] == 5
