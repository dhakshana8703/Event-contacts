"""In-memory Playwright retrieval client for discovery.

Fetches web pages entirely in memory without writing HTML snapshots to disk.
"""
from typing import Optional, Tuple
from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page, Playwright
import logging

logger = logging.getLogger(__name__)

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0"
)


class InMemoryBrowserClient:
    """Manages an in-memory browser session for live retrieval without saving files to disk."""

    def __init__(self, headless: bool = True, timeout_ms: int = 15000):
        self.headless = headless
        self.timeout_ms = timeout_ms
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None

    def start(self) -> None:
        """Initialize the browser context with anti-automation detection flags."""
        if self._browser is not None:
            return

        self._playwright = sync_playwright().start()
        
        # Use installed Edge or Chromium channel with automation flag disabled
        # This prevents Akamai WAF 403 Access Denied
        launch_args = [
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--disable-infobars",
        ]

        try:
            # Try msedge channel first on Windows
            self._browser = self._playwright.chromium.launch(
                channel="msedge",
                headless=self.headless,
                args=launch_args,
            )
        except Exception:
            # Fall back to standard chromium launch if msedge channel is unavailable
            self._browser = self._playwright.chromium.launch(
                headless=self.headless,
                args=launch_args,
            )

        self._context = self._browser.new_context(
            user_agent=DEFAULT_USER_AGENT,
            viewport={"width": 1280, "height": 800},
            locale="en-US",
        )

    def fetch_page_content(self, url: str) -> Tuple[Optional[str], int, Optional[str]]:
        """
        Fetch rendered page HTML directly into memory.

        Args:
            url: The URL to fetch.

        Returns:
            Tuple of (html_content, status_code, error_message)
        """
        if self._context is None:
            self.start()

        page: Optional[Page] = None
        try:
            page = self._context.new_page()
            response = page.goto(url, timeout=self.timeout_ms, wait_until="domcontentloaded")

            status = response.status if response else 0
            if status >= 400:
                return None, status, f"HTTP Error {status}"

            # Wait briefly for dynamic React/Next components to settle
            page.wait_for_timeout(1000)

            # Retrieve content into memory
            content = page.content()
            return content, status, None

        except Exception as exc:
            return None, 0, f"Retrieval failed: {str(exc)}"
        finally:
            if page:
                try:
                    page.close()
                except Exception:
                    pass

    def close(self) -> None:
        """Close browser context and stop Playwright cleanly."""
        if self._context:
            try:
                self._context.close()
            except Exception:
                pass
            self._context = None

        if self._browser:
            try:
                self._browser.close()
            except Exception:
                pass
            self._browser = None

        if self._playwright:
            try:
                self._playwright.stop()
            except Exception:
                pass
            self._playwright = None

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
