#!/usr/bin/env python3
"""Vue SPA 렌더 후 포스터/YouTube/퀴즈 검증 (빠른 버전)"""
from playwright.sync_api import sync_playwright
import time, urllib.request, json

BASE = "http://localhost:3000"

# API로 trailer_yt 직접 확인 (브라우저 없이)
print("=== API 직접 확인 ===")
r = json.loads(urllib.request.urlopen(f"{BASE}/api/movies/27205").read())
print(f"  Inception trailer_yt={r.get('trailer_yt')}")
print(f"  embed URL: https://www.youtube.com/embed/{r.get('trailer_yt')}")
has_yt_data = bool(r.get("trailer_yt"))

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
    ctx = browser.new_context(viewport={"width":1280,"height":800})
    js_errors = []
    page = ctx.new_page()
    page.on("pageerror", lambda e: js_errors.append(str(e)))

    # 홈 로드
    print("\n=== 홈 페이지 ===")
    page.goto(BASE + "/", wait_until="domcontentloaded", timeout=12000)
    time.sleep(2)
    content = page.content()
    tmdb_count = content.count("image.tmdb.org")
    print(f"  tmdb CDN refs in HTML={tmdb_count}")
    page.screenshot(path="qa/final_home.png")

    # 영화 상세
    print("\n=== 영화 상세 (Inception) ===")
    page.goto(BASE + "/#/movie/27205", wait_until="domcontentloaded", timeout=12000)
    time.sleep(2)
    content = page.content()
    yt_in_html = content.count("youtube")
    tmdb_in_detail = content.count("image.tmdb.org")
    rec_in_detail = any(w in content for w in ["추천", "Similar", "연관", "비슷한"])
    print(f"  youtube refs={yt_in_html} tmdb refs={tmdb_in_detail} 추천섹션={rec_in_detail}")
    if yt_in_html > 0:
        idx = content.find("youtube")
        print(f"  youtube snippet: {content[max(0,idx-10):idx+80]}")
    page.screenshot(path="qa/final_detail.png")

    # 퀴즈 페이지
    print("\n=== 퀴즈 페이지 ===")
    page.goto(BASE + "/#/quiz", wait_until="domcontentloaded", timeout=12000)
    time.sleep(1.5)
    content = page.content()
    btns = page.locator("button").all_text_contents()
    print(f"  버튼: {[b.strip()[:15] for b in btns[:8]]}")
    has_quiz_kw = any(w in content for w in ["포스터","감독","배우","모드","퀴즈","Quiz"])
    print(f"  퀴즈 키워드={has_quiz_kw}")
    page.screenshot(path="qa/final_quiz.png")

    browser.close()

print(f"\nJS 오류: {len(js_errors)}건")
for e in js_errors[:3]: print(f"  {e[:100]}")
print(f"\n=== 결과 ===")
print(f"  G1 포스터 CDN 경로 데이터: {'PASS' if tmdb_count>=1 else 'FAIL'} (tmdb refs={tmdb_count})")
print(f"  G4 YouTube embed 데이터:   {'PASS' if has_yt_data else 'FAIL'} (template: refs={yt_in_html})")
print(f"  G3 AI추천 렌더:            {'PASS' if rec_in_detail else 'FAIL'}")
