"""
G4 심층 2: 영화 상세 라우트 + YouTube embed 탐색
"""
from playwright.sync_api import sync_playwright
import json

BASE = "https://organt-p-031.onrender.com"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
    ctx = browser.new_context(ignore_https_errors=True, viewport={"width":1280,"height":800})
    page = ctx.new_page()

    # movies 목록 페이지에서 상세 링크 탐색
    print("=== /movies 목록 → 상세 링크 ===")
    page.goto(f"{BASE}/#/movies", wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(4000)
    page.screenshot(path="qa_diag2_movies.png")

    # 모든 href 수집
    all_links = page.eval_on_selector_all(
        "a", "els => els.map(e=>({href:e.href,text:e.innerText.trim().slice(0,30)}))"
    )
    print(f"전체 링크: {len(all_links)}")
    for l in all_links[:20]:
        print(f"  {l}")

    # 클릭 가능한 movie 카드 탐색
    clickables = page.query_selector_all("[class*='card'], [class*='movie'], [class*='film'], [class*='poster'], li, article")
    print(f"\n클릭 가능 후보 수: {len(clickables)}")
    for el in clickables[:5]:
        cls = el.get_attribute("class") or ""
        tag = el.evaluate("e => e.tagName")
        print(f"  tag={tag}, class='{cls[:50]}'")

    # 카드 클릭 시도
    print("\n=== 카드 클릭 시도 ===")
    for el in clickables[:10]:
        try:
            el.click()
            page.wait_for_timeout(2000)
            new_url = page.url
            if "/movies/" in new_url or "/movie/" in new_url:
                print(f"상세 URL 도달: {new_url}")
                break
            else:
                # 뒤로가기
                page.go_back(wait_until="domcontentloaded", timeout=10000)
                page.wait_for_timeout(1000)
        except Exception as e:
            pass

    final_url = page.url
    print(f"최종 URL: {final_url}")

    # Vue router 내부 경로 확인 (hash)
    hash_url = page.evaluate("() => window.location.hash")
    print(f"hash: {hash_url}")

    # 직접 영화 ID 경로 시도
    print("\n=== 직접 영화 상세 라우트 시도 ===")
    for route in ["#/movies/1", "#/movie/1", "#/detail/1", "#/films/1"]:
        page.goto(f"{BASE}/{route}", wait_until="domcontentloaded", timeout=20000)
        page.wait_for_timeout(2000)
        content_len = len(page.content())
        hash_r = page.evaluate("() => window.location.hash")
        body_text = page.inner_text("body")[:100]
        iframes = page.query_selector_all("iframe")
        yt_iframes = [f for f in iframes if "youtube" in (f.get_attribute("src") or "")]
        print(f"  {route}: content={content_len}, hash={hash_r}, youtube_iframes={len(yt_iframes)}, text='{body_text}'")
        if yt_iframes:
            for fi in yt_iframes:
                print(f"    YT iframe src: {fi.get_attribute('src')}")

    # Vue App 라우터 목록 확인
    print("\n=== Vue 라우터 등록 경로 확인 ===")
    page.goto(f"{BASE}/#/", wait_until="domcontentloaded", timeout=30000)
    page.wait_for_timeout(3000)
    try:
        routes = page.evaluate("""
        () => {
            if (window.__vue_app__) {
                const router = window.__vue_app__.config.globalProperties.$router;
                if (router && router.getRoutes) {
                    return router.getRoutes().map(r => ({path: r.path, name: r.name}));
                }
            }
            return null;
        }
        """)
        print(f"Vue routes: {json.dumps(routes, ensure_ascii=False)}")
    except Exception as e:
        print(f"Vue router eval err: {e}")

    # /movies/:id 페이지에서 실제 영화 클릭
    print("\n=== /movies 목록 → 실제 클릭 탐색 ===")
    page.goto(f"{BASE}/#/movies", wait_until="domcontentloaded", timeout=30000)
    page.wait_for_timeout(4000)
    # 모든 클릭 가능 요소 중 navigate 유발 체크
    page.on("framenavigated", lambda f: print(f"  navigated: {f.url}"))
    cards = page.query_selector_all("[class*='card'], [class*='item'], [class*='movie-']")
    for card in cards[:5]:
        try:
            with page.expect_navigation(timeout=5000):
                card.click()
            new_url = page.url
            print(f"  navigate to: {new_url}")
            if "/movies/" in new_url or "/movie/" in new_url:
                break
        except:
            pass

    print(f"현재 URL: {page.url}")
    page.screenshot(path="qa_diag2_after_click.png")

    browser.close()
print("Done.")
