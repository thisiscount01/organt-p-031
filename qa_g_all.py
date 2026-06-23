import urllib.request, urllib.error, json, sys

BASE = "http://localhost:3000"

def fetch(path, method="GET", data=None, headers=None):
    url = BASE + path
    req = urllib.request.Request(url, method=method)
    if headers:
        for k,v in headers.items():
            req.add_header(k, v)
    if data:
        req.data = json.dumps(data).encode()
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            body = r.read()
            try:
                return r.status, json.loads(body)
            except Exception:
                return r.status, {}
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read())
        except Exception:
            return e.code, {}
    except Exception as ex:
        return 0, {"error": str(ex)}

results = {}

# ── G1: 영화 500편 + 포스터 CDN ──────────────────────────────
print("\n=== G1: Movies fixture + poster CDN ===")
status, data = fetch("/api/movies?limit=1")
total = data.get("total", 0)
results_list = data.get("results", [])
movie = results_list[0] if results_list else {}
poster = movie.get("poster_path", "")
cdn_url = f"https://image.tmdb.org/t/p/w500{poster}"
print(f"  API status: {status}, total: {total}")
print(f"  First poster_path: {poster}")
print(f"  CDN URL: {cdn_url}")
try:
    cdn_req = urllib.request.Request(cdn_url, headers={"User-Agent":"Mozilla/5.0"})
    with urllib.request.urlopen(cdn_req, timeout=8) as r:
        cdn_status = r.status
except urllib.error.HTTPError as e:
    cdn_status = e.code
except Exception as ex:
    cdn_status = f"ERR:{ex}"
print(f"  CDN HTTP: {cdn_status}")
g1 = "PASS" if total >= 500 and cdn_status == 200 else "FAIL"
print(f"  G1: {g1}")
results["G1"] = g1

# ── G2: 퀴즈 3종 ─────────────────────────────────────────────
print("\n=== G2: Quiz 3 endpoints ===")
g2_ok = True
for mode in ["poster", "director", "cast"]:
    s, d = fetch(f"/api/quiz/{mode}")
    qs = d.get("questions", [])
    tl = d.get("timeLimit")
    ok = s == 200 and len(qs) >= 10 and isinstance(tl, (int, float))
    print(f"  /api/quiz/{mode}: HTTP {s}, questions={len(qs)}, timeLimit={tl} → {'OK' if ok else 'FAIL'}")
    if not ok:
        g2_ok = False
g2 = "PASS" if g2_ok else "FAIL"
print(f"  G2: {g2}")
results["G2"] = g2

# ── G3: recommendations 5편 ───────────────────────────────────
print("\n=== G3: AI recommendations ===")
movie_id = movie.get("id")
s, detail = fetch(f"/api/movies/{movie_id}")
print(f"  /api/movies/{movie_id} HTTP: {s}")
s2, rec_data = fetch(f"/api/movies/{movie_id}/recommendations")
recs = rec_data if isinstance(rec_data, list) else rec_data.get("recommendations") or rec_data.get("results") or []
print(f"  recommendations count: {len(recs)}")
for r in recs[:3]:
    print(f"    - {r.get('title')} score={r.get('score')}")
has_score = all("score" in r for r in recs[:5])
g3 = "PASS" if len(recs) >= 5 and has_score else "FAIL"
print(f"  G3: {g3}")
results["G3"] = g3

# ── G4: trailer_yt / embed URL ────────────────────────────────
print("\n=== G4: trailer_yt YouTube embed ===")
trailer_yt = detail.get("trailer_yt")
print(f"  trailer_yt on detail: {trailer_yt!r}")
if trailer_yt:
    embed_url = f"https://www.youtube.com/embed/{trailer_yt}"
    print(f"  embed URL: {embed_url}")
    g4 = "PASS"
else:
    # fixture에서 직접 확인
    import os
    fx_path = os.path.join(os.path.dirname(__file__), "public", "data", "movies.json")
    with open(fx_path) as f:
        fx = json.load(f)
    has_yt = sum(1 for m in fx if m.get("trailer_yt"))
    print(f"  Fixture trailer_yt populated: {has_yt}/{len(fx)}")
    # API가 노출 안 하더라도 fixture에는 있을 수 있음 — API 응답 확인
    g4 = "PASS" if has_yt == len(fx) else "FAIL"
    if g4 == "FAIL":
        print("  WARN: fixture has None trailer_yt entries")
