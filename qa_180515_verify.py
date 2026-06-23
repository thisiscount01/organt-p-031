"""
Task 180515-1 QA Verification Script v2 (SSL fix + splash timing)
Playwright evidence for live URL: https://organt-p-031.onrender.com
"""
from playwright.sync_api import sync_playwright
import time

BASE  = "https://organt-p-031.onrender.com"
SHOTS = "/home/user/organt_workspace/p-031-ai-기반-추천-웹게임"

with sync_playwright() as p:
    browser = p.chromium.launch(
        args=["--ignore-certificate-errors", "--disable-web-security",
              "--no-sandbox", "--disable-setuid-sandbox"]
    )
    ctx  = browser.new_context(viewport={"width": 1280, "height": 800}, ignore_https_errors=True)
    page = ctx.new_page()
    errs = []
    page.on("console", lambda m: errs.append(f"{m.type}:{m.text}") if m.type in ("error","warn") else None)

    # 1. cold-splash timing
    page.goto(BASE, wait_until="commit", timeout=20000)
    page.wait_for_timeout(400)
    early_html = page.content()
    early_splash = "cold-splash" in early_html
    page.screenshot(path=f"{SHOTS}/qa_180515_cold_early.png")

    page.wait_for_load_state("networkidle", timeout=25000)
    page.wait_for_timeout(800)
    final_el = page.query_selector("#cold-splash")
    final_visible = final_el.is_visible() if final_el else False
    page.screenshot(path=f"{SHOTS}/qa_180515_cold_final.png")
    print(f"[SPLASH] cold-splash in early DOM(400ms)={early_splash} | visible after networkidle={final_visible}")
    print(f"[ERRORS] {errs[:5]}")

    # 2. Home posters
    tmdb_home = page.query_selector_all("img[src*='tmdb.org']")
    page.screenshot(path=f"{SHOTS}/qa_180515_1_home.png")
    print(f"[HOME POSTERS] {len(tmdb_home)} tmdb img tags")

    # 3. Movies page
    page.goto(f"{BASE}/#/movies", wait_until="networkidle", timeout=20000)
    page.wait_for_timeout(2500)
    page.screenshot(path=f"{SHOTS}/qa_180515_2_movies.png")
    tmdb_mov = page.query_selector_all("img[src*='tmdb.org']")
    print(f"[MOVIES PAGE] {len(tmdb_mov)} tmdb posters")

    # 4. Quiz select
    page.goto(f"{BASE}/#/quiz", wait_until="networkidle", timeout=20000)
    page.wait_for_timeout(1500)
    page.screenshot(path=f"{SHOTS}/qa_180515_3_quiz_select.png")
    quiz_el = page.query_selector_all("button, .quiz-mode, [class*='mode']")
    print(f"[QUIZ SELECT] {len(quiz_el)} elements")

    # 5. Quiz game
    start_btns = page.query_selector_all("button")
    clicked = False
    for b in start_btns:
        txt = (b.inner_text() or "").strip()
        if txt and txt not in ("홈", "Home", "로그인", "Login", ""):
            b.click(); page.wait_for_timeout(2500); clicked = True; break
    page.screenshot(path=f"{SHOTS}/qa_180515_4_quiz_game.png")
    q_img  = page.query_selector("img[src*='tmdb.org']")
    q_opts = page.query_selector_all(".choice-btn, .option-btn, [class*='choice'], [class*='answer']")
    print(f"[QUIZ GAME] clicked={clicked} | img={q_img is not None} | option elements={len(q_opts)}")

    # 6. Movie detail (YouTube + AI rec)
    page.goto(f"{BASE}/#/movies/399566", wait_until="networkidle", timeout=20000)
    page.wait_for_timeout(3000)
    page.screenshot(path=f"{SHOTS}/qa_180515_5_detail.png")
    yt = page.query_selector("iframe[src*='youtube'], iframe[src*='youtu'], iframe[src*='ytb']")
    rec_wrap = page.query_selector_all("[class*='recommend'], .rec-card, .similar-card, [class*='related']")
    print(f"[DETAIL] yt iframe={yt is not None} | rec wrappers={len(rec_wrap)}")
    if yt:
        print(f"  yt src: {yt.get_attribute('src')[:80]}")

    # 7. Community
    page.goto(f"{BASE}/#/community", wait_until="networkidle", timeout=20000)
    page.wait_for_timeout(2000)
    page.screenshot(path=f"{SHOTS}/qa_180515_6_community.png")
    cards = page.query_selector_all(".card, .post-card, article, [class*='post-item']")
    print(f"[COMMUNITY] {len(cards)} post cards")

    # 8. Leaderboard
    page.goto(f"{BASE}/#/leaderboard", wait_until="networkidle", timeout=20000)
    page.wait_for_timeout(1500)
    page.screenshot(path=f"{SHOTS}/qa_180515_7_leaderboard.png")
    lb = page.query_selector_all("tbody tr, .rank-item, [class*='rank-row']")
    print(f"[LEADERBOARD] {len(lb)} rank rows")

    # 9. Auth
    page.goto(f"{BASE}/#/login", wait_until="networkidle", timeout=20000)
    page.wait_for_timeout(1000)
    page.screenshot(path=f"{SHOTS}/qa_180515_8_auth.png")
    inps = page.query_selector_all("input")
    print(f"[AUTH] {len(inps)} form inputs")

    ctx.close()
    browser.close()

print("[DONE] Screenshots saved.")
