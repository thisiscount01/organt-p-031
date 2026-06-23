"""
G4: 영화 상세 페이지 YouTube trailer 렌더링 조건 확인
- trailer_yt API 데이터 있음 → 프론트엔드에서 iframe 미렌더 원인 파악
"""
from playwright.sync_api import sync_playwright
import json, re

BASE = "https://organt-p-031.onrender.com"
MOVIE_ID = 399566  # Godzilla vs. Kong

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
    ctx = browser.new_context(ignore_https_errors=True, viewport={"width":1280,"height":800})
    page = ctx.new_page()
    js_errors = []
    page.on("pageerror", lambda e: js_errors.append(str(e)))

    # 홈 → 상세 경로 (정상 탐색 흐름)
    print("=== 홈 → 상세 정상 탐색 ===")
    page.goto(f"{BASE}/#/", wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(3000)

    # 홈에서 '상세보기' 링크 찾기
    detail_links = page.eval_on_selector_all(
        "a", "els => els.map(e=>({href:e.href,text:e.innerText.trim().slice(0,40)}))"
                                              "   .filter(l=>l.href.includes('detail') || l.text.includes('상세') || l.text.includes('detail'))"
    )
    print(f"상세보기 링크: {detail_links[:5]}")

    # 직접 상세 URL 이동
    print(f"\n=== 직접 #/detail/{MOVIE_ID} 이동 ===")
    page.goto(f"{BASE}/#/detail/{MOVIE_ID}", wait_until="domcontentloaded", timeout=30000)
    page.wait_for_timeout(5000)

    print(f"콘솔 에러: {js_errors}")

    # 전체 HTML 일부 출력 (trailer 관련 부분)
    html = page.content()
    # trailer_yt 또는 youtube 포함 여부
    yt_idx = html.lower().find("youtube")
    trailer_idx = html.lower().find("trailer")
    print(f"HTML 길이: {len(html)}")
    print(f"'youtube' 위치: {yt_idx}")
    print(f"'trailer' 위치: {trailer_idx}")
    if yt_idx >= 0:
        print(f"  주변: ...{html[max(0,yt_idx-50):yt_idx+100]}...")
    if trailer_idx >= 0:
        print(f"  주변: ...{html[max(0,trailer_idx-50):trailer_idx+100]}...")

    # Vue 컴포넌트 데이터 확인
    print("\n=== Vue 컴포넌트 데이터 ===")
    try:
        movie_data = page.evaluate("""
        () => {
            // Vue3 __vue_app__
            if (window.__vue_app__) {
                const router = window.__vue_app__.config.globalProperties.$router;
                return { route: router ? router.currentRoute.value.fullPath : null };
            }
            return null;
        }
        """)
        print(f"Vue app data: {movie_data}")
    except Exception as e:
        print(f"Vue eval err: {e}")

    # 버튼 목록 (트레일러 재생 버튼이 있을 수 있음)
    buttons = page.query_selector_all("button")
    print(f"\n버튼 목록 ({len(buttons)}개):")
    for btn in buttons:
        try:
            txt = btn.inner_text().strip()
            cls = btn.get_attribute("class") or ""
            print(f"  '{txt}' class='{cls[:50]}'")
        except:
            pass

    # 트레일러 버튼 클릭 시도
    print("\n=== 트레일러 버튼 클릭 시도 ===")
    for btn in buttons:
        try:
            txt = btn.inner_text().strip().lower()
            if any(w in txt for w in ["trailer", "트레일러", "예고편", "watch", "play", "▶", "재생"]):
                print(f"  클릭: '{txt}'")
                btn.click()
                page.wait_for_timeout(2000)
                iframes_after = page.query_selector_all("iframe")
                print(f"  클릭 후 iframe 수: {len(iframes_after)}")
                for fi in iframes_after:
                    print(f"    src: {fi.get_attribute('src')}")
                break
        except:
            pass

    # 퀴즈 도전 버튼 vs 상세보기 버튼 확인
    print("\n=== 상세 페이지 body 텍스트 (전체) ===")
    body_text = page.inner_text("body")
    print(body_text[:1500])

    page.screenshot(path="qa_diag4_detail.png", full_page=True)
    browser.close()
print("Done.")