print(f"  G4: {g4}")
results["G4"] = g4

# ── G5: 독립 URL 5개+ ─────────────────────────────────────────
print("\n=== G5: SPA routes (200 responses) ===")
pages = ["/", "/movies", f"/movies/{movie_id}", "/quiz", "/leaderboard", "/community"]
g5_ok = True
for pg in pages:
    s, _ = fetch(pg)
    ok = s == 200
    print(f"  {pg}: HTTP {s} → {'OK' if ok else 'FAIL'}")
    if not ok:
        g5_ok = False
g5 = "PASS" if g5_ok else "FAIL"
print(f"  G5: {g5}")
results["G5"] = g5

# ── G6: JWT 인증 ──────────────────────────────────────────────
print("\n=== G6: JWT auth ===")
import time
uid = f"qatest{int(time.time())}"
s_reg, reg = fetch("/api/auth/register", "POST", {"username": uid, "email": f"{uid}@qa.test", "password": "Qa12345!"})
token_reg = reg.get("token")
print(f"  register: HTTP {s_reg}, token={'yes' if token_reg else 'no'}")
s_log, log_data = fetch("/api/auth/login", "POST", {"email": f"{uid}@qa.test", "password": "Qa12345!"})
token_log = log_data.get("token")
print(f"  login: HTTP {s_log}, token={'yes' if token_log else 'no'}")
g6 = "PASS" if token_reg and token_log else "FAIL"
print(f"  G6: {g6}")
results["G6"] = g6

# ── G7: RESTful 엔드포인트 10개+ ─────────────────────────────
print("\n=== G7: RESTful endpoints ===")
import re, os
srv_path = os.path.join(os.path.dirname(__file__), "server.js")
with open(srv_path) as f:
    src = f.read()
routes = re.findall(r"app\.(get|post|put|delete|patch)\s*\(\s*['\"]([^'\"]+)['\"]", src)
print(f"  Total routes found: {len(routes)}")
unique_paths = set((m, p) for m, p in routes)
for m, p in sorted(unique_paths, key=lambda x: x[1]):
    print(f"    {m.upper():6} {p}")
g7 = "PASS" if len(unique_paths) >= 10 else "FAIL"
print(f"  G7: {g7} ({len(unique_paths)} unique routes)")
results["G7"] = g7

# ── G8: Render URL ────────────────────────────────────────────
print("\n=== G8: Render deployment ===")
ry_path = os.path.join(os.path.dirname(__file__), "render.yaml")
render_url = None
if os.path.exists(ry_path):
    with open(ry_path) as f:
        content = f.read()
    print(f"  render.yaml exists")
    m = re.search(r"https://[a-zA-Z0-9._/-]+\.onrender\.com", content)
    if m:
        render_url = m.group(0)
if not render_url:
    # 이전 QA 보고에서 찾기
    for fname in ["qa_final_task180515_result.json", "qa_report.json"]:
        fp = os.path.join(os.path.dirname(__file__), fname)
        if os.path.exists(fp):
            with open(fp) as f:
                try:
                    rep = json.load(f)
                    url_candidate = rep.get("render_url") or rep.get("liveUrl") or rep.get("url")
                    if url_candidate:
                        render_url = url_candidate
                except:
                    pass
print(f"  Render URL found: {render_url!r}")
if render_url:
    try:
        rr = urllib.request.Request(render_url, headers={"User-Agent":"Mozilla/5.0"})
        with urllib.request.urlopen(rr, timeout=15) as rr2:
            render_status = rr2.status
    except urllib.error.HTTPError as e:
        render_status = e.code
    except Exception as ex:
        render_status = f"ERR:{ex}"
    print(f"  Render HTTP: {render_status}")
    g8 = "PASS" if render_status == 200 else "FAIL"
else:
    g8 = "FAIL (URL not found)"
print(f"  G8: {g8}")
results["G8"] = g8

# ── 종합 ──────────────────────────────────────────────────────
print("\n" + "="*50)
print("FINAL RESULTS:")
all_pass = True
for k, v in results.items():
    print(f"  {k}: {v}")
    if v != "PASS":
        all_pass = False
if all_pass:
    print("\n종합: DEPLOY_OK")
else:
    fails = [k for k, v in results.items() if v != "PASS"]
    print(f"\n종합: FAIL 목록: {fails}")
