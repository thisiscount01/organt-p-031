#!/usr/bin/env python3
"""QA 전체 Goal 검증 스크립트"""
import urllib.request, urllib.error, json, time, sys

BASE = "http://localhost:3000"

def req(method, path, body=None, token=None):
    url = BASE + path
    data = json.dumps(body).encode() if body else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    r = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        resp = urllib.request.urlopen(r)
        body_bytes = resp.read()
        try:
            return resp.status, json.loads(body_bytes) if body_bytes.strip() else {}
        except Exception:
            return resp.status, {}
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read())
        except:
            return e.code, {}
    except Exception as e:
        return 0, {"error": str(e)}

results = {}
ts = str(int(time.time()))

# ─── Goal 1: 영화 300편+ ───
print("\n=== GOAL 1: 영화 데이터 ===")
status, data = req("GET", "/api/movies?limit=1")
total = data.get("total", 0)
first = data.get("results", [{}])[0]
poster = first.get("poster_path", "")
g1 = total >= 300 and bool(poster)
print(f"  총 영화 수={total} (>=300: {'OK' if total>=300 else 'FAIL'})")
print(f"  poster_path='{poster[:35]}' → CDN=https://image.tmdb.org/t/p/w500{poster}")
print(f"  [G1] {'PASS' if g1 else 'FAIL'}")
results["G1_movies_300plus"] = g1

# ─── Goal 3: AI 추천 ───
print("\n=== GOAL 3: AI 추천 (cosine sim) ===")
status, data = req("GET", "/api/movies/27205/recommend")
recs = data.get("recommendations", [])
g3 = len(recs) == 5 and all("score" in r and "title" in r for r in recs)
print(f"  추천 수={len(recs)} (need 5)")
for r in recs:
    print(f"    score={r.get('score',0):.3f} title={r.get('title')}")
print(f"  [G3] {'PASS' if g3 else 'FAIL'}")
results["G3_recommend_5"] = g3

# ─── Goal 6: JWT 인증 ───
print("\n=== GOAL 6: JWT 인증 ===")
s, reg = req("POST", "/api/auth/register", {"username":f"qa{ts}","email":f"qa{ts}@t.com","password":"pass123"})
TOKEN = reg.get("token","")
g6_reg = s == 201 and bool(TOKEN)
print(f"  register → status={s} token_ok={bool(TOKEN)}")

s, login = req("POST", "/api/auth/login", {"email":f"qa{ts}@t.com","password":"pass123"})
TOKEN = login.get("token", TOKEN)
g6_login = s == 200 and bool(TOKEN)
print(f"  login → status={s} token_ok={bool(TOKEN)}")

# 잘못된 비번
s, bad = req("POST", "/api/auth/login", {"email":f"qa{ts}@t.com","password":"wrong"})
g6_wrong = s == 401
print(f"  wrong password → status={s} (expect 401: {'OK' if g6_wrong else 'FAIL'})")

g6 = g6_reg and g6_login and g6_wrong
print(f"  [G6] {'PASS' if g6 else 'FAIL'}")
results["G6_jwt_auth"] = g6

# ─── Goal 2: 퀴즈 3종 ───
print("\n=== GOAL 2: 퀴즈 3종 + 타이머 ===")
modes = [("poster","poster"), ("director","director"), ("cast","cast")]
g2_ok = []
for mode, expected_type in modes:
    s, data = req("GET", f"/api/quiz/questions?mode={mode}&count=5")
    qs = data.get("questions", [])
    if qs:
        q0 = qs[0]
        ok = (len(qs) >= 3 and q0.get("type") == expected_type
              and len(q0.get("choices",[])) == 4
              and bool(q0.get("image"))
              and q0.get("timeLimit", 0) > 0
              and q0.get("correctId") is not None)
        g2_ok.append(ok)
        print(f"  {mode}: count={len(qs)} type={q0.get('type')} tl={q0.get('timeLimit')}s choices={len(q0.get('choices',[]))} img={bool(q0.get('image'))} → {'OK' if ok else 'FAIL'}")
    else:
        g2_ok.append(False)
        print(f"  {mode}: NO QUESTIONS → FAIL")

# game/scores POST (score/lives/timer)
s, score_resp = req("POST", "/api/game/scores", {"score":750,"mode":"poster","correct":7,"total":10,"time":45}, TOKEN)
g2_score = s == 201 and score_resp.get("entry",{}).get("score") == 750
print(f"  game/scores POST → status={s} entry_score={score_resp.get('entry',{}).get('score')} → {'OK' if g2_score else 'FAIL'}")

g2 = all(g2_ok) and g2_score
print(f"  [G2] {'PASS' if g2 else 'FAIL'}")
results["G2_quiz_3types"] = g2

# ─── Goal 5: Community CRUD + 5 URL ───
print("\n=== GOAL 5: Community CRUD + 랭킹 ===")

