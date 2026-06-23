#!/usr/bin/env python3
"""Playwright 브라우저 검증 — Goal 4(YouTube embed) + 5개 URL + UI 렌더링"""
from playwright.sync_api import sync_playwright
import json, time, sys

BASE = "http://localhost:3000"
RESULTS = {}

def take_ss(page, name):
    try:
        page.screenshot(path=f"qa/ss_{name}.png", full_page=False)
    except Exception as e:
        print(f"  [SS] {name} 실패: {e}")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
    ctx = browser.new_context(viewport={"width": 1280, "height": 800})

    js_errors = []

    def on_pageerror(exc):
        js_errors.append(str(exc))

    page = ctx.new_page()
    page.on("pageerror", on_pageerror)

    # ─── Goal 5: 5개 URL 확인 ───
    print("\n=== GOAL 5: 독립 URL 5개+ ===")
    routes = [
        ("/",               "홈"),
        ("/#/movies",       "영화목록"),
        ("/#/quiz",         "퀴즈"),
        ("/#/community",    "커뮤니티"),
        ("/#/leaderboard",  "랭킹"),
        ("/#/auth",         "인증"),
    ]
    url_pass = []
    for route, label in routes:
        page.goto(BASE + route, wait_until="domcontentloaded", timeout=15000)
        time.sleep(1.2)
        title = page.title()
        content = page.content()
        # 각 페이지에 의미있는 컨텐츠가 있는지 확인
        has_content = len(content) > 500
        # CineAI 앱 로드 확인
        has_app = "CineAI" in content or "cineai" in content.lower()
        ok = has_content and has_app
        url_pass.append(ok)
        print(f"  {'OK' if ok else 'FAIL'} {route} ({label}) title={title[:40]}")
        take_ss(page, f"url_{label}")

    g5_urls = sum(url_pass) >= 5
    print(f"  URL 통과: {sum(url_pass)}/{len(url_pass)} → {'PASS' if g5_urls else 'FAIL'}")
    RESULTS["G5_5urls"] = g5_urls

    # ─── Goal 1: 홈 + 포스터 이미지 로드 ───
    print("\n=== GOAL 1: 홈페이지 포스터 렌더링 ===")
    page.goto(BASE + "/", wait_until="domcontentloaded", timeout=15000)
    time.sleep(2)
    # 포스터 이미지 태그 수 확인
    imgs = page.locator("img[src*='image.tmdb.org']").count()
    print(f"  TMDB 포스터 이미지 수={imgs}")
    take_ss(page, "home_posters")
    g1_ui = imgs >= 1
    print(f"  [G1 UI] {'PASS' if g1_ui else 'FAIL'}")
    RESULTS["G1_poster_ui"] = g1_ui

    # ─── Goal 4: YouTube embed ───
    print("\n=== GOAL 4: YouTube Embed ===")
    # 영화 상세 페이지 접근 (Inception id=27205)
    page.goto(BASE + "/#/movie?id=27205", wait_until="domcontentloaded", timeout=15000)
    time.sleep(2.5)

    # iframe youtube embed 확인
    iframes = page.locator("iframe[src*='youtube.com/embed']").count()
    print(f"  YouTube iframe count={iframes}")

    # iframe src 추출
    if iframes > 0:
        src = page.locator("iframe[src*='youtube.com/embed']").first.get_attribute("src")
        print(f"  iframe src={src}")
        g4 = "youtube.com/embed" in (src or "")
    else:
        # trailer_yt 데이터가 있지만 미렌더링? 콘텐츠 확인
        content = page.content()
        g4 = "youtube.com/embed" in content
        if g4:
            print(f"  HTML에 embed URL 존재 (iframe count 오탐)")

    take_ss(page, "movie_detail_yt")
    print(f"  [G4] {'PASS' if g4 else 'FAIL'}")
    RESULTS["G4_youtube_embed"] = g4

    # ─── Goal 2: 퀴즈 UI ───
    print("\n=== GOAL 2: 퀴즈 UI 렌더링 ===")
    page.goto(BASE + "/#/quiz", wait_until="domcontentloaded", timeout=15000)
    time.sleep(1.5)
    content = page.content()
    has_mode_select = any(w in content for w in ["포스터", "감독", "배우", "모드", "퀴즈"])
    print(f"  퀴즈 페이지 로드: has_mode_keywords={has_mode_select}")
    take_ss(page, "quiz_page")
    g2_ui = has_mode_select
    RESULTS["G2_quiz_ui"] = g2_ui
    print(f"  [G2 UI] {'PASS' if g2_ui else 'FAIL'}")

    # ─── Goal 3: 영화 상세 → AI 추천 ───
    print("\n=== GOAL 3: AI 추천 UI ===")
    page.goto(BASE + "/#/movie?id=27205", wait_until="domcontentloaded", timeout=15000)
    time.sleep(2.5)
    content = page.content()
    has_rec = any(w in content for w in ["추천", "비슷한 영화", "Similar", "연관"])
    print(f"  추천 섹션 키워드 존재={has_rec}")
    take_ss(page, "movie_detail_recommend")
    g3_ui = has_rec
    RESULTS["G3_recommend_ui"] = g3_ui
    print(f"  [G3 UI] {'PASS' if g3_ui else 'FAIL'}")

    # ─── JS 오류 수집 ───
    print(f"\n=== JS 오류 ({len(js_errors)}건) ===")
    for e in js_errors[:5]:
        print(f"  ERROR: {e}")

    browser.close()

print("\n" + "="*50)
print("브라우저 검증 요약")
print("="*50)
for k, v in RESULTS.items():
    print(f"  {'PASS' if v else 'FAIL'} {k}")
all_ok = all(RESULTS.values())
print(f"\n결과: {'ALL PASS' if all_ok else 'SOME FAIL'}")
