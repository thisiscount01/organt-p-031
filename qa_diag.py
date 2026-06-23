"""
FAIL 항목 심층 진단:
  G1c: 영화 300편+ (API /api/movies 실제 반환 수)
  G4:  YouTube embed (영화 상세 페이지 구조)
"""
from playwright.sync_api import sync_playwright
import json

BASE = "https://organt-p-031.onrender.com"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
    ctx = browser.new_context(ignore_https_errors=True, viewport={"width":1280,"height":800})
    page = ctx.new_page()

    # ── G1c 심층: API 응답 구조 확인 ────────────────────────────
    print("=== G1c: /api/movies 응답 구조 ===")
    r = page.request.get(f"{BASE}/api/movies?limit=600", timeout=30000)
    print(f"status: {r.status}")
    body = r.json()
    if isinstance(body, dict):
        top_keys = list(body.keys())
        print(f"top-level keys: {top_keys}")
        for k, v in body.items():
            if isinstance(v, list):
                print(f"  body['{k}'] → list len={len(v)}")
            elif isinstance(v, int):
                print(f"  body['{k}'] → int={v}")
            else:
                print(f"  body['{k}'] → {type(v).__name__}={str(v)[:80]}")
    elif isinstance(body, list):
        print(f"body is list len={len(body)}")
        if body:
            print(f"  first item keys: {list(body[0].keys()) if isinstance(body[0], dict) else body[0]}")

    # total 필드 등 페이지네이션 메타 확인
    print("\n=== /api/movies (no limit) ===")
    r2 = page.request.get(f"{BASE}/api/movies", timeout=30000)
    b2 = r2.json()
    if isinstance(b2, dict):
        for k, v in b2.items():
            if isinstance(v, list):
                print(f"  '{k}' list len={len(v)}")
            elif isinstance(v, (int, float, str, bool)):
                print(f"  '{k}': {v}")

    print("\n=== /api/movies?page=1&limit=10 ===")
    r3 = page.request.get(f"{BASE}/api/movies?page=1&limit=10", timeout=30000)
    b3 = r3.json()
    if isinstance(b3, dict):
        for k, v in b3.items():
            if isinstance(v, list):
                print(f"  '{k}' list len={len(v)}")
            elif isinstance(v, (int, float, str, bool)):
                print(f"  '{k}': {v}")

    print("\n=== /api/movies?page=2&limit=100 (pagination test) ===")
    r4 = page.request.get(f"{BASE}/api/movies?page=2&limit=100", timeout=30000)
    b4 = r4.json()
    if isinstance(b4, dict):
        for k, v in b4.items():
            if isinstance(v, list):
                print(f"  '{k}' list len={len(v)}")
            elif isinstance(v, (int, float, str, bool)):
                print(f"  '{k}': {v}")

    # ── G4 심층: 영화 상세 페이지 YouTube embed 구조 ────────────
    print("\n=== G4: 영화 상세 페이지 YouTube embed 확인 ===")
    # 홈에서 영화 카드 직접 href 수집
    page.goto(f"{BASE}/#/", wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(4000)

    links = page.eval_on_selector_all(
        "a", "els => els.map(e=>({href:e.href, text:e.innerText.trim().slice(0,40)}))"
    )
    movie_links = [l for l in links if "movie" in l["href"] and "#" in l["href"]]
    print(f"영화 링크 수: {len(movie_links)}")
    if movie_links:
        print(f"샘플: {movie_links[:5]}")

    # href로 직접 이동
    if movie_links:
        detail_href = movie_links[0]["href"]
        print(f"\n이동: {detail_href}")
        page.goto(detail_href, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(4000)
        print(f"최종 URL: {page.url}")
        detail_html = page.content()
        print(f"HTML 크기: {len(detail_html)}")

        # iframe 검색
        iframes = page.query_selector_all("iframe")
        print(f"iframe 수: {len(iframes)}")
        for i, f in enumerate(iframes):
            src = f.get_attribute("src") or ""
            print(f"  iframe[{i}] src={src[:100]}")

        # youtube 텍스트
        has_yt_text = "youtube" in detail_html.lower() or "trailer" in detail_html.lower()
        print(f"HTML에 'youtube'/'trailer' 포함: {has_yt_text}")

        # 페이지 주요 구조
        sections = page.query_selector_all("section, [class*='section'], [class*='trailer'], [class*='video']")
        print(f"section/trailer/video 엘리먼트 수: {len(sections)}")
        for s in sections[:5]:
            cls = s.get_attribute("class") or ""
            print(f"  class='{cls[:60]}'")

        # 스크린샷
        page.screenshot(path="qa_diag_detail.png")

        # 해당 영화의 API 라우트 탐색
        url_hash = page.url.split("#")[-1] if "#" in page.url else ""
        print(f"\nhash route: {url_hash}")
        # movie id 추출
        parts = url_hash.strip("/").split("/")
        print(f"parts: {parts}")
        if len(parts) >= 2:
            mid = parts[-1]
            api_movie = page.request.get(f"{BASE}/api/movies/{mid}", timeout=15000)
            print(f"GET /api/movies/{mid} → {api_movie.status}")
            if api_movie.status == 200:
                md = api_movie.json()
                if isinstance(md, dict):
                    print(f"  movie keys: {list(md.keys())}")
                    yt_key = [k for k in md if "trailer" in k.lower() or "youtube" in k.lower() or "video" in k.lower()]
                    print(f"  video/trailer keys: {yt_key}")
                    for k in yt_key:
                        print(f"  {k}={md[k]}")

    browser.close()
print("\nDone.")
