import json, os

GENRE_MAP = {
    "Action": 28, "Adventure": 12, "Animation": 16, "Comedy": 35,
    "Crime": 80, "Documentary": 99, "Drama": 18, "Family": 10751,
    "Fantasy": 14, "History": 36, "Horror": 27, "Music": 10402,
    "Mystery": 9648, "Romance": 10749, "Science Fiction": 878,
    "TV Movie": 10770, "Thriller": 53, "War": 10752, "Western": 37
}

with open('/tmp/glin_movies.json') as f:
    raw = json.load(f)

movies = []
for m in raw:
    if not m.get('poster_path'): continue
    if not m.get('overview') or len(m['overview']) < 40: continue
    if not m.get('genres'): continue
    if not m.get('directors'): continue

    genre_ids = [GENRE_MAP[g] for g in m['genres'] if g in GENRE_MAP]
    if not genre_ids: continue

    director = m['directors'][0]['name'] if m['directors'] else ''
    cast_names = [c['name'] for c in (m.get('cast') or [])[:3]]

    yr = str(m.get('release_date', ''))[:4]
    year = int(yr) if yr.isdigit() else 2000

    movies.append({
        "id": m['id'],
        "title": m['title'],
        "original_title": m.get('title', m['title']),
        "overview": m['overview'],
        "poster_path": m['poster_path'],
        "backdrop_path": None,
        "release_date": m.get('release_date', ''),
        "vote_average": round(float(m.get('vote_average', 0)), 1),
        "vote_count": int(m.get('vote_count', 0)),
        "genres": genre_ids,
        "director": director,
        "cast": cast_names,
        "trailer_yt": m.get('trailer_yt', ''),
        "year": year,
        "popularity": float(m.get('popularity', 0))
    })

movies.sort(key=lambda x: x['vote_count'], reverse=True)
movies = movies[:500]

os.makedirs('public/data', exist_ok=True)
with open('public/data/movies.json', 'w') as f:
    json.dump(movies, f, ensure_ascii=False)

print(f"Saved {len(movies)} movies")
print("Sample:", json.dumps(movies[0], indent=2)[:400])
