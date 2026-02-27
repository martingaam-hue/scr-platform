"""Abstract base class for report generators."""

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from decimal import Decimal


class BaseReportGenerator(ABC):
    """Base class providing shared formatting and branding helpers."""

    def __init__(
        self,
        template_config: dict,
        org_settings: dict | None = None,
    ) -> None:
        self.template_config = template_config
        org = org_settings or {}
        self.org_name: str = org.get("org_name", "SCR Platform")
        self.logo_url: str | None = org.get("logo_url")
        self.brand_color: str = org.get("brand_color", "#1E3A5F")
        self.generated_at: str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    @abstractmethod
    def generate(self, data: dict, sections: list[dict]) -> tuple[bytes, str]:
        """Generate report bytes and content type.

        Returns:
            Tuple of (file_bytes, content_type).
        """

    def _format_currency(self, value, currency: str = "USD") -> str:
        try:
            num = Decimal(str(value))
            if currency == "USD":
                return f"${num:,.2f}"
            elif currency == "EUR":
                return f"\u20ac{num:,.2f}"
            elif currency == "GBP":
                return f"\u00a3{num:,.2f}"
            return f"{currency} {num:,.2f}"
        except (TypeError, ValueError):
            return str(value)

    def _format_percent(self, value) -> str:
        try:
            num = float(value)
            return f"{num:.1%}" if abs(num) < 1 else f"{num:.1f}%"
        except (TypeError, ValueError):
            return str(value)

    def _format_date(self, value) -> str:
        if isinstance(value, datetime):
            return value.strftime("%Y-%m-%d")
        if isinstance(value, str):
            return value[:10]
        return str(value)
