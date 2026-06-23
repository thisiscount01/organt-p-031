"""
G4: 영화 상세 #/detail/:id YouTube embed 정밀 검사
G3: AI 추천 5편 확인
"""
from playwright.sync_api import sync_playwright
import json, re

BASE = "https://organt-p-031.onrender.com"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
    ctx = browser.new_context(ignore_https_errors=True, viewport={"width":1280,"height":800})
    page = ctx.new_page()
    js_errors = []
    page.on("pageerror", lambda e: js_errors.append(str(e)))

    # 실제 영화 id 확인 (API에서 첫 번째 영화 id)
    print("=== 실제 영화 ID 확인 ===")
    r = page.request.get(f"{BASE}/api/movies?limit=5", timeout=30000)
    body = r.json()
    movies = body.get("results", [])
    if movies:
        m0 = movies[0]
        mid = m0.get("id") or m0.get("_id") or m0.get("tmdb_id") or "1"
        print(f"첫 영화: id={mid}, title={m0.get('title','?')}")
        print(f"  keys: {list(m0.keys())}")
    else:
        mid = 1
        print(f"영화 목록 비어있음, mid=1 사용")

    # 상세 페이지 이동
    print(f"\n=== #/detail/{mid} 상세 페이지 ===")
    page.goto(f"{BASE}/#/detail/{mid}", wait_until="domcontentloaded", timeout=30000)
    page.wait_for_timeout(5000)
    print(f"URL: {page.url}")
    print(f"콘솔 에러: {js_errors}")
    page.screenshot(path="qa_diag3_detail.png")

    # iframe 전체
    iframes = page.query_selector_all("iframe")
    print(f"iframe 수: {len(iframes)}")
    for i, f in enumerate(iframes):
        src = f.get_attribute("src") or ""
        allowfullscreen = f.get_attribute("allowfullscreen") or ""
        print(f"  iframe[{i}]: src='{src[:100]}', allowfullscreen={allowfullscreen}")

    # HTML에 youtube 포함 여부
    html = page.content()
    yt_in_html = "youtube" in html.lower()
    trailer_in_html = "trailer" in html.lower()
    print(f"HTML youtube 포함: {yt_in_html}")
    print(f"HTML trailer 포함: {trailer_in_html}")

    # video 엘리먼트
    videos = page.query_selector_all("video")
    print(f"video 엘리먼트: {len(videos)}")

    # 트레일러 관련 섹션
    trailer_els = page.query_selector_all("[class*='trailer'], [class*='video'], [class*='youtube'], [id*='trailer'], [id*='video']")
    print(f"trailer/video 엘리먼트: {len(trailer_els)}")
    for el in trailer_els:
        cls = el.get_attribute("class") or ""
        id_ = el.get_attribute("id") or ""
        tag = el.evaluate("e => e.tagName")
        print(f"  {tag} class='{cls[:60]}' id='{id_}'")

    # AI 추천 영화 확인
    print("\n=== AI 추천 영화 확인 ===")
    rec_text = page.inner_text("body")
    # "추천 영화" 섹션 이후 내용
    rec_idx = rec_text.find("추천 영화")
    if rec_idx >= 0:
        rec_section = rec_text[rec_idx:rec_idx+500]
        print(f"추천 섹션 텍스트:\n{rec_section}")
    else:
        print("'추천 영화' 텍스트 없음")

    # 추천 영화 엘리먼트들
    rec_els = page.query_selector_all("[class*='recommend'], [class*='similar'], [class*='related'], [class*='rec']")
    print(f"추천 엘리먼트 수: {len(rec_els)}")
    if rec_els:
        for el in rec_els[:3]:
            cls = el.get_attribute("class") or ""
            print(f"  class='{cls[:60]}': {el.inner_text()[:80]}")

    # 전체 구조 확인
    print("\n=== 페이지 body 구조 ===")
    sections = page.query_selector_all("section, main, article, div[class*='detail'], div[class*='movie-detail']")
    print(f"주요 섹션 수: {len(sections)}")
    for s in sections[:8]:
        cls = s.get_attribute("class") or ""
        id_ = s.get_attribute("id") or ""
        tag = s.evaluate("e => e.tagName")
        txt = s.inner_text()[:60]
        print(f"  {tag} class='{cls[:50]}' id='{id_}': {txt!r}")

    # API /api/movies/:id/recommend
    print(f"\n=== /api/movies/{mid}/recommend ===")
    r_rec = page.request.get(f"{BASE}/api/movies/{mid}/recommend", timeout=15000)
    print(f"status: {r_rec.status}")
    if r_rec.status == 200:
        rec_body = r_rec.json()
        print(f"body type: {type(rec_body).__name__}")
        if isinstance(rec_body, list):
            print(f"list len={len(rec_body)}")
            if rec_body:
                print(f"  first: {list(rec_body[0].keys()) if isinstance(rec_body[0],dict) else rec_body[0]}")
        elif isinstance(rec_body, dict):
            for k,v in rec_body.items():
                if isinstance(v, list):
                    print(f"  '{k}' list len={len(v)}")
                else:
                    print(f"  '{k}': {str(v)[:80]}")
    else:
        print(f"body: {r_rec.text()[:200]}")

    # 다른 recommend 경로 시도
    for ep in [f"/api/movies/{mid}/recommendations", f"/api/recommend/{mid}", f"/api/movies/{mid}/similar"]:
        try:
            rr = page.request.get(f"{BASE}{ep}", timeout=8000)
            print(f"GET {ep} → {rr.status}")
            if rr.status == 200:
                bb = rr.json()
                if isinstance(bb, list):
                    print(f"  list len={len(bb)}")
                elif isinstance(bb, dict):
                    print(f"  keys={list(bb.keys())[:6]}")
        except Exception as e:
            print(f"GET {ep} → ERR: {e}")

    # detail API
    print(f"\n=== /api/movies/{mid} (detail) ===")
    r_d = page.request.get(f"{BASE}/api/movies/{mid}", timeout=15000)
    print(f"status: {r_d.status}")
    if r_d.status == 200:
        dd = r_d.json()
        if isinstance(dd, dict):
            print(f"keys: {list(dd.keys())}")
            for k in dd:
                if "trailer" in k.lower() or "youtube" in k.lower() or "video" in k.lower() or "key" in k.lower():
                    print(f"  {k}={dd[k]}")

    browser.close()
print("Done.")
