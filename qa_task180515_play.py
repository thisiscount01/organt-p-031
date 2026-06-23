from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(args=['--no-sandbox','--disable-setuid-sandbox'])
    ctx = browser.new_context(ignore_https_errors=True, viewport={'width':1280,'height':900})
    page = ctx.new_page()
    errors = []
    page.on('pageerror', lambda e: errors.append(str(e)))

    # 퀴즈 선택 페이지 이동
    page.goto('http://localhost:3002/#/quiz', wait_until='networkidle', timeout=15000)
    page.wait_for_timeout(1500)
    page.screenshot(path='qa_180515_quiz_select.png', full_page=True)

    # 게임 시작! 버튼 클릭
    start_btn = page.query_selector('button:has-text("게임 시작")')
    if start_btn:
        print('Found start button — clicking')
        start_btn.click()
        page.wait_for_timeout(3000)
        page.screenshot(path='qa_180515_quiz_playing.png', full_page=True)
        url_after = page.url
        body_text = page.inner_text('body')[:500].replace('\n',' ')
        print(f'[AFTER START] url={url_after}')
        print(f'body={body_text}')
    else:
        print('ERROR: start button not found')
        buttons = page.query_selector_all('button')
        for b in buttons[:10]:
            print(' button:', b.inner_text()[:40])

    browser.close()
    print('JS errors:', len(errors))
    for e in errors: print(' ERR:', e)
