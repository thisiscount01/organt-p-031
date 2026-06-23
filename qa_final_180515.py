"""
QA Final Cross-Validation — Task 180515-1
Goals: G1 (movies 300+, poster CDN), G2 (quiz 3 types), community alias
"""
import subprocess, time, json, urllib.request, urllib.error, sys, os
import struct, zlib, re

BASE = 'http://localhost:3000'
WS   = '/home/user/organt_workspace/p-031-ai-기반-추천-웹게임'
RESULTS = {}

# ── Minimal valid 1×1 RGB PNG ────────────────────────────────────────────────
def make_1x1_png():
    def chunk(t, d):
        c = t + d
        return struct.pack('>I', len(d)) + c + struct.pack('>I', zlib.crc32(c) & 0xffffffff)
    sig  = b'\x89PNG\r\n\x1a\n'
    IHDR = chunk(b'IHDR', struct.pack('>IIBBBBB', 1, 1, 8, 2, 0, 0, 0))
    IDAT = chunk(b'IDAT', zlib.compress(b'\x00\xff\x8c\x00'))  # filter=0, R, G, B
    IEND = chunk(b'IEND', b'')
    return sig + IHDR + IDAT + IEND

PNG_STUB = make_1x1_png()

# ── helpers ──────────────────────────────────────────────────────────────────
def api_get(path):
    try:
        req = urllib.request.Request(f'{BASE}{path}', headers={'Accept':'application/json'})
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, {}
    except Exception as ex:
        return 0, {'error': str(ex)}

def api_post(path, body=None, token=None):
    data = json.dumps(body or {}).encode()
    headers = {'Content-Type':'application/json', 'Accept':'application/json'}
    if token:
        headers['Authorization'] = f'Bearer {token}'
    try:
        req = urllib.request.Request(f'{BASE}{path}', data=data, headers=headers, method='POST')
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read())
        except:
            return e.code, {}
    except Exception as ex:
        return 0, {'error': str(ex)}

def check(name, cond, detail=''):
    status = 'PASS' if cond else 'FAIL'
    RESULTS[name] = status
    icon = '✅' if cond else '❌'
    print(f'  {icon} [{status}] {name}' + (f' — {detail}' if detail else ''))

# ── Start server ──────────────────────────────────────────────────────────────
print('\n[Phase 0] Server boot')
srv = subprocess.Popen(
    ['node', 'server.js'],
    cwd=WS,
    stdout=subprocess.PIPE, stderr=subprocess.PIPE
)
for i in range(14):
    time.sleep(0.5)
    try:
        urllib.request.urlopen(f'{BASE}/api/health', timeout=2)
        print(f'  Server ready after {(i+1)*0.5:.1f}s')
        break
    except:
        pass
else:
    out, err = srv.communicate(timeout=3)
    print('  FATAL: server not up', err.decode()[:300])
    sys.exit(1)

# ── Phase 1: /api/movies — total ≥ 300 ──────────────────────────────────────
print('\n[Phase 1] G1 — Movies fixture & poster CDN')
status, data = api_get('/api/movies?limit=1')
check('GET /api/movies → 200', status == 200, f'HTTP {status}')
total = data.get('total', 0)
check('total ≥ 300', total >= 300, f'total={total}')
if data.get('results'):
    poster = data['results'][0].get('poster_path', '')
    check('poster_path not empty', bool(poster), repr(poster))
else:
    check('poster_path not empty', False, 'no results')

# Verify quiz poster URL construction
status2, data2 = api_get('/api/quiz/poster?count=1')
poster_url = ''
if data2.get('questions'):
    poster_url = data2['questions'][0].get('image', '')
check('quiz poster URL starts with image.tmdb.org',
      poster_url.startswith('https://image.tmdb.org/t/p/'), repr(poster_url))

# ── Phase 2: Quiz alias endpoints ────────────────────────────────────────────
print('\n[Phase 2] G2 — Quiz alias 3 types')
for alias, label in [
    ('/api/quiz/poster?count=1', 'poster'),
    ('/api/quiz/title?count=1',  'title'),
    ('/api/quiz/actor?count=1',  'actor'),
]:
    s, d = api_get(alias)
    qs = d.get('questions', [])
    check(f'GET {alias} → 200', s == 200, f'HTTP {s}')
    check(f'{label} questions non-empty', len(qs) > 0, f'count={len(qs)}')

