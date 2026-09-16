"""Scrapy settings for the acquisition layer (generic transport policy only).

Robots enforcement, throttling, retries and redirect handling are delegated to
Scrapy's own downloader middleware. There is no bespoke fetch engine in this
repo; the only hand-written acquisition code is domain glue (see spiders.py).
"""

from __future__ import annotations

from .settings import get_settings


def scrapy_settings(*, obey_robots: bool = True) -> dict:
    settings = get_settings()
    return {
        # robots: Scrapy's RobotsTxtMiddleware enforces per-URL rules, and it is
        # applied to redirect targets too (RedirectMiddleware re-enters the
        # downloader for every hop), so redirects cannot evade per-target policy.
        "ROBOTSTXT_OBEY": obey_robots,
        "ROBOTSTXT_USER_AGENT": settings.user_agent,
        # politeness: AutoThrottle + per-domain delay
        "AUTOTHROTTLE_ENABLED": True,
        "AUTOTHROTTLE_START_DELAY": settings.per_host_delay_seconds,
        "AUTOTHROTTLE_MAX_DELAY": 20.0,
        "AUTOTHROTTLE_TARGET_CONCURRENCY": 1.0,
        "DOWNLOAD_DELAY": settings.per_host_delay_seconds,
        "RANDOMIZE_DOWNLOAD_DELAY": True,
        "CONCURRENT_REQUESTS": settings.max_concurrency,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 1,
        # resilience: Scrapy retry + redirect middleware
        "RETRY_ENABLED": True,
        "RETRY_TIMES": 2,
        "RETRY_HTTP_CODES": [429, 500, 502, 503, 504, 522, 524, 408],
        "REDIRECT_ENABLED": True,
        "REDIRECT_MAX_TIMES": 5,
        "DOWNLOAD_TIMEOUT": settings.request_timeout_seconds,
        # classify HTTP failures ourselves so blocked/stale sources are surfaced
        "HTTPERROR_ALLOW_ALL": True,
        "USER_AGENT": settings.user_agent,
        "LOG_LEVEL": "ERROR",
        "TELNETCONSOLE_ENABLED": False,
        "COOKIES_ENABLED": False,
        "HTTPCACHE_ENABLED": False,
        "REQUEST_FINGERPRINTER_IMPLEMENTATION": "2.7",
    }
