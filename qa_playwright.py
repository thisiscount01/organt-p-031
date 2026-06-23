#!/usr/bin/env python3
"""QA playwright end-to-end verification"""
from playwright.sync_api import sync_playwright
import json, time

errors = []
results = {}

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(args=['--no-sandbox'])
        ctx = browser.new_context()
        page = ctx.new_page()
        page.on("pageerror", lambda e: errors.append(f"JS_ERR: {e}"))
        page.on("console", lambda m: errors.append(f"CON_{m.type.upper()}: {m.text}") if m.type in ("error","warning") else None)

        # 1) Home
        page.goto("http://localhost:3000/", wait_until="load", timeout=15000)
        time.sleep(2)
        page.screenshot(path="qa_pw_home.png")
        hero_visible = page.locator(".hero-title").first.is_visible()
        popular_cards = page.locator(".movie-card").count()
        print(f"[HOME] hero={hero_visible}, popular_cards={popular_cards}")
        results["home_hero"] = hero_visible
        results["home_cards"] = popular_cards

        # 2) Movies page
        page.goto("http://localhost:3000/#/movies", wait_until="load", timeout=10000)
        time.sleep(2)
        cards = page.locator(".movie-card").count()
        print(f"[MOVIES] cards={cards}")
        page.screenshot(path="qa_pw_movies.png")
        results["movies_cards"] = cards

        # 3) Movie detail (Inception id=27205)
        page.goto("http://localhost:3000/#/movie/27205", wait_until="load", timeout=10000)
        time.sleep(1.5)
        detail_title = page.locator(".detail-title").text_content() if page.locator(".detail-title").count() else "N/A"
        rec_section_exists = page.locator(".similar-section").count() > 0
        yt_iframe = page.locator("iframe[src*='youtube.com']").count()
        poster_img = page.locator(".detail-poster-wrap img").first
        poster_src = poster_img.get_attribute("src") if poster_img.count() else ""
        print(f"[DETAIL] title={detail_title}, AI_rec={rec_section_exists}, yt_iframe={yt_iframe}, poster_src={poster_src[:60]}")
        page.screenshot(path="qa_pw_detail.png")
        results["detail_title"] = detail_title
        results["detail_ai_rec"] = rec_section_exists
        results["detail_yt_iframe"] = yt_iframe

        # 4) Quiz select screen
        page.goto("http://localhost:3000/#/quiz", wait_until="load", timeout=10000)
        time.sleep(1)
        mode_cards = page.locator(".mode-card").count()
        print(f"[QUIZ-SELECT] mode_cards={mode_cards}")
        page.screenshot(path="qa_pw_quiz_select.png")
        results["quiz_modes"] = mode_cards

        # 5) Start quiz, play first question
        page.locator(".btn-start").click()
        time.sleep(2)
        hud_visible = page.locator(".quiz-hud").is_visible()
        timer_visible = page.locator(".quiz-timer-bar").is_visible()
        choice_count = page.locator(".quiz-choice").count()
        lives_shown = page.locator(".hud-value.red").text_content() if page.locator(".hud-value.red").count() else ""
        score_el = page.locator(".hud-value.gold").text_content() if page.locator(".hud-value.gold").count() else "0"
        print(f"[QUIZ-GAME] hud={hud_visible}, timer={timer_visible}, choices={choice_count}, lives={lives_shown}, score={score_el}")
        page.screenshot(path="qa_pw_quiz_game_before.png")

        # 첫 번째 보기 클릭
        page.locator(".quiz-choice").first.click()
        time.sleep(1)
        feedback_visible = page.locator(".quiz-feedback").count() > 0
        print(f"[QUIZ-GAME] feedback_after_click={feedback_visible}")
        page.screenshot(path="qa_pw_quiz_game_after.png")
        results["quiz_hud"] = hud_visible
        results["quiz_timer"] = timer_visible
        results["quiz_choices"] = choice_count
        results["quiz_feedback"] = feedback_visible

        # 6) Community
        page.goto("http://localhost:3000/#/community", wait_until="load", timeout=10000)
        time.sleep(1)
        post_items = page.locator(".review-card").count()
        write_btn = page.locator(".write-toggle").count()
        print(f"[COMMUNITY] posts={post_items}, write_btn={write_btn}")
        page.screenshot(path="qa_pw_community.png")
        results["community_posts"] = post_items

        # 7) Leaderboard
        page.goto("http://localhost:3000/#/leaderboard", wait_until="load", timeout=10000)
        time.sleep(1)
        lb_rows = page.locator(".lb-row").count()
        print(f"[LEADERBOARD] rows={lb_rows}")
        page.screenshot(path="qa_pw_leaderboard.png")
        results["leaderboard_rows"] = lb_rows

        # 8) Auth
        page.goto("http://localhost:3000/#/auth", wait_until="load", timeout=10000)
        time.sleep(0.5)
        form_visible = page.locator(".review-form-wrap").count() > 0
        print(f"[AUTH] form={form_visible}")
        page.screenshot(path="qa_pw_auth.png")
        results["auth_form"] = form_visible

        browser.close()

    print("\n=== SUMMARY ===")
    for k, v in results.items():
        status = "✅" if v else "❌"
        print(f"  {status} {k}: {v}")
    print(f"\nJS Errors ({len(errors)}):")
    for e in errors[:10]:
        print(f"  {e}")

run()
