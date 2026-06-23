"""
G4 최종: '상세보기' 버튼 → 이동 경로 + YouTube embed 존재 여부
"""
from playwright.sync_api import sync_playwright

BASE = "https://organt-p-031.onrender.com"
MOVIE_ID = 399566

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
    ctx = browser.new_context(ignore_https_errors=True, viewport={"width":1280,"height":800})
    page = ctx.new_page()

    page.goto(f"{BASE}/#/detail/{MOVIE_ID}", wait_until="domcontentloaded", timeout=30000)
    page.wait_for_timeout(4000)

    # 상세보기 버튼/링크
    all_links = page.eval_on_selector_all(
        "a, button",
        "els => els.map(e => ({tag:e.tagName, href:e.href||'', text:e.innerText.trim().slice(0,30), cls:e.className.slice(0,40)}))"
    )
    print("전체 a/button 목록:")
    for l in all_links:
        print(f"  {l['tag']} text='{l['text']}' href='{l['href']}' class='{l['cls']}'")

    # '상세보기' 클릭
    detail_btns = [l for l in all_links if "상세" in l["text"]]
    print(f"\n'상세보기' 버튼/링크: {len(detail_btns)}개")
    for l in detail_btns[:3]:
        print(f"  href='{l['href']}'")

    if detail_btns:
        first_detail_href = detail_btns[0]["href"]
        if first_detail_href:
            print(f"\n{first_detail_href} 이동 →")
            page.goto(first_detail_href, wait_until="domcontentloaded", timeout=20000)
            page.wait_for_timeout(3000)
            print(f"  URL: {page.url}")
            iframes = page.query_selector_all("iframe")
            yt_iframes = [f for f in iframes if "youtube" in (f.get_attribute("src") or "")]
            print(f"  iframe 수: {len(iframes)}, youtube iframe: {len(yt_iframes)}")
            html2 = page.content()
            print(f"  HTML youtube 포함: {'youtube' in html2.lower()}")
            page.screenshot(path="qa_diag5_from_detail_btn.png")
        else:
            # 버튼이면 클릭
            print("버튼 클릭 시도")
            btn_el = page.query_selector("button:has-text('상세보기')")
            if btn_el:
                btn_el.click()
                page.wait_for_timeout(2000)
                print(f"  URL after click: {page.url}")
                iframes = page.query_selector_all("iframe")
                yt_iframes = [f for f in iframes if "youtube" in (f.get_attribute("src") or "")]
                print(f"  iframe: {len(iframes)}, yt: {len(yt_iframes)}")

    # 마지막: HTML 내 youtube/embed 문자열 검색
    page.goto(f"{BASE}/#/detail/{MOVIE_ID}", wait_until="domcontentloaded", timeout=30000)
    page.wait_for_timeout(4000)
    html = page.content()
    for keyword in ["youtube", "youtu.be", "embed", "iframe", "trailer", "trailer_yt", "odM92ap8"]:
        idx = html.lower().find(keyword.lower())
        if idx >= 0:
            print(f"HTML 내 '{keyword}' at {idx}: ...{html[max(0,idx-30):idx+80]}...")
        else:
            print(f"HTML 내 '{keyword}': 없음")

    # 퀴즈 도전이 어디로 가는지
    print("\n'퀴즈 도전' href:")
    quiz_links = [l for l in all_links if "퀴즈" in l["text"]]
    for l in quiz_links[:3]:
        print(f"  href='{l['href']}'")

    browser.close()
print("Done.")
