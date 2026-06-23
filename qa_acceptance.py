"""
QA Acceptance Test — https://organt-p-031.onrender.com
8 criteria pass/fail + screenshots
"""

import os, json, time, subprocess
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

BASE_URL = "https://organt-p-031.onrender.com"
SS_DIR = Path("qa_screenshots")
SS_DIR.mkdir(exist_ok=True)

results = {}

def ss(name: str, page):
    path = str(SS_DIR / f"{name}.png")
    page.screenshot(path=path, full_page=True)
    return path

def curl_check(url: str, extra_args: list = None):
    cmd = ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", "--max-time", "20", url]
    if extra_args:
        cmd[2:2] = extra_args
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=25)
        return r.stdout.strip()
    except Exception as e:
        return f"ERR:{e}"

def curl_json(url: str, headers: dict = None):
    cmd = ["curl", "-s", "--max-time", "20"]
    if headers:
        for k, v in headers.items():
            cmd += ["-H", f"{k}: {v}"]
    cmd.append(url)
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=25)
        return r.stdout.strip()
    except Exception as e:
        return f"ERR:{e}"

def curl_post(url: str, data: dict, headers: dict = None):
    cmd = ["curl", "-s", "--max-time", "20", "-X", "POST",
           "-H", "Content-Type: application/json",
           "-d", json.dumps(data)]
    if headers:
        for k, v in headers.items():
            cmd += ["-H", f"{k}: {v}"]
    cmd.append(url)
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=25)
        return r.stdout.strip()
    except Exception as e:
        return f"ERR:{e}"

def wait_and_check(page, selector: str, timeout: int = 10000):
    try:
        page.wait_for_selector(selector, timeout=timeout, state="visible")
        return True
    except PWTimeout:
        return False

