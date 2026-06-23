"""
Task 180515-1 QA Detail Inspection
Checks detail/community/leaderboard/auth pages in depth
"""
from playwright.sync_api import sync_playwright

BASE  = "https://organt-p-031.onrender.com"
SHOTS = "/home/user/organt_workspace/p-031-ai-기반-추천-웹게임"

with sync_playwright() as p:
    browser = p.chromium.launch(args=["--ignore-certificate-errors","--no-sandbox"])
    ctx  = browser.new_context(viewport={"width":1280,"height":900}, ignore_https_errors=True)
    page = ctx.new_page()

    # Detail page
    page.goto(f"{BASE}/#/movies/399566", wait_until="networkidle", timeout=20000)
    page.wait_for_timeout(3000)

    iframes = page.query_selector_all("iframe")
    print(f"[DETAIL IFRAMES] count={len(iframes)}")
    for i, f in enumerate(iframes[:5]):
        print(f"  iframe[{i}] src={f.get_attribute('src')}")

    body_text = page.inner_text("body")
    yt_text = "youtube" in body_text.lower() or "youtu.be" in body_text.lower() or "trailer" in body_text.lower()
    print(f"  youtube/trailer text in body: {yt_text}")

    sections = page.query_selector_all("section, .section, [class*='trailer'], [class*='video'], [class*='recommend'], [class*='similar']")
    print(f"  sections/trailer/rec: {len(sections)}")
    for s in sections[:6]:
        cls = s.get_attribute("class") or s.tag_name
        print(f"    {cls[:60]}")

    page.screenshot(path=f"{SHOTS}/qa_180515_detail_v2.png")

    # Community
    page.goto(f"{BASE}/#/community", wait_until="networkidle", timeout=20000)
    page.wait_for_timeout(2500)

    all_with_class = page.query_selector_all("*[class]")
    community_classes = set()
    for el in all_with_class:
        c = (el.get_attribute("class") or "")
        if any(k in c for k in ["post","card","article","community","thread","board"]):
            community_classes.add(c[:50])
    print(f"[COMMUNITY CLASSES] {list(community_classes)[:10]}")

    links_btns = page.query_selector_all("a, button")
    print(f"[COMMUNITY] links/buttons={len(links_btns)}")
    page.screenshot(path=f"{SHOTS}/qa_180515_community_v2.png")

    # Leaderboard
    page.goto(f"{BASE}/#/leaderboard", wait_until="networkidle", timeout=20000)
    page.wait_for_timeout(2000)

    tables = page.query_selector_all("table, .table")
    trs = page.query_selector_all("tr")
    divs_rank = page.query_selector_all("[class*='rank'], [class*='score'], [class*='leader']")
    print(f"[LEADERBOARD] tables={len(tables)} | tr={len(trs)} | rank divs={len(divs_rank)}")
    page.screenshot(path=f"{SHOTS}/qa_180515_leaderboard_v2.png")

    # Auth
    page.goto(f"{BASE}/#/login", wait_until="networkidle", timeout=20000)
    page.wait_for_timeout(1500)
    all_inputs = page.query_selector_all("input, form")
    btns = page.query_selector_all("button")
    print(f"[AUTH] inputs+forms={len(all_inputs)} | buttons={len(btns)}")
    body_auth = page.inner_text("body")
    print(f"  body[:200]: {body_auth[:200]}")
    page.screenshot(path=f"{SHOTS}/qa_180515_auth_v2.png")

    ctx.close()
    browser.close()

print("[DONE]")
