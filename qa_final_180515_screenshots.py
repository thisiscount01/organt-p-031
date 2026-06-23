"""최종 스크린샷 세트 생성 — qa_final_180515_*.png"""
from playwright.sync_api import sync_playwright
import base64

BASE = "http://localhost:3000"
PNG_1x1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
)

with sync_playwright() as p:
    browser = p.chromium.launch(args=["--no-sandbox","--disable-dev-shm-usage"])
    ctx = browser.new_context(viewport={"width":1280,"height":900})
    page = ctx.new_page()

    # CDN 인터셉트 (stub으로 빠른 로드)
    page.route("**/image.tmdb.org/**", lambda route: route.fulfill(
        status=200, content_type="image/png", body=PNG_1x1))

    # 1. 홈 init 완료
    page.goto(BASE + "/", wait_until="domcontentloaded")
    page.wait_for_selector(".init-loader", state="hidden", timeout=10000)
    page.screenshot(path="qa_final_180515_home.png")
    print("[OK] qa_final_180515_home.png")

    # 2. G1: 영화 목록 + 포스터
    page.evaluate("() => { location.hash = '#/movies'; }")
    page.wait_for_selector(".movie-card", timeout=8000)
    page.wait_for_timeout(1500)
    page.screenshot(path="qa_final_180515_g1_movies_cdn.png")
    card_count = page.locator(".movie-card").count()
    tmdb_imgs = page.locator("img[src*='image.tmdb.org']").count()
    print(f"[OK] qa_final_180515_g1_movies_cdn.png  cards={card_count}  tmdb_imgs={tmdb_imgs}")

    # 3. G2: 퀴즈 선택 화면
    page.evaluate("() => { location.hash = '#/quiz'; }")
    page.wait_for_selector(".quiz-select-screen", timeout=6000)
    page.wait_for_timeout(500)
    page.screenshot(path="qa_final_180515_g2_quiz_select.png")
    mode_count = page.locator(".mode-card").count()
    print(f"[OK] qa_final_180515_g2_quiz_select.png  mode_cards={mode_count}")

    # 4. G2: 게임 화면 (poster 모드)
    page.locator(".mode-card").first.click()
    page.wait_for_timeout(300)
    page.locator(".btn-start").click()
    page.wait_for_selector(".quiz-game-screen", timeout=8000)
    page.wait_for_timeout(1000)
    page.screenshot(path="qa_final_180515_g2_quiz_play.png")
    choices = page.locator(".quiz-choice").count()
    question = page.locator(".quiz-q-prompt").inner_text().strip() if page.locator(".quiz-q-prompt").count() else "N/A"
    print(f"[OK] qa_final_180515_g2_quiz_play.png  choices={choices}  q={question[:50]}")

    browser.close()
    print("\n스크린샷 저장 완료")
