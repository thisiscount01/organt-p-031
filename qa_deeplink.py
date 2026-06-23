"""Direct URL deep-link test for /#/movies/:id"""
from playwright.sync_api import sync_playwright
import time

BASE = "https://organt-p-031.onrender.com"
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=["--no-sandbox","--disable-dev-shm-usage"])
    ctx = browser.new_context(viewport={"width":1280,"height":900}, ignore_https_errors=True)
    page = ctx.new_page()

    page.goto(f"{BASE}/#/movies/399566", timeout=30000, wait_until="domcontentloaded")
    time.sleep(10)
    body = page.inner_text("body")
    url = page.url
    iframe_cnt = page.locator("iframe").count()
    cards = page.locator(".movie-card").count()
    print(f"URL: {url}")
    print(f"body_len: {len(body)}, iframe: {iframe_cnt}, .movie-card: {cards}")
    print(f"body (400): {body[:400]}")
    page.screenshot(path="qa_screenshots/deeplink_test.png", full_page=True)
    browser.close()
