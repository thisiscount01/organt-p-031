"""G1 포스터 img src 진단 - 실제 렌더된 src 값 확인"""
from playwright.sync_api import sync_playwright

BASE = "http://localhost:3000"

with sync_playwright() as p:
    browser = p.chromium.launch(args=["--no-sandbox","--disable-dev-shm-usage"])
    ctx = browser.new_context(viewport={"width":1280,"height":900})
    page = ctx.new_page()

    # 홈 로드 후 init 완료 대기
    page.goto(BASE + "/", wait_until="domcontentloaded")
    page.wait_for_selector(".init-loader", state="hidden", timeout=10000)

    # 영화 목록으로 이동
    page.evaluate("() => { location.hash = '#/movies'; }")
    page.wait_for_selector(".movie-card", timeout=8000)
    page.wait_for_timeout(1500)

    # 모든 img의 src 수집
    all_img_srcs = page.evaluate("""
        () => Array.from(document.querySelectorAll('img')).map(img => img.src || img.getAttribute('src') || '(empty)').slice(0, 20)
    """)
    print("== 페이지 내 img src (최대 20개) ==")
    for s in all_img_srcs:
        print(" ", s[:100])

    # movie-card 내 img
    card_imgs = page.evaluate("""
        () => Array.from(document.querySelectorAll('.movie-card img')).map(img => img.src).slice(0,5)
    """)
    print("\n== .movie-card img src (최대 5개) ==")
    for s in card_imgs:
        print(" ", s[:100])

    # movie-card 개수
    card_count = page.locator(".movie-card").count()
    print(f"\n.movie-card 개수: {card_count}")

    # 페이지 내 tmdb 관련 텍스트 확인
    has_tmdb = page.evaluate("() => document.documentElement.innerHTML.includes('image.tmdb.org')")
    print(f"HTML에 image.tmdb.org 존재: {has_tmdb}")

    page.screenshot(path="qa_final_180515_g1_diag.png")
    browser.close()
