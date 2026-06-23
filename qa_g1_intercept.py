"""
G1 포스터 CDN 검증 — route 인터셉트 방식
image.tmdb.org 요청을 캡처 + stub 1x1 PNG으로 응답해 naturalWidth 확인
"""
from playwright.sync_api import sync_playwright
import base64, json

BASE = "http://localhost:3000"

# 1x1 투명 PNG (stub)
PNG_1x1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
)

tmdb_requests = []

def handle_tmdb(route):
    url = route.request.url
    tmdb_requests.append(url)
    route.fulfill(
        status=200,
        content_type="image/png",
        body=PNG_1x1,
    )

with sync_playwright() as p:
    browser = p.chromium.launch(args=["--no-sandbox","--disable-dev-shm-usage"])
    ctx = browser.new_context(viewport={"width":1280,"height":900})
    page = ctx.new_page()

    # image.tmdb.org 요청 인터셉트
    page.route("**/image.tmdb.org/**", handle_tmdb)

    page.goto(BASE + "/", wait_until="domcontentloaded")
    page.wait_for_selector(".init-loader", state="hidden", timeout=10000)

    page.evaluate("() => { location.hash = '#/movies'; }")
    page.wait_for_selector(".movie-card", timeout=8000)
    page.wait_for_timeout(2000)  # 이미지 로드 대기

    page.screenshot(path="qa_final_180515_g1_cdn.png")

    # 결과 수집
    card_count = page.locator(".movie-card").count()

    # naturalWidth 확인
    nw_results = page.evaluate("""
        () => Array.from(document.querySelectorAll('.movie-card img'))
              .slice(0, 10)
              .map(img => ({ src: img.src.slice(0,80), nw: img.naturalWidth }))
    """)

    tmdb_loaded = sum(1 for r in nw_results if r["nw"] > 0)
    tmdb_url_in_src = sum(1 for r in nw_results if "image.tmdb.org" in r["src"])

    print(f"=== G1 포스터 CDN 검증 결과 ===")
    print(f"movie-card 수: {card_count}")
    print(f"image.tmdb.org 요청 인터셉트 수: {len(tmdb_requests)}")
    print(f"인터셉트된 URL 샘플:")
    for u in tmdb_requests[:3]:
        print(f"  {u[:100]}")
    print(f"\n.movie-card img src/naturalWidth (10개 샘플):")
    for r in nw_results[:5]:
        print(f"  nw={r['nw']}  src={r['src']}")
    print(f"\ntmdb_url_in_src: {tmdb_url_in_src}/10")
    print(f"naturalWidth>0: {tmdb_loaded}/10")

    g1_intercept_pass = len(tmdb_requests) >= 10  # 최소 10개 tmdb 요청
    g1_nw_pass = tmdb_loaded >= 5                  # 5개 이상 실제 로드
    print(f"\nG1 CDN 요청 PASS (≥10 req): {g1_intercept_pass}")
    print(f"G1 naturalWidth PASS (≥5): {g1_nw_pass}")
    print(f"G1 최종: {'PASS' if g1_intercept_pass and g1_nw_pass else 'FAIL'}")

    browser.close()
