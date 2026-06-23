"""
Task 180515-1 Final QA Verification
All screenshots + concrete evidence
"""
from playwright.sync_api import sync_playwright
import time

BASE  = "https://organt-p-031.onrender.com"
SHOTS = "/home/user/organt_workspace/p-031-ai-기반-추천-웹게임"

with sync_playwright() as p:
    browser = p.chromium.launch(args=["--ignore-certificate-errors","--no-sandbox"])
    ctx  = browser.new_context(viewport={"width":1280,"height":900}, ignore_https_errors=True)
    page = ctx.new_page()
    errs = []
    page.on("console", lambda m: errs.append(f"{m.type}:{m.text[:80]}") if m.type == "error" else None)

    print("=" * 60)
    print("Task 180515-1 Live QA Report")
    print("=" * 60)

    # ── SC1+SC4: health + warm load time ─────────────────────────────
    t0 = time.time()
    page.goto(BASE, wait_until="networkidle", timeout=20000)
    warm_ms = int((time.time() - t0) * 1000)
    print(f"\n[SC1] /api/health: tested via curl separately")
    print(f"[SC4] Warm load time: {warm_ms}ms (limit: 20000ms) → {'PASS' if warm_ms < 20000 else 'FAIL'}")

    # ── SC2: poster images on home ───────────────────────────────────
    tmdb = page.query_selector_all("img[src*='tmdb.org']")
    print(f"[SC2] TMDB poster img tags on home: {len(tmdb)} → {'PASS' if len(tmdb) > 0 else 'FAIL'}")
    page.screenshot(path=f"{SHOTS}/qa_final_180515_home.png")

    # ── SC2 cont: movies page ─────────────────────────────────────────
    page.goto(f"{BASE}/#/movies", wait_until="networkidle", timeout=20000)
    page.wait_for_timeout(2000)
    tmdb_m = page.query_selector_all("img[src*='tmdb.org']")
    print(f"[SC2b] TMDB posters on movies page: {len(tmdb_m)} → {'PASS' if len(tmdb_m) > 0 else 'FAIL'}")
    page.screenshot(path=f"{SHOTS}/qa_final_180515_movies.png")

    # ── SC3: quiz game ────────────────────────────────────────────────
    page.goto(f"{BASE}/#/quiz", wait_until="networkidle", timeout=20000)
    page.wait_for_timeout(1500)
    page.screenshot(path=f"{SHOTS}/qa_final_180515_quiz_select.png")
    # Start quiz by clicking first non-nav button
    btns = page.query_selector_all("button")
    for b in btns:
        txt = (b.inner_text() or "").strip()
        if txt and txt not in ("홈","Home","로그인","Login",""):
            b.click(); page.wait_for_timeout(2500); break
    q_img  = page.query_selector("img[src*='tmdb.org']")
    q_all  = page.query_selector_all("button")
    q_opts = [b for b in q_all if len((b.inner_text() or "").strip()) > 1]
    page.screenshot(path=f"{SHOTS}/qa_final_180515_quiz_play.png")
    print(f"[SC3] Quiz game: img={q_img is not None} | clickable buttons={len(q_opts)} → {'PASS' if q_img and len(q_opts) >= 4 else 'PARTIAL'}")

    # ── YouTube + AI Rec on detail ────────────────────────────────────
    page.goto(f"{BASE}/#/movie/399566", wait_until="networkidle", timeout=20000)
    page.wait_for_timeout(3000)
    page.screenshot(path=f"{SHOTS}/qa_final_180515_detail.png")
    yt = page.query_selector("iframe[src*='youtube']")
    sim_sec = page.query_selector(".similar-section")
    sim_cards = page.query_selector_all(".similar-section .movie-card, .similar-section .card, .similar-section a")
    yt_src = yt.get_attribute("src") if yt else "MISSING"
    print(f"[YT] YouTube embed: {yt is not None} | src={yt_src[:60] if yt else 'N/A'} → {'PASS' if yt else 'FAIL'}")
    print(f"[AI] Similar section: {sim_sec is not None} | cards={len(sim_cards)} → {'PASS' if sim_sec else 'FAIL'}")

    # ── SC5: cold-splash in served HTML ──────────────────────────────
    # Re-verify via new tab
    page2 = ctx.new_page()
    page2.goto(BASE, wait_until="commit", timeout=15000)
    page2.wait_for_timeout(300)
    early = "cold-splash" in page2.content()
    page2.wait_for_load_state("networkidle", timeout=20000)
    page2.wait_for_timeout(800)
    final_el = page2.query_selector("#cold-splash")
    final_vis = final_el.is_visible() if final_el else False
    page2.screenshot(path=f"{SHOTS}/qa_final_180515_splash.png")
    print(f"[SC5] cold-splash in early DOM: {early} | visible after mount: {final_vis} → {'PASS' if early and not final_vis else 'FAIL'}")
    page2.close()

    # ── Community page ────────────────────────────────────────────────
    page.goto(f"{BASE}/#/community", wait_until="networkidle", timeout=20000)
    page.wait_for_timeout(2500)
    page.screenshot(path=f"{SHOTS}/qa_final_180515_community.png")
    review_cards = page.query_selector_all(".review-card")
    print(f"[COMMUNITY] posts visible: {len(review_cards)} → {'PASS' if len(review_cards) > 0 else 'FAIL'}")

    # ── Leaderboard ───────────────────────────────────────────────────
    page.goto(f"{BASE}/#/leaderboard", wait_until="networkidle", timeout=20000)
    page.wait_for_timeout(2000)
    page.screenshot(path=f"{SHOTS}/qa_final_180515_leaderboard.png")
    rank_els = page.query_selector_all("[class*='rank']")
    print(f"[LEADERBOARD] rank elements: {len(rank_els)} → {'PASS' if len(rank_els) > 0 else 'FAIL'}")

    # ── Auth page ─────────────────────────────────────────────────────
    page.goto(f"{BASE}/#/auth", wait_until="networkidle", timeout=20000)
    page.wait_for_timeout(1500)
    page.screenshot(path=f"{SHOTS}/qa_final_180515_auth.png")
    inps = page.query_selector_all("input")
    print(f"[AUTH] form inputs: {len(inps)} → {'PASS' if len(inps) >= 2 else 'FAIL'}")

    # ── Console errors ────────────────────────────────────────────────
    print(f"\n[ERRORS] JS console errors: {errs[:5]}")

    ctx.close()
    browser.close()

print("\n[DONE] Screenshots saved.")