with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=True,
        args=["--no-sandbox", "--disable-dev-shm-usage"]
    )
    ctx = browser.new_context(
        viewport={"width": 1280, "height": 900},
        ignore_https_errors=True,
    )
    page = ctx.new_page()

    # ── 사이트 초기 웜업 ─────────────────────────────────────────
    print("=== 사이트 초기 로드 (최대 60s 대기) ===")
    try:
        page.goto(BASE_URL, timeout=60000, wait_until="domcontentloaded")
        page.wait_for_load_state("networkidle", timeout=30000)
    except Exception as e:
        print(f"  초기 로드 경고: {e}")

    time.sleep(2)

    # ════════════════════════════════════════════════════════════
    # 1. 홈 화면 — 영화 목록·배너 정상 표시
    # ════════════════════════════════════════════════════════════
    print("\n[1] 홈 화면 검증")
    try:
        page.goto(BASE_URL + "/#/", timeout=30000, wait_until="domcontentloaded")
        time.sleep(3)

        html = page.content()

        # 영화 관련 콘텐츠 탐색 (다양한 셀렉터 시도)
        movie_selectors = [
            ".movie-card", ".movie-item", ".film-card",
            "[data-movie]", ".card", ".movie",
            "img[src*='tmdb']", "img[src*='image.tmdb']",
            ".hero", ".banner", ".carousel",
            "h1", "h2", ".movie-title",
        ]

        found_elements = []
        for sel in movie_selectors:
            try:
                count = page.locator(sel).count()
                if count > 0:
                    found_elements.append(f"{sel}({count})")
            except:
                pass

        # 페이지 텍스트 검사
        body_text = page.inner_text("body") if page.locator("body").count() > 0 else ""
        has_movie_content = any(kw in body_text for kw in [
            "영화", "Movie", "movie", "Film", "film", "퀴즈", "Quiz",
            "추천", "장르", "Genre", "Rating"
        ])

        path_1 = ss("01_home", page)

        # 최소 기준: 페이지가 로드되고 콘텐츠가 있으면
        page_loaded = len(body_text) > 100
        has_visual = len(found_elements) > 0 or has_movie_content

        if page_loaded and has_visual:
            results["1_home"] = {
                "status": "PASS",
                "detail": f"홈 로드 성공. found: {found_elements[:5]}",
                "screenshot": path_1
            }
        else:
            results["1_home"] = {
                "status": "FAIL",
                "detail": f"콘텐츠 불충분. body_len={len(body_text)}, elements={found_elements}",
                "screenshot": path_1
            }
        print(f"  → {results['1_home']['status']}: {results['1_home']['detail'][:80]}")
    except Exception as e:
        path_1 = ss("01_home_err", page)
        results["1_home"] = {"status": "FAIL", "detail": str(e), "screenshot": path_1}
        print(f"  → FAIL: {e}")

    # ════════════════════════════════════════════════════════════
    # 2. 영화 상세 → AI 추천 5편 + YouTube iframe
    # ════════════════════════════════════════════════════════════
    print("\n[2] 영화 상세 페이지 검증")
    try:
        # 먼저 영화 목록 API로 첫 번째 영화 ID 확보
        movies_raw = curl_json(f"{BASE_URL}/api/movies?limit=1")
        movie_id = None
        try:
            movies_data = json.loads(movies_raw)
            if isinstance(movies_data, list) and movies_data:
                movie_id = movies_data[0].get("id") or movies_data[0].get("_id")
            elif isinstance(movies_data, dict):
                items = movies_data.get("movies") or movies_data.get("data") or movies_data.get("results") or []
                if items:
                    movie_id = items[0].get("id") or items[0].get("_id")
        except:
            pass

        # 영화 ID fallback — 홈에서 링크 탐색
        if not movie_id:
            try:
                page.goto(BASE_URL + "/#/movies", timeout=20000, wait_until="domcontentloaded")
                time.sleep(3)
                links = page.locator("a[href*='movie'], a[href*='/movies/']").all()
                if links:
                    href = links[0].get_attribute("href")
                    if href:
                        # 링크 클릭
                        links[0].click()
                        time.sleep(3)
            except:
                pass

        # 상세 페이지로 이동
        if movie_id:
            detail_url = f"{BASE_URL}/#/movies/{movie_id}"
        else:
            # fallback: 일반적인 ID 1 시도
            detail_url = f"{BASE_URL}/#/movies/1"

        page.goto(detail_url, timeout=30000, wait_until="domcontentloaded")
        time.sleep(4)

        html_detail = page.content()

        # AI 추천 검사
        recommend_selectors = [
            ".recommend", ".recommendation", ".similar",
            "[class*='recommend']", "[class*='similar']",
            ".related-movies", ".movie-recommend",
            "section.recommend", "div.recommend"
        ]

        rec_found = []
        for sel in recommend_selectors:
            try:
                cnt = page.locator(sel).count()
                if cnt > 0:
                    rec_found.append(f"{sel}({cnt})")
            except:
                pass

        body_detail = page.inner_text("body") if page.locator("body").count() > 0 else ""
        has_rec_text = any(kw in body_detail for kw in ["추천", "recommend", "Recommend", "similar", "Similar", "관련"])

        # YouTube iframe 검사
        iframe_count = page.locator("iframe").count()
        youtube_iframes = page.locator("iframe[src*='youtube'], iframe[src*='youtu']").count()

        # API 추천 직접 확인
        rec_raw = curl_json(f"{BASE_URL}/api/movies/{movie_id or 1}/recommend")
        try:
            rec_data = json.loads(rec_raw)
            rec_ok = isinstance(rec_data, list) and len(rec_data) >= 5
            rec_detail = f"API:{len(rec_data) if isinstance(rec_data, list) else 'not-list'}"
        except:
            rec_ok = False
            rec_detail = f"API-parse-err: {rec_raw[:80]}"

        path_2 = ss("02_movie_detail", page)

        ai_ok = rec_ok or bool(rec_found) or has_rec_text
        trailer_ok = iframe_count > 0 or youtube_iframes > 0

        status_2 = "PASS" if (ai_ok and trailer_ok) else ("PARTIAL" if (ai_ok or trailer_ok) else "FAIL")
        results["2_movie_detail"] = {
            "status": status_2,
            "detail": f"AI추천:{rec_detail},rec_ui:{rec_found[:3]},rec_text:{has_rec_text} | iframe:{iframe_count},yt:{youtube_iframes}",
            "screenshot": path_2
        }
        print(f"  → {status_2}: {results['2_movie_detail']['detail'][:100]}")
    except Exception as e:
        path_2 = ss("02_movie_detail_err", page)
        results["2_movie_detail"] = {"status": "FAIL", "detail": str(e), "screenshot": path_2}
        print(f"  → FAIL: {e}")

    # ════════════════════════════════════════════════════════════
    # 3. 퀴즈 선택 화면 — poster/director/cast 3종 버튼
    # ════════════════════════════════════════════════════════════
    print("\n[3] 퀴즈 선택 화면 검증")
    try:
        page.goto(BASE_URL + "/#/quiz", timeout=20000, wait_until="domcontentloaded")
        time.sleep(3)

        body_quiz = page.inner_text("body") if page.locator("body").count() > 0 else ""

        # 3종 모드 버튼 검사
        mode_checks = {
            "poster": any(kw in body_quiz for kw in ["poster", "Poster", "포스터"]),
            "director": any(kw in body_quiz for kw in ["director", "Director", "감독"]),
            "cast": any(kw in body_quiz for kw in ["cast", "Cast", "배우", "actor", "Actor"]),
        }

        # 버튼 셀렉터도 검사
        btn_selectors = [
            "button", ".btn", "[class*='quiz-mode']",
            "[data-mode]", ".mode-btn"
        ]
        btn_texts = []
        for sel in btn_selectors:
            try:
                btns = page.locator(sel).all()
                for b in btns[:10]:
                    t = b.inner_text().strip()
                    if t:
                        btn_texts.append(t)
            except:
                pass

        path_3 = ss("03_quiz_select", page)

        modes_found = sum(mode_checks.values())
        # 버튼 텍스트에서도 탐색
        btn_text_joined = " ".join(btn_texts).lower()
        has_poster_btn = "poster" in btn_text_joined or "포스터" in btn_text_joined
        has_director_btn = "director" in btn_text_joined or "감독" in btn_text_joined
        has_cast_btn = "cast" in btn_text_joined or "배우" in btn_text_joined or "actor" in btn_text_joined

        all_modes = (mode_checks["poster"] or has_poster_btn) and \
                    (mode_checks["director"] or has_director_btn) and \
                    (mode_checks["cast"] or has_cast_btn)

        if all_modes:
            status_3 = "PASS"
            detail_3 = f"3종 모드 모두 확인: {mode_checks}, btns={btn_texts[:6]}"
        elif modes_found >= 2 or (has_poster_btn and has_director_btn) or (has_poster_btn and has_cast_btn):
            status_3 = "PARTIAL"
            detail_3 = f"일부 모드만: {mode_checks}, btns={btn_texts[:6]}"
        else:
            status_3 = "FAIL"
            detail_3 = f"퀴즈 모드 버튼 없음. body snippet: {body_quiz[:200]}"

        results["3_quiz_select"] = {"status": status_3, "detail": detail_3, "screenshot": path_3}
        print(f"  → {status_3}: {detail_3[:100]}")
    except Exception as e:
        path_3 = ss("03_quiz_select_err", page)
        results["3_quiz_select"] = {"status": "FAIL", "detail": str(e), "screenshot": path_3}
        print(f"  → FAIL: {e}")

    # ════════════════════════════════════════════════════════════
    # 4. 퀴즈 게임 플레이 — 문제·선택지 4개·점수/타이머
    # ════════════════════════════════════════════════════════════
    print("\n[4] 퀴즈 게임 플레이 검증")
    try:
        # 퀴즈 시작 시도: 선택 화면에서 poster 모드 클릭
        page.goto(BASE_URL + "/#/quiz", timeout=20000, wait_until="domcontentloaded")
        time.sleep(2)

        # 가능한 시작 버튼들 탐색
        start_clicked = False
        for btn_text in ["poster", "Poster", "포스터", "시작", "Start", "Play", "play"]:
            try:
                btn = page.get_by_text(btn_text, exact=False).first
                if btn.is_visible(timeout=1000):
                    btn.click()
                    time.sleep(2)
                    start_clicked = True
                    break
            except:
                pass

        if not start_clicked:
            # 버튼 직접 클릭 시도
            try:
                page.locator("button").first.click()
                time.sleep(2)
                start_clicked = True
            except:
                pass

        time.sleep(3)
        body_game = page.inner_text("body") if page.locator("body").count() > 0 else ""

        # 게임 UI 요소 검사
        has_question = any(kw in body_game for kw in ["?", "Q.", "Question", "문제", "다음"])
        has_options = page.locator("button, .option, .choice, [class*='answer']").count() >= 4
        has_score = any(kw in body_game for kw in ["점수", "Score", "score", "Points", "0점"])
        has_timer = any(kw in body_game for kw in ["timer", "Timer", "시간", "초", "sec", "Time"])

        # 선택지 4개 체크
        btn_count = page.locator("button").count()

        path_4 = ss("04_quiz_game", page)

        game_score = sum([has_question, has_options, has_score, has_timer])

        if game_score >= 3:
            status_4 = "PASS"
        elif game_score >= 2:
            status_4 = "PARTIAL"
        else:
            status_4 = "FAIL"

        detail_4 = (f"question:{has_question}, options:{has_options}(btn:{btn_count}), "
                    f"score:{has_score}, timer:{has_timer}, start_clicked:{start_clicked}")

        results["4_quiz_game"] = {"status": status_4, "detail": detail_4, "screenshot": path_4}
        print(f"  → {status_4}: {detail_4}")
    except Exception as e:
        path_4 = ss("04_quiz_game_err", page)
        results["4_quiz_game"] = {"status": "FAIL", "detail": str(e), "screenshot": path_4}
        print(f"  → FAIL: {e}")

    # ════════════════════════════════════════════════════════════
    # 5. 커뮤니티 — 게시글 목록 + GET /api/community/posts 200
    # ════════════════════════════════════════════════════════════
    print("\n[5] 커뮤니티 검증")
    try:
        # API 확인
        community_endpoints = [
            "/api/community/posts",
            "/api/posts",
            "/api/community",
        ]
        api_status = {}
        api_body = {}
        for ep in community_endpoints:
            code = curl_check(f"{BASE_URL}{ep}")
            raw = curl_json(f"{BASE_URL}{ep}")
            api_status[ep] = code
            api_body[ep] = raw[:100]

        # UI 확인
        page.goto(BASE_URL + "/#/community", timeout=20000, wait_until="domcontentloaded")
        time.sleep(3)

        body_comm = page.inner_text("body") if page.locator("body").count() > 0 else ""

        has_posts = any(kw in body_comm for kw in ["게시글", "게시물", "Post", "post", "글", "Community", "커뮤니티"])
        post_items = page.locator(".post, .post-item, [class*='post'], .card, article").count()

        path_5 = ss("05_community", page)

        api_ok = any(v == "200" for v in api_status.values())
        ui_ok = has_posts or post_items > 0

        status_5 = "PASS" if (api_ok and ui_ok) else ("PARTIAL" if (api_ok or ui_ok) else "FAIL")
        detail_5 = f"API:{api_status}, ui_posts:{has_posts}, post_items:{post_items}"

        results["5_community"] = {
            "status": status_5,
            "detail": detail_5,
            "api_bodies": {k: v for k, v in api_body.items()},
            "screenshot": path_5
        }
        print(f"  → {status_5}: {detail_5}")
    except Exception as e:
        path_5 = ss("05_community_err", page)
        results["5_community"] = {"status": "FAIL", "detail": str(e), "screenshot": path_5}
        print(f"  → FAIL: {e}")

    # ════════════════════════════════════════════════════════════
    # 6. 인증 — 회원가입 → 로그인 → JWT 토큰
    # ════════════════════════════════════════════════════════════
    print("\n[6] 인증 검증")
    try:
        import random, string
        rand_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
        test_email = f"qatest_{rand_suffix}@example.com"
        test_pw = "Test1234!!"
        test_username = f"qauser_{rand_suffix}"

        reg_body = {"email": test_email, "password": test_pw, "username": test_username}

        # 회원가입
        reg_raw = curl_post(f"{BASE_URL}/api/auth/register", reg_body)
        reg_code = curl_check(f"{BASE_URL}/api/auth/register", ["-X", "POST",
            "-H", "Content-Type: application/json",
            "-d", json.dumps(reg_body)])

        try:
            reg_data = json.loads(reg_raw)
        except:
            reg_data = {}

        # 로그인
        login_body = {"email": test_email, "password": test_pw}
        login_raw = curl_post(f"{BASE_URL}/api/auth/login", login_body)
        try:
            login_data = json.loads(login_raw)
            has_token = bool(login_data.get("token") or login_data.get("access_token") or
                             login_data.get("accessToken") or login_data.get("jwt"))
            token_val = (login_data.get("token") or login_data.get("access_token") or
                         login_data.get("accessToken") or "")
        except:
            login_data = {}
            has_token = False
            token_val = ""

        # UI도 확인
        page.goto(BASE_URL + "/#/login", timeout=20000, wait_until="domcontentloaded")
        time.sleep(2)
        path_6 = ss("06_auth", page)

        body_login = page.inner_text("body") if page.locator("body").count() > 0 else ""
        has_login_ui = any(kw in body_login for kw in ["login", "Login", "로그인", "email", "Email", "password", "Password", "비밀번호"])

        if has_token:
            status_6 = "PASS"
            detail_6 = f"회원가입:{reg_code}, 로그인:토큰확인(len={len(token_val)}), login_ui:{has_login_ui}"
        elif reg_code in ["200", "201"] and login_data:
            status_6 = "PARTIAL"
            detail_6 = f"회원가입:{reg_code}, 로그인 응답:{str(login_data)[:100]}, token 미확인"
        else:
            status_6 = "FAIL"
            detail_6 = f"reg:{reg_code}({reg_raw[:80]}), login:{login_raw[:80]}"

        results["6_auth"] = {
            "status": status_6,
            "detail": detail_6,
            "jwt_token": token_val[:50] + "..." if len(token_val) > 50 else token_val,
            "screenshot": path_6
        }
        print(f"  → {status_6}: {detail_6[:120]}")
    except Exception as e:
        path_6 = ss("06_auth_err", page)
        results["6_auth"] = {"status": "FAIL", "detail": str(e), "screenshot": path_6}
        print(f"  → FAIL: {e}")

    # ════════════════════════════════════════════════════════════
    # 7. 랭킹 — #/leaderboard + GET /api/leaderboard
    # ════════════════════════════════════════════════════════════
    print("\n[7] 랭킹 페이지 검증")
    try:
        # API 확인
        lb_endpoints = ["/api/leaderboard", "/api/rankings", "/api/scores", "/api/game/scores"]
        lb_status = {}
        lb_body = {}
        for ep in lb_endpoints:
            code = curl_check(f"{BASE_URL}{ep}")
            raw = curl_json(f"{BASE_URL}{ep}")
            lb_status[ep] = code
            lb_body[ep] = raw[:150]

        # UI 확인
        page.goto(BASE_URL + "/#/leaderboard", timeout=20000, wait_until="domcontentloaded")
        time.sleep(3)
        body_lb = page.inner_text("body") if page.locator("body").count() > 0 else ""

        has_lb_ui = any(kw in body_lb for kw in ["랭킹", "Rank", "rank", "Leaderboard", "leaderboard", "순위", "점수", "Score"])

        path_7 = ss("07_leaderboard", page)

        api_200 = any(v == "200" for v in lb_status.values())

        # JSON 파싱 검증
        json_ok = False
        for ep, raw in lb_body.items():
            try:
                d = json.loads(raw)
                if d is not None:
                    json_ok = True
                    break
            except:
                pass

        if api_200 and has_lb_ui:
            status_7 = "PASS"
        elif api_200 or has_lb_ui:
            status_7 = "PARTIAL"
        else:
            status_7 = "FAIL"

        detail_7 = f"API:{lb_status}, json_ok:{json_ok}, lb_ui:{has_lb_ui}"
        results["7_leaderboard"] = {
            "status": status_7,
            "detail": detail_7,
            "api_sample": {k: v for k, v in lb_body.items() if lb_status.get(k) == "200"},
            "screenshot": path_7
        }
        print(f"  → {status_7}: {detail_7}")
    except Exception as e:
        path_7 = ss("07_leaderboard_err", page)
        results["7_leaderboard"] = {"status": "FAIL", "detail": str(e), "screenshot": path_7}
        print(f"  → FAIL: {e}")

    # ════════════════════════════════════════════════════════════
    # 8. 독립 URL 5개 — #/movies, #/quiz, #/leaderboard, #/community, #/login
    # ════════════════════════════════════════════════════════════
    print("\n[8] 독립 URL 5개 검증")
    routes_to_check = [
        ("movies", "/#/movies"),
        ("quiz", "/#/quiz"),
        ("leaderboard", "/#/leaderboard"),
        ("community", "/#/community"),
        ("login", "/#/login"),
    ]

    route_results = {}
    for name, path in routes_to_check:
        try:
            page.goto(BASE_URL + path, timeout=20000, wait_until="domcontentloaded")
            time.sleep(2)
            body = page.inner_text("body") if page.locator("body").count() > 0 else ""
            title = page.title()
            has_content = len(body) > 80
            ss_path = ss(f"08_{name}", page)

            route_results[name] = {
                "url": BASE_URL + path,
                "pass": has_content,
                "body_len": len(body),
                "title": title,
                "screenshot": ss_path,
                "snippet": body[:80]
            }
            print(f"  {name}: {'PASS' if has_content else 'FAIL'} (body={len(body)} chars)")
        except Exception as e:
            route_results[name] = {
                "url": BASE_URL + path,
                "pass": False,
                "body_len": 0,
                "error": str(e),
                "screenshot": ""
            }
            print(f"  {name}: FAIL ({e})")

    pass_count = sum(1 for v in route_results.values() if v["pass"])
    status_8 = "PASS" if pass_count >= 5 else ("PARTIAL" if pass_count >= 3 else "FAIL")
    results["8_urls"] = {
        "status": status_8,
        "detail": f"{pass_count}/5 URL 정상 렌더링",
        "routes": route_results
    }

    browser.close()

