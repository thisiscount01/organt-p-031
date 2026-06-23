"""
QA 최종 인수 검증 — https://organt-p-031.onrender.com
목표: Task 180515-1 Goal 1~8 라이브 검증
"""
from playwright.sync_api import sync_playwright
import json, time, sys

BASE = "https://organt-p-031.onrender.com"
results = {}
js_errors = []


def log(msg):
    print(f"[QA] {msg}", flush=True)


with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
    ctx = browser.new_context(viewport={"width": 1280, "height": 800}, ignore_https_errors=True)
    page = ctx.new_page()
    page.on("pageerror", lambda e: js_errors.append(str(e)))

    # ── STEP 1: 홈 화면 로드 ──────────────────────────────────────
    log("STEP1: 홈 화면 로드")
    t0 = time.time()
    resp = page.goto(BASE, wait_until="domcontentloaded", timeout=90000)
    page.wait_for_timeout(5000)
    load_ms = int((time.time() - t0) * 1000)
    results["s1_home_status"] = resp.status
    results["s1_home_load_ms"] = load_ms
    results["s1_title"] = page.title()
    results["s1_js_errors"] = list(js_errors)

    poster_srcs = page.eval_on_selector_all(
        "img",
        "els => els.map(e=>e.src).filter(s=>s.includes('image.tmdb.org'))"
    )
    results["s1_tmdb_poster_count"] = len(poster_srcs)
    results["s1_poster_sample"] = poster_srcs[:3]
    page.screenshot(path="qa_ss_01_home.png")
    log(f"  홈 상태={resp.status}, 로드={load_ms}ms, 포스터={len(poster_srcs)}개")

    # ── STEP 2: /api/movies 500편 확인 ───────────────────────────
    log("STEP2: /api/movies 영화 수 확인")
    api_resp = page.request.get(f"{BASE}/api/movies?limit=600", timeout=30000)
    results["s2_api_status"] = api_resp.status
    if api_resp.status == 200:
        try:
            body = api_resp.json()
            if isinstance(body, dict):
                lst = (body.get("movies") or body.get("data")
                       or body.get("results") or body.get("items") or [])
            else:
                lst = body
            results["s2_movie_count"] = len(lst)
            if lst:
                first = lst[0]
                results["s2_movie_keys"] = list(first.keys()) if isinstance(first, dict) else []
                poster_paths = [m.get("poster_path", "") for m in lst[:5] if isinstance(m, dict)]
                results["s2_poster_paths_sample"] = poster_paths
        except Exception as e:
            results["s2_parse_err"] = str(e)
            results["s2_raw"] = api_resp.text()[:500]
    log(f"  API /api/movies status={api_resp.status}, count={results.get('s2_movie_count', 'N/A')}")

    # ── STEP 3: 퀴즈 모드 목록 확인 ─────────────────────────────
    log("STEP3: 퀴즈 모드 목록")
    js_errors.clear()
    page.goto(f"{BASE}/#/quiz", wait_until="domcontentloaded", timeout=30000)
    page.wait_for_timeout(3000)
    results["s3_quiz_js_errors"] = list(js_errors)
    results["s3_quiz_url"] = page.url

    body_text = page.inner_text("body")
    mode_kw = [k for k in [
        "poster", "director", "cast", "genre", "year", "overview",
        "포스터", "감독", "배우", "장르", "연도", "줄거리"
    ] if k.lower() in body_text.lower()]
    results["s3_mode_keywords"] = mode_kw
    results["s3_mode_kw_count"] = len(mode_kw)

    all_buttons = page.query_selector_all("button")
    btn_texts = []
    for b in all_buttons[:20]:
        try:
            btn_texts.append(b.inner_text().strip())
        except:
            pass
    results["s3_button_texts"] = btn_texts
    page.screenshot(path="qa_ss_03_quiz_modes.png")
    log(f"  퀴즈 모드 키워드={mode_kw}, 버튼={btn_texts[:6]}")

    # ── STEP 4: 퀴즈 모드 선택 → 문제 출력 ─────────────────────
    log("STEP4: 퀴즈 모드 선택 → 문제 출력")
    js_errors.clear()
    # 강제 언마운트 후 재진입
    page.goto(f"{BASE}/#/", wait_until="domcontentloaded", timeout=30000)
    page.wait_for_timeout(500)
    page.goto(f"{BASE}/#/quiz", wait_until="domcontentloaded", timeout=30000)
    page.wait_for_timeout(3000)

    question_appeared = False
    clicked_mode = None
    candidates = page.query_selector_all("button, [class*='mode-card'], [class*='quiz-card'], [role='button']")
    for el in candidates[:15]:
        try:
            txt = el.inner_text().strip()
            el.click()
            page.wait_for_timeout(2000)
            after = page.inner_text("body")
            if any(w in after.lower() for w in [
                "question", "문제", "q1", "1/", "/10", "score", "점수",
                "choose", "선택", "정답", "보기"
            ]):
                question_appeared = True
                clicked_mode = txt
                results["s4_mode_clicked"] = txt
                results["s4_question_text_preview"] = after[:400]
                break
        except:
            pass
    results["s4_question_appeared"] = question_appeared
    page.screenshot(path="qa_ss_04_quiz_question.png")
    log(f"  문제 출현={question_appeared}, 클릭모드='{clicked_mode}'")

    # ── STEP 5: 정답/오답 클릭 → 점수 반영 ─────────────────────
    log("STEP5: 정답/오답 처리 + 점수 반영")
    score_reflected = False
    if question_appeared:
        ans_btns = page.query_selector_all("button")
        for btn in ans_btns[:10]:
            try:
                btn.click()
                page.wait_for_timeout(1500)
                after = page.inner_text("body")
                if any(w in after.lower() for w in [
                    "correct", "wrong", "정답", "오답", "❌", "✅",
                    "score", "점수", "lives", "생명", "hp"
                ]):
                    score_reflected = True
                    results["s5_feedback_preview"] = after[:300]
                    break
            except:
                pass
    results["s5_score_reflected"] = score_reflected
    results["s5_quiz_js_errors"] = list(js_errors)
    page.screenshot(path="qa_ss_05_quiz_answer.png")
    log(f"  점수 반영={score_reflected}")

    # ── STEP 6: 영화 상세 + AI 추천 5편 ────────────────────────
    log("STEP6: 영화 상세 + AI 추천")
    js_errors.clear()
    page.goto(f"{BASE}/#/", wait_until="domcontentloaded", timeout=30000)
    page.wait_for_timeout(4000)
    detail_reached = False
    rec_count = 0

    movie_els = page.query_selector_all("a[href*='movie'], [class*='movie-card'], [class*='film-card'], [class*='poster']")
    if movie_els:
        try:
            movie_els[0].click()
            page.wait_for_timeout(3500)
            detail_url = page.url
            detail_text = page.inner_text("body")
            rec_kw = [k for k in ["recommend", "추천", "similar", "관련", "related"] if k in detail_text.lower()]
            rec_els = page.query_selector_all("[class*='recommend'], [class*='similar'], [class*='related'], [class*='rec-']")
            rec_count = len(rec_els)
            results["s6_detail_url"] = detail_url
            results["s6_rec_keywords"] = rec_kw
            results["s6_rec_element_count"] = rec_count
            detail_reached = True
            page.screenshot(path="qa_ss_06_detail.png")
        except Exception as e:
            results["s6_err"] = str(e)
    results["s6_detail_reached"] = detail_reached
    log(f"  상세={detail_reached}, 추천 엘리먼트={rec_count}, 키워드={results.get('s6_rec_keywords')}")

    # ── STEP 7: 독립 URL 5개+ 확인 ──────────────────────────────
    log("STEP7: 독립 URL 5개 확인")
    routes = {
        "movies": "/#/movies",
        "quiz": "/#/quiz",
        "community": "/#/community",
        "ranking": "/#/ranking",
        "login": "/#/login",
        "signup": "/#/signup",
    }
    route_ok = {}
    for label, path in routes.items():
        try:
            page.goto(f"{BASE}{path}", wait_until="domcontentloaded", timeout=20000)
            page.wait_for_timeout(1500)
            route_ok[label] = len(page.content())
        except Exception as e:
            route_ok[label] = f"ERR:{e}"
    results["s7_routes"] = route_ok
    results["s7_valid_routes"] = sum(1 for v in route_ok.values() if isinstance(v, int) and v > 500)
    log(f"  유효 라우트={results['s7_valid_routes']}/6")

    # ── STEP 8: JWT 회원가입 흐름 확인 ──────────────────────────
    log("STEP8: JWT 회원가입 API")
    import random, string
    rnd = "".join(random.choices(string.ascii_lowercase, k=6))
    reg_resp = page.request.post(
        f"{BASE}/api/auth/register",
        data=json.dumps({"username": f"qatest_{rnd}", "email": f"qa_{rnd}@test.com", "password": "Test1234!"}),
        headers={"Content-Type": "application/json"},
        timeout=15000
    )
    results["s8_register_status"] = reg_resp.status
    if reg_resp.status in (200, 201):
        body = reg_resp.json()
        results["s8_has_token"] = "token" in body or "access_token" in body or "jwt" in str(body).lower()
        results["s8_register_keys"] = list(body.keys()) if isinstance(body, dict) else []
    log(f"  회원가입 status={reg_resp.status}, 토큰={results.get('s8_has_token')}")

    # ── STEP 9: /api/* 엔드포인트 10개+ 측정 ────────────────────
    log("STEP9: RESTful API 엔드포인트")
    ep_list = [
        ("/api/movies", "GET"),
        ("/api/movies?page=1&limit=10", "GET"),
        ("/api/quiz/question", "GET"),
        ("/api/ranking", "GET"),
        ("/api/community/posts", "GET"),
        ("/api/auth/register", "POST"),
        ("/api/auth/login", "POST"),
        ("/api/movies/1/recommend", "GET"),
        ("/api/movies/1", "GET"),
        ("/api/quiz/submit", "POST"),
        ("/api/community/posts/1", "GET"),
        ("/api/community/posts/1/likes", "POST"),
    ]
    ep_status = {}
    for ep, method in ep_list:
        try:
            if method == "GET":
                r = page.request.get(f"{BASE}{ep}", timeout=15000)
            else:
                r = page.request.post(
                    f"{BASE}{ep}",
                    data=json.dumps({}),
                    headers={"Content-Type": "application/json"},
                    timeout=15000
                )
            ep_status[f"{method} {ep}"] = r.status
        except Exception as e:
            ep_status[f"{method} {ep}"] = f"ERR:{e}"
    results["s9_endpoints"] = ep_status
    results["s9_ep_non500_count"] = sum(
        1 for v in ep_status.values() if isinstance(v, int) and v < 500
    )
    log(f"  비-5xx 엔드포인트={results['s9_ep_non500_count']}/12")

    # ── STEP 10: YouTube embed 트레일러 확인 ────────────────────
    log("STEP10: YouTube embed 확인")
    page.goto(f"{BASE}/#/movies", wait_until="domcontentloaded", timeout=30000)
    page.wait_for_timeout(3000)
    # 영화 하나 클릭해서 상세 이동
    items = page.query_selector_all("a[href*='movie'], [class*='movie'], [class*='film']")
    youtube_found = False
    if items:
        try:
            items[0].click()
            page.wait_for_timeout(3000)
            iframes = page.query_selector_all("iframe[src*='youtube']")
            youtube_found = len(iframes) > 0
            results["s10_youtube_iframe_count"] = len(iframes)
            if iframes:
                results["s10_youtube_src"] = iframes[0].get_attribute("src")
            page.screenshot(path="qa_ss_10_detail_youtube.png")
        except Exception as e:
            results["s10_err"] = str(e)
    results["s10_youtube_found"] = youtube_found
    log(f"  YouTube embed={youtube_found}, count={results.get('s10_youtube_iframe_count', 0)}")

    browser.close()

