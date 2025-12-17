import time
from urllib.parse import urlparse
from playwright.async_api import async_playwright

from src.logger import logger


class Browser:
    def __init__(self, throttle_helper, headless=True):
        self.headless = headless
        self.throttle_helper = throttle_helper
        self.playwright = None
        self.browser = None
        self.page = None

        self.viewport = {"width": 1920, "height": 1080}

        self.user_agent = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )

        # Anti-detection chromium flags
        self.chrome_args = [
            "--disable-blink-features=AutomationControlled",
            "--disable-dev-shm-usage",
            "--disable-features=IsolateOrigins,site-per-process",
            "--disable-web-security",
            "--disable-infobars",
            "--window-size=1920,1080",
            "--start-maximized",
        ]

    async def __aenter__(self):
        self.playwright = await async_playwright().__aenter__()

        self.browser = await self.playwright.chromium.launch(
            headless=self.headless, args=self.chrome_args
        )

        context = await self.browser.new_context(
            viewport=self.viewport,
            user_agent=self.user_agent,
            locale="pl-PL",
            timezone_id="Europe/Warsaw",
        )

        self.page = await context.new_page()

        # <<< Apply stealth manually for async API
        stealth_js = """
        Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        Object.defineProperty(navigator, 'plugins', { get: () => [1,2,3,4,5] });
        Object.defineProperty(navigator, 'languages', { get: () => ['pl-PL','pl'] });
        """
        await self.page.add_init_script(stealth_js)

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

    async def goto(self, url, domain, **kwargs):
        """Navigate to URL with automatic throttling and error handling.

        Args:
            url: URL to navigate to
            domain: Domain for throttle rate limiting
            **kwargs: Additional arguments to pass to page.goto()

        Returns:
            Response from page.goto()

        Raises:
            RuntimeError: If token acquisition fails after retries
        """
        # Acquire throttle token for the domain before making the request
        # The context manager ensures token is released even if page.goto fails
        async with self.throttle_helper.throttled_request(
            domain, max_retries=3
        ) as acquired:
            if not acquired:
                logger.error(
                    f"Failed to acquire throttle token for domain {domain} after retries. "
                    f"Aborting request to {url}"
                )
                raise RuntimeError(
                    f"Failed to acquire throttle token for domain {domain}"
                )

            try:
                logger.debug(f"Token acquired for {domain}, navigating to {url}")
                response = await self.page.goto(url, **kwargs)
                logger.debug(f"Navigation to {url} completed successfully")
                return response
            except Exception as e:
                logger.error(f"Error navigating to {url}: {e}", exc_info=True)
                raise

    async def query_selector(self, selector):
        return await self.page.query_selector(selector)

    async def query_selector_all(self, selector):
        return await self.page.query_selector_all(selector)

    async def inner_text(self, element):
        return await element.inner_text() if element else ""

    async def content(self):
        return await self.page.content()
