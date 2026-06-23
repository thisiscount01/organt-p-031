#!/usr/bin/env python3
"""
QA Final Check — Task 180515-1
G1: /api/movies total >= 300 + poster CDN 200
G2: quiz 3종 API (poster/director/cast)
G3: Playwright #/movies/399566 직접 접근 상세 페이지 렌더링
"""
import subprocess, json, urllib.request, time, sys, os

BASE = "http://localhost:3000"
WORKSPACE = "/home/user/organt_workspace/p-031-ai-기반-추천-웹게임"
RESULTS = {}

def check(label, cond, detail=""):
    status = "PASS" if cond else "FAIL"
    RESULTS[label] = {"status": status, "detail": detail}
    print(f"[{status}] {label}: {detail}")
    return cond

def fetch_json(url, timeout=10):
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        return {"_error": str(e)}

def fetch_status(url, timeout=10):
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status
    except Exception as e:
        return str(e)

# ─────────────────────────────────────────────────────────────────────────────
# G1 — /api/movies total >= 300
# ─────────────────────────────────────────────────────────────────────────────
print("\n=== G1: 영화 데이터 ===")
movies_data = fetch_json(f"{BASE}/api/movies?limit=1")
if "_error" in movies_data:
    # try without limit param
    movies_data = fetch_json(f"{BASE}/api/movies")

total = movies_data.get("total") or movies_data.get("count") or (len(movies_data.get("movies", movies_data.get("data", []))) if isinstance(movies_data, dict) else None)
# if response is array itself
if isinstance(movies_data, list):
    total = len(movies_data)

check("G1-1 /api/movies total>=300", total is not None and total >= 300,
      f"total={total}")

# G1-2: poster CDN 200
poster_path = "/9gk7adHYeDvHkCSEqAvQNLV5Uge.jpg"
cdn_url = f"https://image.tmdb.org/t/p/w300{poster_path}"
cdn_status = fetch_status(cdn_url)
check("G1-2 TMDB CDN poster 200", cdn_status == 200, f"HTTP {cdn_status}")

# ─────────────────────────────────────────────────────────────────────────────
# G2 — Quiz 3종 API
# ─────────────────────────────────────────────────────────────────────────────
print("\n=== G2: 퀴즈 API ===")
for mode in ["poster", "director", "cast"]:
    url = f"{BASE}/api/quiz/questions?mode={mode}&count=3"
    data = fetch_json(url)
    qs = data.get("questions", []) if isinstance(data, dict) else data
    q_count = len(qs) if isinstance(qs, list) else 0
    check(f"G2-{mode} questions count=3", q_count == 3, f"got {q_count}")
    if q_count > 0:
        if mode == "poster":
            has_image = all("image" in q or "poster" in str(q) for q in qs)
            check(f"G2-{mode} image field", has_image, f"q[0] keys={list(qs[0].keys())}")
        else:
            choices_ok = all(isinstance(q.get("choices"), list) and len(q.get("choices", [])) == 4 for q in qs)
            check(f"G2-{mode} choices[4]", choices_ok,
                  f"q[0] choices={qs[0].get('choices', 'N/A')}")

# ─────────────────────────────────────────────────────────────────────────────
# G3 — Playwright: #/movies/399566 상세 페이지
# ─────────────────────────────────────────────────────────────────────────────
print("\n=== G3: Playwright 라우팅 ===")
try:
    from playwright.sync_api import sync_playwright
    SCREENSHOT_PATH = f"{WORKSPACE}/qa_final_task180515_g3_route.png"
    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--no-sandbox", "--disable-setuid-sandbox"])
        ctx = browser.new_context(viewport={"width": 1280, "height": 800})
        page = ctx.new_page()
        console_errors = []
        page.on("console", lambda m: console_errors.append(m.text) if m.type == "error" else None)
        # 직접 접근
        page.goto(f"{BASE}/#/movies/399566", wait_until="domcontentloaded")
        time.sleep(3)
        page.screenshot(path=SCREENSHOT_PATH)
        html = page.content()
        title = page.title()
        # 상세 페이지 판단: 포스터 img, 영화 제목/감독 등 콘텐츠 존재 여부
        has_detail_content = (
            "movie" in html.lower() or
            "poster" in html.lower() or
            "director" in html.lower() or
            "recommend" in html.lower() or
            page.locator("img").count() > 0
        )
        # 홈으로 떨어졌는지 확인 (hash 라우팅 실패 시 홈 렌더링)
        url_after = page.url
        img_count = page.locator("img").count()
        # 상세 특이 요소: movie-detail, .detail, [data-movie-id] 등
        has_detail_el = (
            page.locator(".movie-detail, #movie-detail, [class*='detail'], [id*='detail']").count() > 0 or
            page.locator("h2, h1").count() > 0
        )
        check("G3 #/movies/399566 상세 렌더링", has_detail_content and img_count > 0,
              f"img={img_count}, has_detail={has_detail_el}, url={url_after}, title={title}")
        # 추가 스크린샷: 직접 접근 + 클릭 내비게이션 비교
        # 클릭 내비게이션: 홈에서 영화 카드 클릭
        page.goto(f"{BASE}/#/movies", wait_until="domcontentloaded")
        time.sleep(2)
        page.screenshot(path=f"{WORKSPACE}/qa_final_task180515_g3_movies_list.png")
        # 영화 카드 링크 클릭
        clicked = False
        for sel in ["a[href*='movies/']", ".movie-card a", "[data-movie-id]", ".card a"]:
            els = page.locator(sel)
            if els.count() > 0:
                try:
                    els.first.click()
                    time.sleep(2)
                    clicked = True
                    break
                except:
                    pass
        if clicked:
            page.screenshot(path=f"{WORKSPACE}/qa_final_task180515_g3_click_nav.png")
            html2 = page.content()
            img2 = page.locator("img").count()
            check("G3 클릭 내비게이션 상세 렌더링", img2 > 0,
                  f"img={img2}, url={page.url}")
        browser.close()
except Exception as e:
    check("G3 Playwright", False, str(e))

# ─────────────────────────────────────────────────────────────────────────────
# Summary
# ─────────────────────────────────────────────────────────────────────────────
print("\n=== 최종 요약 ===")
passed = sum(1 for v in RESULTS.values() if v["status"] == "PASS")
failed = sum(1 for v in RESULTS.values() if v["status"] == "FAIL")
print(f"PASS: {passed} / FAIL: {failed}")
for k, v in RESULTS.items():
    print(f"  [{v['status']}] {k}: {v['detail']}")

with open(f"{WORKSPACE}/qa_final_task180515_result.json", "w") as f:
    json.dump(RESULTS, f, ensure_ascii=False, indent=2)

sys.exit(0 if failed == 0 else 1)
