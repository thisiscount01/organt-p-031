"""
TMDB 영화 데이터 수집 파이프라인
- genres.json / movies.json 생성
- idempotent: 같은 날 두 번 실행해도 결과 동일
- raw 응답 보존 → fixture 변환 분리
"""

import urllib.request
import json
import time
import os
import sys

API_KEY = "fb7bb23f03b6994dafc674c074d01761"
BASE_URL = "https://api.themoviedb.org/3"
FIXTURE_DIR = "backend/movies/fixtures"
RAW_DIR = "backend/movies/fixtures/raw"

def fetch_json(url, retries=3):
    """HTTP GET → JSON, 재시도 포함"""
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(url, timeout=15) as r:
                return json.loads(r.read())
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
            else:
                raise RuntimeError(f"Failed to fetch {url}: {e}")

def collect_genres():
    """장르 목록 수집"""
    url = f"{BASE_URL}/genre/movie/list?api_key={API_KEY}&language=ko-KR"
    data = fetch_json(url)
    return data["genres"]  # [{"id": 28, "name": "액션"}, ...]

def collect_movies_from_endpoint(endpoint, pages=8):
    """popular 또는 top_rated 엔드포인트에서 N 페이지 수집"""
    movies = []
    for page in range(1, pages + 1):
        url = f"{BASE_URL}/movie/{endpoint}?api_key={API_KEY}&language=ko-KR&page={page}"
        try:
            data = fetch_json(url)
            results = data.get("results", [])
            movies.extend(results)
            print(f"  [{endpoint}] page {page}: {len(results)} movies (total so far: {len(movies)})")
            time.sleep(0.25)  # rate limit 안전 마진 (40req/10s)
        except Exception as e:
            print(f"  [!] {endpoint} page {page} 실패: {e}", file=sys.stderr)
    return movies

def deduplicate(movies):
    """tmdb id 기준 중복 제거, popularity 높은 것 우선"""
    seen = {}
    for m in movies:
        mid = m["id"]
        if mid not in seen or m.get("popularity", 0) > seen[mid].get("popularity", 0):
            seen[mid] = m
    return list(seen.values())

def build_genre_fixture(genres):
    """genres.json fixture 형식 생성"""
    fixture = []
    for g in genres:
        fixture.append({
            "model": "movies.genre",
            "pk": g["id"],
            "fields": {
                "name": g["name"]
            }
        })
    return fixture

def normalize_date(date_str):
    """release_date: 비어있거나 형식 불량이면 None"""
    if not date_str or len(date_str) < 4:
        return None
    return date_str[:10]  # YYYY-MM-DD

def build_movie_fixture(movies):
    """movies.json fixture 형식 생성 (pk는 1부터 순번)"""
    fixture = []
    for idx, m in enumerate(movies, start=1):
        release_date = normalize_date(m.get("release_date", ""))
        poster_path = m.get("poster_path") or ""
        backdrop_path = m.get("backdrop_path") or ""
        overview = m.get("overview") or ""
        vote_average = round(float(m.get("vote_average", 0.0)), 3)
        vote_count = int(m.get("vote_count", 0))
        popularity = round(float(m.get("popularity", 0.0)), 3)
        genre_ids = [gid for gid in m.get("genre_ids", []) if gid]

        fixture.append({
            "model": "movies.movie",
            "pk": idx,
            "fields": {
                "tmdb_id": m["id"],
                "title": m.get("title") or m.get("original_title", ""),
                "original_title": m.get("original_title", ""),
                "overview": overview,
                "poster_path": poster_path,
                "backdrop_path": backdrop_path,
                "release_date": release_date,
                "vote_average": vote_average,
                "vote_count": vote_count,
                "popularity": popularity,
                "genres": genre_ids
            }
        })
    return fixture

def compute_quality_report(movies):
    """결측률 수치화 — 데이터 엔지니어 품질 기준"""
    total = len(movies)
    fields = ["title", "overview", "poster_path", "backdrop_path", "release_date", "genre_ids"]
    report = {}
    for f in fields:
        if f == "genre_ids":
            missing = sum(1 for m in movies if not m.get(f))
        elif f == "release_date":
            missing = sum(1 for m in movies if not normalize_date(m.get(f, "")))
        else:
            missing = sum(1 for m in movies if not m.get(f))
        report[f] = {
            "missing": missing,
            "missing_pct": round(missing / total * 100, 2) if total else 0
        }
    return report