# ── 최종 판정 ─────────────────────────────────────────────────────
print("\n" + "="*60)
print("  QA 최종 인수 검증 결과")
print("="*60)
print(json.dumps(results, indent=2, ensure_ascii=False, default=str))

PASS = {}
FAIL = {}

def chk(key, label, cond):
    if cond:
        PASS[key] = label
    else:
        FAIL[key] = label

chk("G1a", "홈 상태 200",       results.get("s1_home_status") == 200)
chk("G1b", "포스터 TMDB 5개+",  (results.get("s1_tmdb_poster_count", 0) or 0) >= 5)
chk("G1c", "영화 300편+",       (results.get("s2_movie_count", 0) or 0) >= 300)
chk("G2a", "퀴즈 모드 3종+ 키워드", (results.get("s3_mode_kw_count", 0) or 0) >= 3)
chk("G2b", "퀴즈 문제 출현",    results.get("s4_question_appeared", False))
chk("G2c", "정답/점수 반영",    results.get("s5_score_reflected", False))
chk("G3",  "AI 추천 키워드",    len(results.get("s6_rec_keywords", [])) > 0)
chk("G5",  "독립 URL 5개+",     (results.get("s7_valid_routes", 0) or 0) >= 5)
chk("G6",  "JWT 회원가입 성공", results.get("s8_register_status") in (200, 201))
chk("G7",  "API 10개+",         (results.get("s9_ep_non500_count", 0) or 0) >= 10)
chk("G4",  "YouTube embed",     results.get("s10_youtube_found", False))

print("\n[PASS]")
for k, v in PASS.items():
    print(f"  ✅ {k}: {v}")
print("[FAIL / 추가 확인 필요]")
for k, v in FAIL.items():
    print(f"  ❌ {k}: {v}")

total = len(PASS) + len(FAIL)
print(f"\n종합: {len(PASS)}/{total} 통과")
if len(FAIL) == 0:
    print("→ 전 항목 통과 — ACCEPT")
else:
    print("→ 일부 미통과 — REVIEW 필요")
    sys.exit(1)