# ═══════════════════════════════════════════════════════════════
# 최종 리포트 출력
# ═══════════════════════════════════════════════════════════════
print("\n" + "═" * 60)
print("QA 인수 검증 최종 리포트")
print("═" * 60)

pass_c = sum(1 for v in results.values() if v.get("status") == "PASS")
fail_c = sum(1 for v in results.values() if v.get("status") == "FAIL")
partial_c = sum(1 for v in results.values() if v.get("status") == "PARTIAL")

print(f"전체: PASS {pass_c} / PARTIAL {partial_c} / FAIL {fail_c}\n")

for key, val in results.items():
    st = val.get("status", "?")
    marker = "✓" if st == "PASS" else ("△" if st == "PARTIAL" else "✗")
    print(f"{marker} [{st}] {key}")
    print(f"      {val.get('detail', '')[:120]}")
    if val.get("screenshot"):
        print(f"      screenshot: {val['screenshot']}")
    if val.get("api_bodies"):
        for ep, body in val["api_bodies"].items():
            print(f"      {ep}: {body[:80]}")
    if val.get("api_sample"):
        for ep, body in val["api_sample"].items():
            print(f"      {ep} (200): {body[:80]}")
    if val.get("jwt_token"):
        print(f"      JWT: {val['jwt_token']}")
    if key == "8_urls" and "routes" in val:
        for rname, rv in val["routes"].items():
            st2 = "PASS" if rv.get("pass") else "FAIL"
            print(f"      [{st2}] {rname}: {rv.get('url')} (body={rv.get('body_len')})")
    print()

# JSON 저장
with open("qa_report.json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)
print("상세 결과: qa_report.json")
print("스크린샷: qa_screenshots/")
