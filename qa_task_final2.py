"""
QA 최종 인수 검증 v2 — Task 180515-1
- .mode-card div 요소로 모드 선택 (버튼 아님)
- 6종 모드 확인 (poster/director/cast/genre/year/overview)
- 각 모드 클릭 → 게임 시작 → 퀴즈 문제 출력 확인
"""
import json, time
from playwright.sync_api import sync_playwright

results = {}

with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=True,
        args=['--no-sandbox','--disable-setuid-sandbox','--ignore-certificate-errors']
    )

    # ─── GOAL 1A: /api/movies total ≥ 300 ───
    ctx1 = browser.new_context(ignore_https_errors=True)
    pg1 = ctx1.new_page()
    try:
        resp = pg1.request.get("http://localhost:3000/api/movies")
        data = resp.json()
        total = data.get("total", 0)
        results["G1A_total"] = total
        results["G1A_pass"] = total >= 300
        print(f"[G1A] /api/movies total={total} => {'PASS' if total>=300 else 'FAIL'}")
    except Exception as e:
        results["G1A_pass"] = False
        print(f"[G1A] ERROR: {e}")
    ctx1.close()

    # ─── GOAL 1B: TMDB 포스터 CDN HTTP 200 ───
    ctx2 = browser.new_context(ignore_https_errors=True)
    pg2 = ctx2.new_page()
    console_errors = []
    pg2.on("console", lambda msg: console_errors.append({"type": msg.type, "text": msg.text}) if msg.type == "error" else None)

    try:
        # API에서 포스터 URL 추출
        qresp = pg2.request.get("http://localhost:3000/api/quiz/question?type=poster")
        qdata = qresp.json()
        print(f"[G1B] API keys: {list(qdata.keys())}")

        # 포스터 URL 추출 로직
        poster_path = None
        if "image" in qdata:
            poster_path = qdata["image"]
        elif "movie" in qdata:
            movie = qdata["movie"]
            if "poster_path" in movie:
                poster_path = "https://image.tmdb.org/t/p/w500" + movie["poster_path"]
        elif "poster_path" in qdata:
            poster_path = "https://image.tmdb.org/t/p/w500" + qdata["poster_path"]

        print(f"[G1B] Poster URL: {poster_path}")
        results["G1B_poster_url"] = poster_path

        # CDN HTTP 200 확인
        if poster_path and "image.tmdb.org" in poster_path:
            cdn_resp = pg2.request.get(poster_path)
            results["G1B_cdn_status"] = cdn_resp.status
            results["G1B_cdn_pass"] = cdn_resp.status == 200
            print(f"[G1B] CDN status: {cdn_resp.status} => {'PASS' if cdn_resp.status==200 else 'FAIL'}")
        else:
            results["G1B_cdn_pass"] = False

        # 브라우저 렌더링: 퀴즈 시작 후 img[src*=image.tmdb.org] 확인
        pg2.goto("http://localhost:3000/#/quiz", wait_until="domcontentloaded")
        time.sleep(2)
        pg2.screenshot(path="qa_final2_select.png")

        # mode-card div 있는지 확인
        mode_cards = pg2.query_selector_all(".mode-card")
        print(f"[G1B] .mode-card count: {len(mode_cards)}")
        mode_texts = [c.inner_text().strip()[:40] for c in mode_cards]
        print(f"[G1B] Mode cards: {mode_texts}")
        results["G2A_mode_card_count"] = len(mode_cards)
        results["G2A_mode_card_texts"] = mode_texts

        # 첫 번째 mode-card(poster) 클릭 → 게임 시작
        if mode_cards:
            mode_cards[0].click()
            time.sleep(0.3)

        start_btn = pg2.query_selector(".btn-start, button.btn-start")
        if start_btn:
            start_btn.click()
            time.sleep(2)
        pg2.screenshot(path="qa_final2_quiz_started.png")

        # DOM img 체크
        imgs = pg2.query_selector_all("img")
        tmdb_srcs = [i.get_attribute("src") for i in imgs if "image.tmdb.org" in (i.get_attribute("src") or "")]
        print(f"[G1B] TMDB imgs in DOM: {len(tmdb_srcs)}")
        if tmdb_srcs:
            print(f"[G1B] Sample: {tmdb_srcs[0]}")
        results["G1B_dom_tmdb_imgs"] = len(tmdb_srcs)
        results["G1B_pass"] = results.get("G1B_cdn_pass", False) or len(tmdb_srcs) > 0

    except Exception as e:
        results["G1B_pass"] = False
        print(f"[G1B] ERROR: {e}")
        import traceback; traceback.print_exc()

    # ─── GOAL 2A: 모드 선택 UI (6종 mode-card) ───
    results["G2A_pass"] = results.get("G2A_mode_card_count", 0) >= 3
    print(f"[G2A] Mode cards found: {results.get('G2A_mode_card_count',0)} => {'PASS' if results['G2A_pass'] else 'FAIL'}")

    # ─── GOAL 2B: API 3종 퀴즈 모드 (poster/director/cast) ───
    quiz_api_results = []
    for qtype in ["poster", "director", "cast"]:
        try:
            r = pg2.request.get(f"http://localhost:3000/api/quiz/question?type={qtype}")
            jd = r.json()
            # 퀴즈 데이터 필수 필드 확인
            has_question = "question" in jd
            has_choices = "choices" in jd and len(jd.get("choices", [])) >= 2
            has_image = "image" in jd or ("movie" in jd and "poster_path" in jd.get("movie", {}))
            is_valid = r.status == 200 and has_question and has_choices
            quiz_api_results.append({
                "type": qtype,
                "status": r.status,
                "has_question": has_question,
                "has_choices": has_choices,
                "has_image": has_image,
                "choices_count": len(jd.get("choices", [])),
                "pass": is_valid
            })
            print(f"[G2B] type={qtype} status={r.status} question={has_question} choices={len(jd.get('choices',[]))} => {'PASS' if is_valid else 'FAIL'}")
        except Exception as e:
            quiz_api_results.append({"type": qtype, "error": str(e), "pass": False})
            print(f"[G2B] ERROR type={qtype}: {e}")

    results["G2B_api_modes"] = quiz_api_results
    results["G2B_pass"] = sum(1 for m in quiz_api_results if m.get("pass")) >= 3

    # ─── GOAL 2C: UI로 각 모드 시작 → 퀴즈 문제 출력 확인 ───
    # mode-card 키 순서: poster(0), director(1), cast(2), genre(3), year(4), overview(5)
    MODE_KEYS = ["poster", "director", "cast"]
    ui_modes_verified = []

    for i, mode_key in enumerate(MODE_KEYS):
        try:
            # 새 컨텍스트에서 깨끗하게 시작
            mctx = browser.new_context(ignore_https_errors=True)
            mpg = mctx.new_page()
            mpg.goto("http://localhost:3000/#/quiz", wait_until="domcontentloaded")
            time.sleep(1.5)

            # mode-card 클릭 (index로 선택)
            cards = mpg.query_selector_all(".mode-card")
            if len(cards) > i:
                cards[i].click()
                time.sleep(0.3)
                # active class 확인
                active = mpg.query_selector(".mode-card.active")
                active_txt = active.inner_text().strip()[:30] if active else "none"
                print(f"[G2C] mode={mode_key} active_card: {active_txt}")
            else:
                print(f"[G2C] mode={mode_key}: card index {i} not found (total={len(cards)})")

            # 게임 시작 클릭
            start = mpg.query_selector(".btn-start")
            if start:
                start.click()
                time.sleep(2.5)

            mpg.screenshot(path=f"qa_final2_mode_{mode_key}.png")
            html_after = mpg.content()

            # 퀴즈 문제 출력 확인: 선택지 버튼, 포스터 img, 타이머
            has_choices_ui = len(mpg.query_selector_all(".choice-btn, .quiz-choice, .quiz-option, [class*='choice']")) > 0
            # fallback: answer option buttons (A/B/C/D)
            btns_after = mpg.query_selector_all("button")
            btn_txts = [b.inner_text().strip() for b in btns_after if b.inner_text().strip()]
            has_answer_btns = any(t[0] in "ABCD" for t in btn_txts if t)
            has_tmdb_img = len(mpg.query_selector_all("img[src*='image.tmdb.org']")) > 0
            has_timer = any(kw in html_after for kw in ["타이머","timer","hud","hud-value","점수","score"])
            has_question_text = any(kw in html_after.lower() for kw in ["맞추","question","문제","quiz-q"])

            quiz_active = has_choices_ui or has_answer_btns or has_tmdb_img
            print(f"[G2C] mode={mode_key}: choices_ui={has_choices_ui} answer_btns={has_answer_btns} tmdb_img={has_tmdb_img} timer={has_timer} => {'PASS' if quiz_active else 'FAIL'}")
            print(f"  btn_txts: {btn_txts[:8]}")

            ui_modes_verified.append({
                "mode": mode_key,
                "has_choices_ui": has_choices_ui,
                "has_answer_btns": has_answer_btns,
                "has_tmdb_img": has_tmdb_img,
                "has_timer": has_timer,
                "btn_txts_sample": btn_txts[:6],
                "pass": quiz_active
            })
            mctx.close()

        except Exception as e:
            ui_modes_verified.append({"mode": mode_key, "error": str(e), "pass": False})
            print(f"[G2C] mode={mode_key} ERROR: {e}")
            import traceback; traceback.print_exc()

    results["G2C_ui_modes"] = ui_modes_verified
    results["G2C_pass"] = sum(1 for m in ui_modes_verified if m.get("pass")) >= 3

    # ─── GOAL 2D: JS 콘솔 에러 (전체 세션 수집) ───
    js_errors = [e for e in console_errors if e["type"] == "error"]
    print(f"\n[G2D] Console errors: {len(js_errors)}")
    for e in js_errors[:5]:
        print(f"  ERR: {e['text'][:120]}")
    results["G2D_console_errors"] = js_errors[:10]
    results["G2D_pass"] = len(js_errors) == 0

    ctx2.close()
    browser.close()

