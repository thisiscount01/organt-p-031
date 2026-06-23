import json
from playwright.sync_api import sync_playwright

results = {}

with sync_playwright() as p:
    browser = p.chromium.launch(args=['--no-sandbox','--disable-setuid-sandbox'])
    page = browser.new_page()

    js_errors = []
    page.on('pageerror', lambda e: js_errors.append(str(e)))

    # CRIT-7: home rendering & JS errors
    page.goto('http://localhost:3000/', wait_until='domcontentloaded', timeout=15000)
    page.wait_for_timeout(2500)
    title = page.title()
    body_text = page.inner_text('body')
    results['crit7_title'] = title
    results['crit7_js_errors'] = js_errors[:]
    results['crit7_body_len'] = len(body_text)
    results['crit7_body_snippet'] = body_text[:300]
    page.screenshot(path='qa_final_home.png')

    # CRIT-8: quiz selection — 3 mode buttons
    page.goto('http://localhost:3000/#/quiz', wait_until='domcontentloaded', timeout=15000)
    page.wait_for_timeout(2500)
    page.screenshot(path='qa_final_quiz_select.png')
    all_btns = page.query_selector_all('button, .btn')
    btn_texts = [b.inner_text().strip() for b in all_btns if b.inner_text().strip()]
    quiz_text = page.inner_text('body')
    # check for mode keywords
    has_poster = any(k in quiz_text for k in ['포스터','포스터 맞추기','Poster','poster'])
    has_title  = any(k in quiz_text for k in ['제목','줄거리','Title','title'])
    has_actor  = any(k in quiz_text for k in ['배우','출연','Actor','actor','캐스트'])
    results['crit8_buttons'] = btn_texts[:20]
    results['crit8_has_poster_mode'] = has_poster
    results['crit8_has_title_mode']  = has_title
    results['crit8_has_actor_mode']  = has_actor
    results['crit8_quiz_snippet']    = quiz_text[:400]

    # CRIT-9: /daily page — date badge & question card
    page.goto('http://localhost:3000/#/daily', wait_until='domcontentloaded', timeout=15000)
    page.wait_for_timeout(2500)
    page.screenshot(path='qa_final_daily.png')
    daily_text = page.inner_text('body')
    results['crit9_has_date'] = '2026' in daily_text or '06-23' in daily_text or '6월' in daily_text
    results['crit9_has_question'] = any(x in daily_text for x in ['문제', '퀴즈', '?', 'Q1', 'Q.1', '이 영화', '감독'])
    results['crit9_snippet'] = daily_text[:400]

    browser.close()

print(json.dumps(results, ensure_ascii=False, indent=2))