# Create
s, post = req("POST", "/api/community/posts",
              {"title":"QA Test","content":"내용","category":"review"}, TOKEN)
pid = post.get("id")
g5_create = s == 201 and bool(pid)
print(f"  CREATE → status={s} id={pid} → {'OK' if g5_create else 'FAIL'}")

# Read
s, read = req("GET", f"/api/community/posts/{pid}")
g5_read = s == 200 and read.get("id") == pid
print(f"  READ → status={s} title={read.get('title')} → {'OK' if g5_read else 'FAIL'}")

# Update
s, upd = req("PUT", f"/api/community/posts/{pid}",
             {"title":"수정제목","content":"수정내용"}, TOKEN)
g5_update = s == 200
print(f"  UPDATE → status={s} → {'OK' if g5_update else 'FAIL'}")

# Like
s, like = req("POST", f"/api/community/posts/{pid}/like", {}, TOKEN)
g5_like = s == 200 and like.get("likes",0) >= 1
print(f"  LIKE → status={s} likes={like.get('likes')} → {'OK' if g5_like else 'FAIL'}")

# Comment
s, cmt = req("POST", f"/api/community/posts/{pid}/comments", {"content":"댓글"}, TOKEN)
g5_comment = s == 201 and bool(cmt.get("id"))
print(f"  COMMENT → status={s} id={cmt.get('id')} → {'OK' if g5_comment else 'FAIL'}")

# Delete
s, _ = req("DELETE", f"/api/community/posts/{pid}", token=TOKEN)
g5_delete = s == 204
print(f"  DELETE → status={s} → {'OK' if g5_delete else 'FAIL'}")

# Leaderboard (랭킹 페이지)
s, lb = req("GET", "/api/leaderboard")
g5_lb = s == 200 and "leaderboard" in lb
print(f"  LEADERBOARD → status={s} entries={lb.get('total')} → {'OK' if g5_lb else 'FAIL'}")

g5 = all([g5_create, g5_read, g5_update, g5_like, g5_comment, g5_delete, g5_lb])
print(f"  [G5] {'PASS' if g5 else 'FAIL'}")
results["G5_community_crud"] = g5

# ─── Goal 7: RESTful 10개+ 엔드포인트 ───
print("\n=== GOAL 7: RESTful 엔드포인트 10개+ ===")
endpoints = [
    ("GET",    "/api/health",                    None, 200),
    ("GET",    "/api/movies",                    None, 200),
    ("GET",    "/api/movies/27205",              None, 200),
    ("GET",    "/api/movies/27205/recommend",    None, 200),
    ("GET",    "/api/genres",                    None, 200),
    ("GET",    "/api/quiz/questions?mode=poster",None, 200),
    ("GET",    "/api/quiz/poster",               None, 200),
    ("GET",    "/api/quiz/title",                None, 200),
    ("GET",    "/api/quiz/actor",                None, 200),
    ("GET",    "/api/leaderboard",               None, 200),
    ("GET",    "/api/game/scores",               None, 200),
    ("GET",    "/api/community/posts",           None, 200),
    ("POST",   "/api/auth/register", {"username":f"ep{ts}x","email":f"ep{ts}x@t.com","password":"pass123"}, 201),
    ("POST",   "/api/auth/login",    {"email":f"ep{ts}x@t.com","password":"pass123"}, 200),
    ("GET",    "/api/movies/999999",             None, 404),
]
ok_count = 0
for method, path, body, expected in endpoints:
    s, _ = req(method, path, body)
    ok = s == expected
    if ok: ok_count += 1
    print(f"  {'OK' if ok else 'FAIL'} {method} {path} → {s} (expect {expected})")
g7 = ok_count >= 10
print(f"  합계 {ok_count}/{len(endpoints)} 통과")
print(f"  [G7] {'PASS' if g7 else 'FAIL'}")
results["G7_endpoints_10plus"] = g7

# ─── 최종 요약 ───
print("\n" + "="*60)
print("최종 QA 요약")
print("="*60)
goals = {
    "G1 영화300편+/포스터":      results.get("G1_movies_300plus"),
    "G2 퀴즈3종+점수시스템":     results.get("G2_quiz_3types"),
    "G3 AI추천5편":              results.get("G3_recommend_5"),
    "G5 커뮤니티CRUD+랭킹":      results.get("G5_community_crud"),
    "G6 JWT인증":                results.get("G6_jwt_auth"),
    "G7 RESTful 10개+":          results.get("G7_endpoints_10plus"),
}
for name, ok in goals.items():
    print(f"  {'PASS' if ok else 'FAIL'} {name}")
all_pass = all(v for v in goals.values())
print(f"\n전체: {'ALL PASS' if all_pass else 'SOME FAIL'}")