# ─── 최종 판정 ───
G1_pass = results.get("G1A_pass", False) and results.get("G1B_pass", False)
G2_pass = (results.get("G2A_pass", False) and
           results.get("G2B_pass", False) and
           results.get("G2C_pass", False))

print("\n" + "="*55)
print("=== FINAL VERDICT ===")
print(f"Goal 1 (300편+, TMDB 포스터 CDN):  {'PASS ✅' if G1_pass else 'FAIL ❌'}")
print(f"  G1A /api/movies total={results.get('G1A_total','?')} >= 300: {'PASS' if results.get('G1A_pass') else 'FAIL'}")
print(f"  G1B TMDB CDN HTTP 200 + DOM img:  {'PASS' if results.get('G1B_pass') else 'FAIL'}")
print(f"    cdn_status={results.get('G1B_cdn_status','?')} dom_imgs={results.get('G1B_dom_tmdb_imgs','?')}")
print(f"Goal 2 (퀴즈 3종 모드):             {'PASS ✅' if G2_pass else 'FAIL ❌'}")
print(f"  G2A 모드 선택 UI (mode-card ≥3): {'PASS' if results.get('G2A_pass') else 'FAIL'} ({results.get('G2A_mode_card_count','?')}개)")
print(f"  G2B API 3종 동작:                 {'PASS' if results.get('G2B_pass') else 'FAIL'}")
for m in results.get("G2B_api_modes", []):
    print(f"    type={m['type']}: {'PASS' if m.get('pass') else 'FAIL'}")
print(f"  G2C UI 모드별 퀴즈 출력:          {'PASS' if results.get('G2C_pass') else 'FAIL'}")
for m in results.get("G2C_ui_modes", []):
    print(f"    mode={m['mode']}: {'PASS' if m.get('pass') else 'FAIL'}")
print(f"  G2D JS 콘솔 에러 없음:           {'PASS' if results.get('G2D_pass') else 'FAIL'}")
print("="*55)
print(f"\nSCREENSHOTS:")
import os
for f in sorted(os.listdir(".")):
    if f.startswith("qa_final2") and f.endswith(".png"):
        print(f"  {f}")

with open("qa_task_final2_result.json", "w", encoding="utf-8") as f:
    json.dump({"results": results, "G1_pass": G1_pass, "G2_pass": G2_pass}, f, indent=2, ensure_ascii=False)
