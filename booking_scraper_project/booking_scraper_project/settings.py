# Scrapy settings for booking_scraper_project project
#
# For simplicity, this file contains only settings considered important or
# commonly used. You can find more settings consulting the documentation:
#
#     https://docs.scrapy.org/en/latest/topics/settings.html
#     https://docs.scrapy.org/en/latest/topics/downloader-middleware.html
#     https://docs.scrapy.org/en/latest/topics/spider-middleware.html

from datetime import datetime
from pathlib import Path

BOT_NAME = "booking_scraper_project"

SPIDER_MODULES = ["booking_scraper_project.spiders"]
NEWSPIDER_MODULE = "booking_scraper_project.spiders"

ADDONS = {}

# Logging to a file rather than to the console.
#
# The crawl of 2026-08-16 finished and wrote a valid hotels.json, but one city
# (Annecy) came back empty and the reason was unrecoverable: the whole Scrapy
# output had gone to a notebook cell, which was lost when the window closed.
# A log on disk is the only thing that survives the run.
#
# INFO, with the spider's own messages raised to INFO to match (Spider.log
# defaults to DEBUG, so LOG_LEVEL alone would have silenced the very lines that
# identify a failed city). Measured on the 2026-08-16 crawl: of 520,199 lines,
# 514,954 came from scrapy-playwright logging every image, XHR and tracking
# ping of every page -- 99% noise for a 123 MB file. The 943 spider lines that
# did the diagnostic work survive here, in well under 1 MB.
LOG_LEVEL = "INFO"

# settings.py -> booking_scraper_project/ -> booking_scraper_project/ -> repo root
# Anchored on __file__ like the spider's CITIES_CSV, so the log lands in the
# same place whether the crawl is launched from the repo root or from the
# scrapy project directory.
_LOG_DIR = Path(__file__).resolve().parents[2] / "logs"
_LOG_DIR.mkdir(parents=True, exist_ok=True)

# One file per run: overwriting would destroy the previous run's evidence at
# the very moment a comparison between two runs becomes useful.
LOG_FILE = str(_LOG_DIR / f"booking_spider_{datetime.now():%Y%m%d_%H%M%S}.log")

# Crawl responsibly by identifying yourself (and your website) on the user-agent
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'

# Obey robots.txt rules
ROBOTSTXT_OBEY = False

# Configure maximum concurrent requests performed by Scrapy (default: 16)
CONCURRENT_REQUESTS = 1

# Configure a delay for requests for the same website (default: 0)
# See https://docs.scrapy.org/en/latest/topics/settings.html#download-delay
# See also autothrottle settings and docs
DOWNLOAD_DELAY = 2
RANDOMIZE_DOWNLOAD_DELAY = True

# Disable cookies (enabled by default)
COOKIES_ENABLED = False

# Disable Telnet Console (enabled by default)
#TELNETCONSOLE_ENABLED = False

# Override the default request headers:
DEFAULT_REQUEST_HEADERS = {
   'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
   'Accept-Language': 'fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7',
   'Accept-Encoding': 'gzip, deflate, br',
   'Connection': 'keep-alive',
   'Upgrade-Insecure-Requests': '1',
   'Sec-Fetch-Dest': 'document',
   'Sec-Fetch-Mode': 'navigate',
   'Sec-Fetch-Site': 'none',
   'Sec-Fetch-User': '?1',
   'Cache-Control': 'max-age=0',
}

# Enable Scrapy User Agents Middleware
DOWNLOADER_MIDDLEWARES = {
    'scrapy.downloadermiddlewares.useragent.UserAgentMiddleware': None,
    'scrapy_user_agents.middlewares.RandomUserAgentMiddleware': 400,
}

# Enable and configure the AutoThrottle extension (disabled by default)
# See https://docs.scrapy.org/en/latest/topics/autothrottle.html
#AUTOTHROTTLE_ENABLED = True
# The initial download delay
#AUTOTHROTTLE_START_DELAY = 5
# The maximum download delay to be set in case of high latencies
#AUTOTHROTTLE_MAX_DELAY = 60
# The average number of requests Scrapy should be sending in parallel to
# each remote server
#AUTOTHROTTLE_TARGET_CONCURRENCY = 1.0
# Enable showing throttling stats for every response received:
#AUTOTHROTTLE_DEBUG = False

# Enable and configure HTTP caching (disabled by default)
# See https://docs.scrapy.org/en/latest/topics/downloader-middleware.html#httpcache-middleware-settings
#HTTPCACHE_ENABLED = True
#HTTPCACHE_EXPIRATION_SECS = 0
#HTTPCACHE_DIR = 'httpcache'
#HTTPCACHE_IGNORE_HTTP_CODES = []
#HTTPCACHE_STORAGE = 'scrapy.extensions.httpcache.FilesystemCacheStorage'
DOWNLOAD_HANDLERS = {
    "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
    "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
}
TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"