# ── Phase 3: Community alias with auth ───────────────────────────────────────
print('\n[Phase 3] Community alias — like & comment')
ts = int(time.time())
reg_s, reg_d = api_post('/api/auth/register', {
    'username': f'qabot{ts}', 'email': f'qa{ts}@test.com', 'password': 'testpass123'
})
token = reg_d.get('token', '')
check('Register test user → 201', reg_s == 201, f'HTTP {reg_s}')
check('Token issued', bool(token), repr(token[:30]) if token else 'no token')

post_s, post_d = api_post('/api/community/posts', {
    'title': 'QA Test Post', 'content': 'Automated QA test'
}, token=token)
post_id = post_d.get('id')
check('Create post → 201', post_s == 201, f'HTTP {post_s}, id={post_id}')

if post_id:
    like_s, like_d = api_post(f'/api/posts/{post_id}/like', token=token)
    check('POST /api/posts/:id/like → 200', like_s == 200, f'HTTP {like_s}, body={like_d}')

    cmt_s, cmt_d = api_post(f'/api/posts/{post_id}/comments', {'content': 'QA comment'}, token=token)
    check('POST /api/posts/:id/comments → 201', cmt_s == 201, f'HTTP {cmt_s}')
else:
    check('POST /api/posts/:id/like → 200', False, 'skipped: no post_id')
    check('POST /api/posts/:id/comments → 201', False, 'skipped: no post_id')

# ── Phase 4: Playwright — screenshots ────────────────────────────────────────
print('\n[Phase 4] Playwright screenshots')
try:
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        browser = pw.chromium.launch(args=['--no-sandbox', '--disable-setuid-sandbox'])
        ctx     = browser.new_context(viewport={'width':1280, 'height':900})

        # Intercept TMDB CDN with a valid 1×1 PNG so @error doesn't fire
        tmdb_pattern = re.compile(r'https://image\.tmdb\.org/.*')
        tmdb_requests = []

        def handle_tmdb(route):
            tmdb_requests.append(route.request.url)
            route.fulfill(
                status=200,
                body=PNG_STUB,
                headers={'Content-Type': 'image/png',
                         'Content-Length': str(len(PNG_STUB))}
            )

        ctx.route(tmdb_pattern, handle_tmdb)
        page = ctx.new_page()

        # ── G1: Home — poster img load ────────────────────────────────────
        page.goto(f'{BASE}/#/', wait_until='domcontentloaded')
        page.wait_for_timeout(4500)
        page.screenshot(path=f'{WS}/qa_final_180515_home.png')

        # After valid PNG stub, @error should NOT fire → img src stays tmdb
        poster_img_count = page.locator('img[src*="tmdb"]').count()
        check('Playwright: tmdb.org requests intercepted (≥10)',
              len(tmdb_requests) >= 10, f'requests={len(tmdb_requests)}')
        check('Playwright: poster imgs visible on home (CDN-stubbed)',
              poster_img_count > 0,
              f'img[src*=tmdb]={poster_img_count}, intercepted={len(tmdb_requests)}')

        # ── G2: Quiz select → game ────────────────────────────────────────
        page.goto(f'{BASE}/#/quiz', wait_until='domcontentloaded')
        page.wait_for_timeout(2000)
        page.screenshot(path=f'{WS}/qa_final_180515_quiz_select.png')

        select_visible = page.locator('.quiz-select-screen').count() > 0
        check('Playwright: quiz select screen renders', select_visible,
              f'count={page.locator(".quiz-select-screen").count()}')

        if select_visible:
            btn = page.locator('.btn-start')
            if btn.count() > 0:
                btn.first.click()
                page.wait_for_timeout(3000)
            page.screenshot(path=f'{WS}/qa_final_180515_quiz_game.png')
            game_visible = page.locator('.quiz-game-screen').count() > 0
            check('Playwright: quiz game screen renders after start', game_visible,
                  f'count={page.locator(".quiz-game-screen").count()}')
        else:
            check('Playwright: quiz game screen renders after start', False, 'quiz-select not found')

        browser.close()
    check('Playwright session completed', True)
except Exception as ex:
    check('Playwright session completed', False, str(ex)[:200])

# ── Summary ───────────────────────────────────────────────────────────────────
srv.terminate()
print('\n══════════════ SUMMARY ══════════════')
passed = sum(1 for v in RESULTS.values() if v == 'PASS')
total_checks = len(RESULTS)
for k, v in RESULTS.items():
    icon = '✅' if v == 'PASS' else '❌'
    print(f'  {icon} {v:4} {k}')
print(f'\n  TOTAL: {passed}/{total_checks} PASS')
print('═════════════════════════════════════')
sys.exit(0 if passed == total_checks else 1)
