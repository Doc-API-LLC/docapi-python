"""DocAPI Python SDK — generate PDFs and screenshots from HTML."""

from __future__ import annotations

import urllib.request
import urllib.error
import json
from typing import Optional, Dict, Any


class DocAPIError(Exception):
    """Raised when the DocAPI server returns an error response."""

    def __init__(self, status: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message

    def __repr__(self) -> str:
        return f"DocAPIError(status={self.status}, code={self.code!r}, message={self.message!r})"


_BASE_URL = "https://api.docapi.co"
_WWW_URL = "https://www.docapi.co"


class DocAPI:
    """Client for the DocAPI REST API.

    Args:
        api_key: Your DocAPI API key (format: ``pk_...``).
                 Get one free at https://www.docapi.co/signup

    Example::

        from docapi import DocAPI

        client = DocAPI("pk_live_...")
        pdf = client.pdf("<h1>Hello World</h1>")
        with open("output.pdf", "wb") as f:
            f.write(pdf)
    """

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key
        self.credits_remaining: Optional[int] = None
        """Updated after every :meth:`pdf` or :meth:`screenshot` call from the
        ``X-Credits-Remaining`` response header. Use this to trigger proactive
        USDC top-ups before credits run out."""

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _request(
        self,
        method: str,
        url: str,
        body: Optional[Dict[str, Any]] = None,
        *,
        track_credits: bool = False,
    ) -> tuple[bytes, Any]:
        """Make an HTTP request and return (body_bytes, response_object)."""
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(
            url,
            data=data,
            method=method,
            headers={
                "x-api-key": self._api_key,
                "Content-Type": "application/json",
                "Accept": "*/*",
                "User-Agent": "docapi-python/0.1.0",
            },
        )
        try:
            with urllib.request.urlopen(req) as resp:
                raw = resp.read()
                if track_credits:
                    remaining = resp.headers.get("X-Credits-Remaining")
                    if remaining is not None:
                        try:
                            self.credits_remaining = int(remaining)
                        except ValueError:
                            pass
                return raw, resp
        except urllib.error.HTTPError as exc:
            raw = exc.read()
            try:
                err = json.loads(raw)
                code = err.get("error", "unknown_error")
                msg = err.get("message", str(exc))
            except Exception:
                code = "unknown_error"
                msg = str(exc)
            raise DocAPIError(exc.code, code, msg) from exc

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def pdf(
        self,
        html: str,
        *,
        format: str = "A4",
        landscape: bool = False,
        print_background: bool = True,
        margin: Optional[Dict[str, str]] = None,
        scale: Optional[float] = None,
        page_ranges: Optional[str] = None,
    ) -> bytes:
        """Convert HTML to a PDF.

        Args:
            html: HTML string to render.
            format: Paper format — ``"A4"`` (default), ``"Letter"``,
                ``"Legal"``, or ``"Tabloid"``.
            landscape: Landscape orientation. Default ``False``.
            print_background: Include background colours/images. Default ``True``.
            margin: Page margins as ``{"top": "0.5in", "bottom": "0.5in", ...}``.
            scale: Scale factor 0.1–2. Default ``1``.
            page_ranges: Pages to print, e.g. ``"1-5, 8"``.

        Returns:
            PDF file as :class:`bytes`.

        Raises:
            DocAPIError: On API errors (401, 402, 429, 500).

        Example::

            pdf = client.pdf(
                "<h1>Invoice #1</h1><p>Amount: $100</p>",
                format="A4",
                margin={"top": "1in", "bottom": "1in", "left": "1in", "right": "1in"},
            )
            with open("invoice.pdf", "wb") as f:
                f.write(pdf)
        """
        options: Dict[str, Any] = {
            "format": format,
            "landscape": landscape,
            "printBackground": print_background,
        }
        if margin is not None:
            options["margin"] = margin
        if scale is not None:
            options["scale"] = scale
        if page_ranges is not None:
            options["pageRanges"] = page_ranges

        raw, _ = self._request(
            "POST",
            f"{_BASE_URL}/v1/pdf",
            {"html": html, "options": options},
            track_credits=True,
        )
        return raw

    def screenshot(
        self,
        *,
        url: Optional[str] = None,
        html: Optional[str] = None,
        width: int = 1200,
        height: int = 630,
        format: str = "png",
    ) -> bytes:
        """Screenshot a URL or render HTML to an image.

        Provide either ``url`` or ``html``, not both.

        Args:
            url: URL to screenshot.
            html: HTML to render.
            width: Viewport width in pixels. Default ``1200``.
            height: Viewport height in pixels. Default ``630``.
            format: Image format — ``"png"`` (default) or ``"jpeg"``.

        Returns:
            Image file as :class:`bytes`.

        Raises:
            ValueError: If neither or both of ``url`` / ``html`` are given.
            DocAPIError: On API errors.

        Example::

            img = client.screenshot(url="https://example.com", width=1200, height=630)
            with open("og.png", "wb") as f:
                f.write(img)
        """
        if url is None and html is None:
            raise ValueError("Provide either 'url' or 'html'")
        if url is not None and html is not None:
            raise ValueError("Provide either 'url' or 'html', not both")

        body: Dict[str, Any] = {"width": width, "height": height, "format": format}
        if url is not None:
            body["url"] = url
        else:
            body["html"] = html

        raw, _ = self._request(
            "POST",
            f"{_BASE_URL}/v1/screenshot",
            body,
            track_credits=True,
        )
        return raw

    def invoice(
        self,
        from_: Dict[str, Any],
        to: Dict[str, Any],
        line_items: list,
        *,
        invoice_number: Optional[str] = None,
        date: Optional[str] = None,
        due_date: Optional[str] = None,
        currency_symbol: Optional[str] = None,
        tax_percent: Optional[float] = None,
        notes: Optional[str] = None,
        logo_url: Optional[str] = None,
    ) -> bytes:
        """Generate a PDF invoice.

        Args:
            from_: Sender details — ``{"name": str, "email": str (opt),
                "address": str (opt), "phone": str (opt)}``.
            to: Recipient details — ``{"name": str, "email": str (opt),
                "address": str (opt)}``.
            line_items: List of line items — each a dict with
                ``{"description": str, "quantity": float, "unit_price": float}``.
            invoice_number: Optional invoice number string.
            date: Optional invoice date string (e.g. ``"2026-03-12"``).
            due_date: Optional due date string.
            currency_symbol: Currency symbol. Default ``"$"``.
            tax_percent: Tax percentage 0–100.
            notes: Optional footer notes.
            logo_url: Optional URL to a logo image.

        Returns:
            PDF file as :class:`bytes`.

        Raises:
            DocAPIError: On API errors (401, 402, 429, 500).

        Example::

            pdf = client.invoice(
                from_={"name": "Acme Corp", "email": "billing@acme.com"},
                to={"name": "Jane Doe", "address": "123 Main St"},
                line_items=[{"description": "Consulting", "quantity": 2, "unit_price": 150.0}],
                invoice_number="INV-001",
                due_date="2026-04-12",
            )
            with open("invoice.pdf", "wb") as f:
                f.write(pdf)
        """
        body: Dict[str, Any] = {
            "from": from_,
            "to": to,
            "line_items": line_items,
        }
        if invoice_number is not None:
            body["invoice_number"] = invoice_number
        if date is not None:
            body["date"] = date
        if due_date is not None:
            body["due_date"] = due_date
        if currency_symbol is not None:
            body["currency_symbol"] = currency_symbol
        if tax_percent is not None:
            body["tax_percent"] = tax_percent
        if notes is not None:
            body["notes"] = notes
        if logo_url is not None:
            body["logo_url"] = logo_url

        raw, _ = self._request(
            "POST",
            f"{_BASE_URL}/v1/invoice",
            body,
            track_credits=True,
        )
        return raw

    def credits(self) -> Dict[str, Any]:
        """Check remaining credits and USDC top-up address.

        Agent accounts only. Returns a dict with ``credits`` and
        ``usdc_address`` keys.

        Example::

            info = client.credits()
            print(f"{info['credits']} credits remaining")
            print(f"Send USDC to {info['usdc_address']}")
        """
        raw, _ = self._request("GET", f"{_WWW_URL}/api/topup")
        return json.loads(raw)

    @staticmethod
    def register(
        notify_email: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Register a new agent account programmatically. No API key required.

        Args:
            notify_email: Optional email for low-balance alerts.

        Returns:
            Dict with ``api_key``, ``usdc_address``, ``free_calls``, and
            integration snippets.

        Example::

            account = DocAPI.register(notify_email="ops@mycompany.com")
            print(account["api_key"])       # "pk_..."
            print(account["usdc_address"])  # "0x..."
            print(account["free_calls"])    # 10
        """
        body: Dict[str, Any] = {}
        if notify_email is not None:
            body["notify_email"] = notify_email

        data = json.dumps(body).encode()
        req = urllib.request.Request(
            f"{_WWW_URL}/api/register",
            data=data,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "User-Agent": "docapi-python/0.1.0",
            },
        )
        try:
            with urllib.request.urlopen(req) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as exc:
            raw = exc.read()
            try:
                err = json.loads(raw)
                code = err.get("error", "unknown_error")
                msg = err.get("message", str(exc))
            except Exception:
                code = "unknown_error"
                msg = str(exc)
            raise DocAPIError(exc.code, code, msg) from exc
