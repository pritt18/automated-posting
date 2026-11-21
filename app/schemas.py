import re
from typing import List, Optional
from urllib.parse import urlparse
from pydantic import BaseModel, Field, field_validator


class PostingRequest(BaseModel):
    message: str = Field(
        ...,
        description="Broadcast message containing text and exactly one valid CTA link",
        examples=["Check out our latest business platform and grow your online visibility. https://example.com"]
    )

    @field_validator("message")
    @classmethod
    def validate_message_rules(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("Message cannot be empty.")

        if len(trimmed) > 200:
            raise ValueError(
                f"Message must not exceed 200 characters. Provided message has {len(trimmed)} characters."
            )

        # Regex to detect any URL/URI scheme or www.
        url_regex = re.compile(
            r'([a-zA-Z][a-zA-Z0-9+.-]+://[^\s<>"]+|www\.[^\s<>"]+)',
            re.IGNORECASE
        )
        raw_matches = url_regex.findall(trimmed)

        # Clean trailing punctuation from URLs that border sentences
        detected_urls = []
        for match in raw_matches:
            cleaned = match.rstrip(".,;!?:)]}>\"'")
            if cleaned:
                detected_urls.append(cleaned)

        if len(detected_urls) == 0:
            raise ValueError(
                "Message must include exactly one CTA link, but none was found."
            )

        if len(detected_urls) > 1:
            raise ValueError(
                f"Message must include exactly one CTA link, but {len(detected_urls)} were found: {', '.join(detected_urls)}."
            )

        raw_url = detected_urls[0]
        if raw_url.startswith("www."):
            raw_url = "https://" + raw_url

        parsed = urlparse(raw_url)
        if parsed.scheme.lower() not in ("http", "https"):
            raise ValueError(
                f"Invalid URL scheme '{parsed.scheme}'. Only http and https protocols are supported."
            )

        if not parsed.netloc or "." not in parsed.netloc:
            raise ValueError(
                f"Invalid domain name in URL '{raw_url}'. A valid fully qualified domain is required."
            )

        return trimmed

    def get_cta_url(self) -> str:
        """Extracts the validated CTA URL from the message."""
        url_regex = re.compile(
            r'([a-zA-Z][a-zA-Z0-9+.-]+://[^\s<>"]+|www\.[^\s<>"]+)',
            re.IGNORECASE
        )
        matches = url_regex.findall(self.message)
        if matches:
            cleaned = matches[0].rstrip(".,;!?:)]}>\"'")
            if cleaned.startswith("www."):
                return "https://" + cleaned
            return cleaned
        return ""


class PlatformResult(BaseModel):
    platform: str
    status: str
    posted_url: Optional[str] = None
    public_access: bool = False
    date: Optional[str] = None
    time: Optional[str] = None
    error: Optional[str] = None


class PostingResponse(BaseModel):
    success: bool
    results: List[PlatformResult]


class HealthResponse(BaseModel):
    status: str
    version: str
    platforms_loaded: int
