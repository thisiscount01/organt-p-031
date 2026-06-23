"""
Task 180515-1 QA — Corrected URL Verification
Routes: #/movie/:id  #/auth  #/community  #/leaderboard
"""
from playwright.sync_api import sync_playwright
import time

BASE  = "https://organt-p-031.onrender.com"
SHOTS = "/home/user/organt_workspace/p-031-ai-기반-추천-웹게임"
MOVIE_ID = 399566  # Godzilla vs. Kong, has trailer_yt=odM92ap8_c0

with sync_playwright() as p:
    browser = p.chromium.launch(args=["--ignore-certificate-errors","--no-sandbox"])
    ctx  = browser.new_context(viewport={"width":1280,"height":900}, ignore_https_errors=True)
    page = ctx.new_page()
    errs = []
    page.on("console", lambda m: errs.append(f"{m.type}:{m.text[:80]}") if m.type in ("error","warn") else None)

    # Movie detail: correct URL is #/movie/:id
    page.goto(f"{BASE}/#/movie/{MOVIE_ID}", wait_until="networkidle", timeout=20000)
    page.wait_for_timeout(3000)
    page.screenshot(path=f"{SHOTS}/qa_180515_detail_correct.png")

    # YouTube embed
    yt = page.query_selector("iframe[src*='youtube']")
    yt_src = yt.get_attribute("src") if yt else None
    # AI recommendations
    rec_section = page.query_selector_all("[class*='recommend'], [class*='similar'], .rec-card, .similar-movie")
    rec_imgs = page.query_selector_all("[class*='recommend'] img, .rec-card img")
    print(f"[DETAIL yt] iframe={yt is not None} | src={yt_src}")
    print(f"[DETAIL AI] rec sections={len(rec_section)} | rec imgs={len(rec_imgs)}")
    # Check if movie title rendered
    h1 = page.query_selector("h1, .movie-title, [class*='title']")
    print(f"[DETAIL TITLE] {h1.inner_text()[:60] if h1 else 'NOT FOUND'}")
    print(f"[DETAIL ERRORS] {errs[:3]}")

    # Auth page: correct URL is #/auth
    errs.clear()
    page.goto(f"{BASE}/#/auth", wait_until="networkidle", timeout=20000)
    page.wait_for_timeout(1500)
    page.screenshot(path=f"{SHOTS}/qa_180515_auth_correct.png")
    inputs = page.query_selector_all("input")
    btns = page.query_selector_all("button")
    print(f"[AUTH] inputs={len(inputs)} | buttons={len(btns)}")
    for inp in inputs:
        print(f"  input type={inp.get_attribute('type')} placeholder={inp.get_attribute('placeholder')}")

    # Community page
    errs.clear()
    page.goto(f"{BASE}/#/community", wait_until="networkidle", timeout=20000)
    page.wait_for_timeout(2500)
    page.screenshot(path=f"{SHOTS}/qa_180515_community_correct.png")
    review_cards = page.query_selector_all(".review-card")
    post_items = page.query_selector_all("[class*='post'], [class*='community']")
    print(f"[COMMUNITY] review-cards={len(review_cards)} | community elements={len(post_items)}")
    body = page.inner_text("body")
    print(f"  body[:150]: {body[:150]}")

    # Leaderboard
    errs.clear()
    page.goto(f"{BASE}/#/leaderboard", wait_until="networkidle", timeout=20000)
    page.wait_for_timeout(2000)
    page.screenshot(path=f"{SHOTS}/qa_180515_leaderboard_correct.png")
    rows = page.query_selector_all("tr, .rank-item, [class*='rank-row'], [class*='leader-row']")
    any_rank = page.query_selector_all("[class*='rank']")
    print(f"[LEADERBOARD] tr/rank-rows={len(rows)} | all rank-class={len(any_rank)}")

    # Warm load time (already loaded server, measure a fresh goto)
    t0 = time.time()
    page.goto(BASE, wait_until="networkidle", timeout=20000)
    warm_ms = int((time.time() - t0) * 1000)
    print(f"[WARM LOAD] {warm_ms}ms (threshold 20000ms)")

    ctx.close()
    browser.close()

print("[DONE]")