def main():
    os.makedirs(FIXTURE_DIR, exist_ok=True)
    os.makedirs(RAW_DIR, exist_ok=True)

    # ─── 1. 장르 수집 ───
    print("[1/4] 장르 수집 중...")
    genres = collect_genres()
    print(f"  장르 {len(genres)}개 수집 완료")

    # raw 보존
    with open(f"{RAW_DIR}/genres_raw.json", "w", encoding="utf-8") as f:
        json.dump(genres, f, ensure_ascii=False, indent=2)

    # ─── 2. 영화 수집 ───
    print("[2/4] popular 영화 수집 중 (8 pages)...")
    popular = collect_movies_from_endpoint("popular", pages=8)

    print("[3/4] top_rated 영화 수집 중 (8 pages)...")
    top_rated = collect_movies_from_endpoint("top_rated", pages=8)

    # raw 보존
    all_raw = popular + top_rated
    with open(f"{RAW_DIR}/movies_raw.json", "w", encoding="utf-8") as f:
        json.dump(all_raw, f, ensure_ascii=False, indent=2)
    print(f"  raw 수집: popular {len(popular)} + top_rated {len(top_rated)} = {len(all_raw)} (중복 포함)")

    # ─── 3. 중복 제거 ───
    unique_movies = deduplicate(all_raw)
    # popularity 내림차순 정렬
    unique_movies.sort(key=lambda m: m.get("popularity", 0), reverse=True)
    print(f"  중복 제거 후: {len(unique_movies)}편")

    if len(unique_movies) < 300:
        print(f"[!] 경고: 300편 미만({len(unique_movies)}편). 페이지 수 증가 필요.", file=sys.stderr)

    # ─── 4. 품질 리포트 ───
    report = compute_quality_report(unique_movies)
    print("\n[품질 리포트]")
    for field, stats in report.items():
        print(f"  {field}: 결측 {stats['missing']}건 ({stats['missing_pct']}%)")

    # 품질 리포트 파일 저장
    with open(f"{RAW_DIR}/quality_report.json", "w", encoding="utf-8") as f:
        json.dump({
            "total_movies": len(unique_movies),
            "quality": report,
            "schema": {
                "tmdb_id": "int — TMDB movie id",
                "title": "str — 한국어 제목(없으면 original_title)",
                "original_title": "str — 원제",
                "overview": "str — 줄거리 (결측 가능)",
                "poster_path": "str — /xxxx.jpg (CDN: https://image.tmdb.org/t/p/w500 + poster_path)",
                "backdrop_path": "str — /xxxx.jpg",
                "release_date": "YYYY-MM-DD | null",
                "vote_average": "float — 0.0~10.0",
                "vote_count": "int",
                "popularity": "float",
                "genres": "list[int] — genre pk 배열(=tmdb genre_id)"
            }
        }, f, ensure_ascii=False, indent=2)

    # ─── 5. fixture 생성 ───
    print("\n[4/4] fixture 파일 생성 중...")

    genre_fixture = build_genre_fixture(genres)
    genre_path = f"{FIXTURE_DIR}/genres.json"
    with open(genre_path, "w", encoding="utf-8") as f:
        json.dump(genre_fixture, f, ensure_ascii=False, indent=2)
    print(f"  genres.json 저장: {genre_path} ({len(genre_fixture)}개)")

    movie_fixture = build_movie_fixture(unique_movies)
    movie_path = f"{FIXTURE_DIR}/movies.json"
    with open(movie_path, "w", encoding="utf-8") as f:
        json.dump(movie_fixture, f, ensure_ascii=False, indent=2)
    print(f"  movies.json 저장: {movie_path} ({len(movie_fixture)}편)")

    # ─── 6. 검증 ───
    print("\n[검증] fixture 파일 재로드 확인...")
    with open(genre_path, encoding="utf-8") as f:
        g_check = json.load(f)
    with open(movie_path, encoding="utf-8") as f:
        m_check = json.load(f)

    assert g_check[0]["model"] == "movies.genre", "genre model 필드 오류"
    assert m_check[0]["model"] == "movies.movie", "movie model 필드 오류"
    assert m_check[0]["pk"] == 1, "pk 시작값 오류"
    assert len(m_check) >= 300, f"300편 미만: {len(m_check)}"
    for m in m_check[:10]:
        assert isinstance(m["fields"]["genres"], list), "genres must be list"
    # pk 연속성 확인
    pks = [m["pk"] for m in m_check]
    assert pks == list(range(1, len(m_check)+1)), "pk 연속성 오류"

    print(f"\n모든 검증 통과 ✓")
    print(f"  {genre_path} — {len(g_check)}개 장르")
    print(f"  {movie_path} — {len(m_check)}편 영화")

    print(f"\n[샘플 — 첫 번째 영화]")
    print(json.dumps(m_check[0], ensure_ascii=False, indent=2))
    print(f"\n[샘플 — 마지막 영화]")
    print(json.dumps(m_check[-1], ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
