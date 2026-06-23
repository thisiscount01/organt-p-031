"""GitHub REST API를 통해 변경 파일을 main 브랜치에 푸시 → Render 자동 배포 트리거."""
import base64, json, urllib.request, urllib.error, os, sys

GH_PAT  = os.environ.get('GH_PAT', '')
GH_USER = os.environ.get('GH_USER', 'thisiscount01')
REPO    = f"{GH_USER}/organt-p-031"
BASE    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def api(path, method='GET', payload=None):
    req = urllib.request.Request(
        f"https://api.github.com{path}",
        data=json.dumps(payload).encode() if payload else None,
        method=method
    )
    req.add_header("Authorization", f"Bearer {GH_PAT}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("User-Agent", "organt-deploy/1.0")
    if payload:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b'{}')

def get_sha(path):
    status, d = api(f"/repos/{REPO}/contents/{path}")
    if status == 200:
        return d.get('sha')
    return None

def push_file(repo_path, local_path, msg):
    sha = get_sha(repo_path)
    with open(local_path, 'rb') as f:
        content = base64.b64encode(f.read()).decode()
    payload = {"message": msg, "content": content}
    if sha:
        payload["sha"] = sha
    status, d = api(f"/repos/{REPO}/contents/{repo_path}", 'PUT', payload)
    if status in (200, 201):
        new_sha = d.get('content', {}).get('sha', '?')[:8]
        print(f"  ✅ {repo_path}: {new_sha}")
        return True
    else:
        print(f"  ❌ {repo_path}: HTTP {status} — {d.get('message','')}")
        return False

FILES = [
    ("server.js",   os.path.join(BASE, "server.js"),   "feat: daily/achievements/user-stats/view/personalized endpoints"),
    ("render.yaml", os.path.join(BASE, "render.yaml"),  "fix: single web service render.yaml"),
]

print(f"Pushing {len(FILES)} files to github.com/{REPO} …")
ok = all(push_file(rp, lp, msg) for rp, lp, msg in FILES)
print("Done:", "ALL OK" if ok else "SOME FAILED")
sys.exit(0 if ok else 1)
