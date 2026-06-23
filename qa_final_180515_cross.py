"""
QA 교차검증 — Task 180515-1
Goal 1: TMDB 500편 fixture, 포스터 image.tmdb.org CDN 로드
Goal 2: 퀴즈 3종 API(choices:4) + UI 플레이 가능 확인
"""
from playwright.sync_api import sync_playwright
import json, sys

BASE = "http://localhost:3000"
RESULTS = {}

def run_checks():
    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--no-sandbox", "--disable-dev-shm-usage"])
        ctx = browser.new_context(viewport={"width": 1280, "height": 900})
        page = ctx.new_page()
        console_errors = []
        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)

        # ── G1: 영화 목록 페이지 포스터 CDN ──
        print("[G1] 홈 먼저 로드해 init 완료 대기...")
        page.goto(BASE + "/", wait_until="domcontentloaded")
        # init-loader 사라질 때까지 대기 (최대 10초)
        try:
            page.wait_for_selector(".init-loader", state="hidden", timeout=10000)
            print("[G1] init-loader 사라짐 — Vue 앱 로드 완료")
        except Exception:
            print("[G1] WARNING: init-loader 타임아웃 — 계속 진행")

        # 영화 목록 페이지로 이동
        page.evaluate("() => { location.hash = '#/movies'; }")
        # movie-card 등장 대기 (최대 8초)
        try:
            page.wait_for_selector(".movie-card", timeout=8000)
            print("[G1] .movie-card 렌더링 확인")
        except Exception:
            print("[G1] WARNING: .movie-card 타임아웃")

        page.wait_for_timeout(1000)
        page.screenshot(path="qa_final_180515_g1_movies.png", full_page=False)

        # image.tmdb.org src를 가진 img 수집
        imgs_tmdb = page.locator("img[src*='image.tmdb.org']").all()
        tmdb_count = len(imgs_tmdb)
        RESULTS["G1_tmdb_img_on_page"] = tmdb_count

        # naturalWidth 체크 (최대 5개 샘플)
        loaded_ok = 0
        for img in imgs_tmdb[:5]:
            try:
                nw = img.evaluate("el => el.naturalWidth")
                if nw and int(nw) > 0:
                    loaded_ok += 1
            except Exception:
                pass
        RESULTS["G1_naturalWidth_sample"] = f"{loaded_ok}/{min(5, tmdb_count)}"

        # 첫 번째 이미지 src 기록
        if imgs_tmdb:
            try:
                first_src = imgs_tmdb[0].get_attribute("src")
                RESULTS["G1_first_img_src"] = first_src[:80] if first_src else "N/A"
            except Exception:
                RESULTS["G1_first_img_src"] = "ERR"

        RESULTS["G1_pass"] = tmdb_count >= 1 and loaded_ok >= 1

        # ── G2: 퀴즈 선택 화면 ──
        print("[G2] 퀴즈 화면 이동...")
        page.evaluate("() => { location.hash = '#/quiz'; }")
        try:
            page.wait_for_selector(".quiz-select-screen", timeout=6000)
            print("[G2] .quiz-select-screen 확인")
        except Exception:
            print("[G2] WARNING: quiz-select-screen 타임아웃")

        page.wait_for_timeout(500)
        page.screenshot(path="qa_final_180515_g2_select.png", full_page=False)

        # 모드 카드 확인 (poster/director/cast 포함)
        mode_cards = page.locator(".mode-card").all()
        mode_titles = []
        for card in mode_cards:
            try:
                t = card.locator(".mode-title").inner_text().strip()
                mode_titles.append(t)
            except Exception:
                pass
        RESULTS["G2_mode_cards"] = mode_titles
        RESULTS["G2_mode_count"] = len(mode_titles)

        # poster 모드 카드 클릭 (포스터 → 제목 맞추기)
        poster_card = page.locator(".mode-card").first
        try:
            poster_card.click()
            page.wait_for_timeout(300)
            print(f"[G2] 첫 번째 모드 카드 클릭: {mode_titles[0] if mode_titles else '?'}")
        except Exception as e:
            print(f"[G2] 모드 카드 클릭 실패: {e}")

        # 게임 시작! 버튼 클릭
        start_btn = page.locator(".btn-start")
        try:
            start_btn.click()
            print("[G2] 게임 시작! 클릭")
        except Exception as e:
            print(f"[G2] 시작 버튼 클릭 실패: {e}")

        # game screen 등장 대기
        try:
            page.wait_for_selector(".quiz-game-screen", timeout=8000)
            print("[G2] .quiz-game-screen 확인")
        except Exception:
            print("[G2] WARNING: quiz-game-screen 타임아웃")
            # 재시도: wait a bit more
            page.wait_for_timeout(3000)

        page.screenshot(path="qa_final_180515_g2_play.png", full_page=False)

        # 선택지 4개 확인
        choices = page.locator(".quiz-choice").all()
        RESULTS["G2_choices_visible"] = len(choices)

        # 문제 텍스트 확인
        try:
            prompt_text = page.locator(".quiz-q-prompt").inner_text().strip()
            RESULTS["G2_question_text"] = prompt_text[:80]
        except Exception:
            RESULTS["G2_question_text"] = "N/A"

        RESULTS["G2_pass"] = len(choices) >= 4

        browser.close()

    # 최종 출력
    print("\n===== QA 교차검증 결과 =====")
    for k, v in RESULTS.items():
        print(f"  {k}: {v}")

    g1 = RESULTS.get("G1_pass", False)
    g2 = RESULTS.get("G2_pass", False)
    print(f"\nGoal1 Playwright POSTER CDN: {'PASS' if g1 else 'FAIL'}")
    print(f"Goal2 Playwright QUIZ UI:    {'PASS' if g2 else 'FAIL'}")

    if not g1 or not g2:
        sys.exit(1)

if __name__ == "__main__":
    run_checks()
