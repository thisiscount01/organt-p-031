"""
세밀 검증:
 A) 영화 상세 라우트 실제 렌더 내용 + API 추천 5편 UI 연결
 B) 퀴즈 게임: 모드 선택 → 게임 시작! → 실제 플레이 화면
"""
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
import time, json, subprocess

BASE = "https://organt-p-031.onrender.com"

def curl_json(url):
    r = subprocess.run(["curl", "-s", "--max-time", "20", url],
                       capture_output=True, text=True, timeout=25)
    return r.stdout.strip()

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=["--no-sandbox","--disable-dev-shm-usage"])
    ctx = browser.new_context(viewport={"width":1280,"height":900}, ignore_https_errors=True)
    page = ctx.new_page()

    # ══════════════════════════════════════════════
    # A. 영화 상세 라우트 확인
    # ══════════════════════════════════════════════
    print("=== A. 영화 상세 라우트 ===")

    # 홈 → 영화 목록 → 첫 번째 영화 카드 클릭 방식
    page.goto(f"{BASE}/#/movies", timeout=30000, wait_until="domcontentloaded")
    time.sleep(4)

    body_movies = page.inner_text("body")
    print(f"영화 목록 body 길이: {len(body_movies)}, card count: {page.locator('.movie-card').count()}")

    # 영화 카드 클릭해서 상세로 이동
    card = page.locator(".movie-card").first
    if card.count() > 0:
        href = card.get_attribute("href") or ""
        print(f"첫 번째 card href: {href}")
        # 클릭
        card.click()
        time.sleep(4)
    else:
        # 링크 탐색
        links = page.locator("a[href*='movies/']").all()
        print(f"movies/ 링크 수: {len(links)}")
        if links:
            href = links[0].get_attribute("href")
            print(f"첫 링크: {href}")
            links[0].click()
            time.sleep(4)
        else:
            # 직접 URL
            page.goto(f"{BASE}/#/movies/399566", timeout=20000, wait_until="domcontentloaded")
            time.sleep(5)

    current_url = page.url
    print(f"현재 URL: {current_url}")

    body_detail = page.inner_text("body")
    print(f"상세 body 길이: {len(body_detail)}")
    print(f"상세 body 처음 600자:\n{body_detail[:600]}")

    # iframe 확인
    iframe_count = page.locator("iframe").count()
    print(f"\niframe count: {iframe_count}")

    # youtube embed 확인
    html = page.content()
    for kw in ["youtube", "YouTube", "iframe", "embed", "trailer", "Trailer", "odM92ap8"]:
        idx = html.find(kw)
        if idx >= 0:
            print(f"HTML '{kw}' at {idx}: ...{html[max(0,idx-30):idx+100]}...")

    # 추천 섹션 확인
    recs = page.locator(".movie-card").count()
    print(f"\n상세 페이지 .movie-card 수: {recs}")

    # API 추천 응답 확인 (상세 페이지의 영화 ID 파악)
    # URL에서 ID 추출
    import re
    m = re.search(r'movies/(\d+)', current_url)
    if m:
        movie_id = m.group(1)
        rec_raw = curl_json(f"{BASE}/api/movies/{movie_id}/recommend")
        try:
            rec_data = json.loads(rec_raw)
            recs_list = rec_data.get("recommendations", []) if isinstance(rec_data, dict) else rec_data
            print(f"\n추천 API (id={movie_id}): {len(recs_list)}편")
            if recs_list:
                print(f"첫 번째: {recs_list[0]}")
        except Exception as e:
            print(f"추천 API parse err: {e}, raw: {rec_raw[:100]}")

    page.screenshot(path="qa_screenshots/A_movie_detail_nav.png", full_page=True)

    # ══════════════════════════════════════════════
    # B. 퀴즈 게임 실제 플레이
    # ══════════════════════════════════════════════
    print("\n=== B. 퀴즈 게임 플레이 ===")
    page.goto(f"{BASE}/#/quiz", timeout=20000, wait_until="domcontentloaded")
    time.sleep(3)

    # 모드 카드들 (클릭 가능한 div/li 형태일 수 있음)
    # "포스터 → 제목" 텍스트가 있는 요소 클릭
    mode_elements = page.get_by_text("포스터 → 제목", exact=False)
    if mode_elements.count() > 0:
        mode_elements.first.click()
        time.sleep(1)
        print("포스터 → 제목 모드 선택")

    # 문제 수 선택 (5문제)
    try:
        q5 = page.get_by_text("5문제", exact=False)
        if q5.count() > 0:
            q5.first.click()
            time.sleep(0.5)
            print("5문제 선택")
    except:
        pass

    # 게임 시작! 버튼 클릭
    try:
        start_btn = page.get_by_text("게임 시작", exact=False)
        if start_btn.count() > 0:
            start_btn.first.click()
            print("게임 시작! 클릭")
            time.sleep(5)  # 게임 화면 로딩
    except:
        pass

    current_url_game = page.url
    print(f"게임 후 URL: {current_url_game}")

    body_game = page.inner_text("body")
    print(f"\n게임 화면 body 길이: {len(body_game)}")
    print(f"게임 화면 처음 800자:\n{body_game[:800]}")

    # 게임 UI 검사
    btn_count = page.locator("button").count()
    btns_text = []
    for b in page.locator("button").all()[:15]:
        try:
            t = b.inner_text().strip()
            if t:
                btns_text.append(t[:40])
        except:
            pass
    print(f"\n버튼 수: {btn_count}, texts: {btns_text}")

    # 선택지 요소 탐색
    for sel in [".option", ".choice", ".quiz-option", "[class*='option']",
                "[class*='choice']", ".list-group-item", "li.option", ".answer-option",
                ".btn-group button", "[class*='answer']"]:
        cnt = page.locator(sel).count()
        if cnt > 0:
            print(f"  {sel}: {cnt}개")

    # img (포스터)
    imgs = page.locator("img").count()
    print(f"img count: {imgs}")

    # 점수/타이머/생명 텍스트
    for kw in ["점수", "Score", "타이머", "Timer", "생명", "❤", "시간", "초", "남은"]:
        if kw in body_game:
            print(f"  '{kw}' 발견")

    page.screenshot(path="qa_screenshots/B_quiz_game_play.png", full_page=True)
    browser.close()
    print("\n완료")
