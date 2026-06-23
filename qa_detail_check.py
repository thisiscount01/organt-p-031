"""Deep check: movie detail iframe + quiz game"""
from playwright.sync_api import sync_playwright
import time, json

BASE = "https://organt-p-031.onrender.com"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=["--no-sandbox","--disable-dev-shm-usage"])
    ctx = browser.new_context(viewport={"width":1280,"height":900}, ignore_https_errors=True)
    page = ctx.new_page()

    # ── 2. 영화 상세 페이지 깊은 검사 ──────────────────────────
    print("=== [2] 영화 상세 상세 검사 ===")
    page.goto(f"{BASE}/#/movies/399566", timeout=30000, wait_until="domcontentloaded")
    time.sleep(6)

    iframes = page.locator("iframe").all()
    print(f"iframe count: {len(iframes)}")
    for i, ifr in enumerate(iframes):
        src = ifr.get_attribute("src") or ""
        print(f"  iframe[{i}] src={src[:120]}")

    body = page.inner_text("body")
    print(f"\nbody 길이: {len(body)}")
    lines = body.split('\n')
    rec_lines = [l.strip() for l in lines if any(kw in l for kw in ['추천','recommend','Recommend','Similar','similar','트레일러','Trailer','YouTube','유튜브'])]
    print(f"관련 라인({len(rec_lines)}):")
    for l in rec_lines[:15]:
        print(f"  {repr(l)}")

    movie_cards = page.locator(".movie-card").count()
    rec_sections = page.locator("[class*='recommend'], .recommendations, .similar-movies, [class*='similar']").count()
    print(f"\n.movie-card: {movie_cards}, recommend sections: {rec_sections}")

    # HTML에서 iframe 구조 확인
    html = page.content()
    iframe_pos = html.find("<iframe")
    if iframe_pos >= 0:
        print(f"\niframe HTML (300): {html[iframe_pos:iframe_pos+300]}")
    else:
        # youtube 관련 구조 탐색
        yt_pos = html.find("youtube")
        if yt_pos >= 0:
            print(f"\nyoutube in HTML (200): {html[max(0,yt_pos-50):yt_pos+200]}")
        else:
            print("\n[FAIL] iframe 및 youtube 키워드 없음")
            # trailer 관련
            trl_pos = html.find("trailer")
            if trl_pos < 0:
                trl_pos = html.find("Trailer")
            if trl_pos >= 0:
                print(f"trailer HTML ctx: {html[max(0,trl_pos-80):trl_pos+200]}")

    page.screenshot(path="qa_screenshots/02_detail_deep.png", full_page=True)

    # ── 4. 퀴즈 게임 플레이 상세 검사 ─────────────────────────
    print("\n=== [4] 퀴즈 게임 상세 검사 ===")
    page.goto(f"{BASE}/#/quiz", timeout=20000, wait_until="domcontentloaded")
    time.sleep(3)

    body_quiz = page.inner_text("body")
    print(f"퀴즈 선택 화면:\n{body_quiz[:400]}")

    # 버튼 목록
    btns = page.locator("button").all()
    print(f"\n버튼 수: {len(btns)}")
    for i, b in enumerate(btns[:10]):
        try:
            print(f"  btn[{i}]: '{b.inner_text().strip()}'")
        except:
            pass

    # 포스터 모드 클릭 (텍스트로)
    clicked = False
    for txt in ["포스터 → 제목", "포스터", "poster", "Poster", "시작", "게임 시작"]:
        try:
            btn = page.get_by_text(txt, exact=False).first
            if btn.is_visible(timeout=1000):
                print(f"\n'{txt}' 버튼 클릭")
                btn.click()
                time.sleep(4)
                clicked = True
                break
        except:
            pass

    if not clicked:
        # 첫 번째 버튼 클릭
        try:
            page.locator("button").first.click()
            time.sleep(4)
            clicked = True
            print("첫 번째 버튼 클릭")
        except:
            pass

    # 게임 화면 확인
    body_game = page.inner_text("body")
    print(f"\n게임 화면 (클릭 후):\n{body_game[:600]}")
    print(f"\nbody 길이: {len(body_game)}")

    btns_game = page.locator("button").all()
    print(f"\n게임 버튼 수: {len(btns_game)}")
    for i, b in enumerate(btns_game[:10]):
        try:
            print(f"  btn[{i}]: '{b.inner_text().strip()[:60]}'")
        except:
            pass

    # 선택지 관련 셀렉터
    for sel in [".option", ".choice", ".answer", "[class*='option']", "[class*='choice']", ".quiz-option", "li", ".list-group-item"]:
        cnt = page.locator(sel).count()
        if cnt > 0:
            print(f"  {sel}: {cnt}개")

    page.screenshot(path="qa_screenshots/04_quiz_deep.png", full_page=True)

    browser.close()
    print("\n완료")
