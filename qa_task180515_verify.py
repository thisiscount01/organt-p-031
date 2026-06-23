from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(args=['--no-sandbox','--disable-setuid-sandbox'])
    ctx = browser.new_context(ignore_https_errors=True)
    page = ctx.new_page()
    errors = []
    page.on('pageerror', lambda e: errors.append(str(e)))

    # 홈
    page.goto('http://localhost:3002/', wait_until='networkidle', timeout=15000)
    page.screenshot(path='qa_verify_home.png', full_page=True)
    title_home = page.title()
    print(f'[HOME] title={title_home}  url={page.url}')

    # 퀴즈 선택 페이지
    page.goto('http://localhost:3002/#/quiz', wait_until='networkidle', timeout=15000)
    page.wait_for_timeout(1500)
    page.screenshot(path='qa_verify_quiz_select.png', full_page=True)
    title_quiz = page.title()
    print(f'[QUIZ SELECT] title={title_quiz}  url={page.url}')

    # 퀴즈 게임 poster 모드
    page.goto('http://localhost:3002/#/quiz/play?mode=poster', wait_until='networkidle', timeout=15000)
    page.wait_for_timeout(2500)
    page.screenshot(path='qa_verify_quiz_poster.png', full_page=True)
    body_text = page.inner_text('body')[:400].replace('\n',' ')
    print(f'[QUIZ POSTER PLAY] url={page.url}  body={body_text}')

    browser.close()

    print('JS errors total:', len(errors))
    for e in errors:
        print('  ERR:', e)
