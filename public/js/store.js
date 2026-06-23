// CineAI Store — Data, AI Engine, Quiz Generator
const TMDB_BASE = "https://image.tmdb.org/t/p/";

const MOOD_GENRES = {
  action:   [28, 12, 53, 80],
  romance:  [10749, 18, 10402],
  horror:   [27, 9648, 53],
  comedy:   [35, 10751, 10402],
  drama:    [18, 99, 36, 10752],
  scifi:    [878, 14, 12],
  family:   [10751, 16, 35, 14],
  thriller: [53, 9648, 80],
};

const MOOD_LABELS = {
  action:   { label: "신나고 짜릿하게", icon: "⚡" },
  romance:  { label: "로맨틱하게",      icon: "💕" },
  horror:   { label: "무섭고 스릴있게", icon: "👻" },
  comedy:   { label: "웃기고 가볍게",   icon: "😂" },
  drama:    { label: "감동적으로",      icon: "😢" },
  scifi:    { label: "SF·판타지로",    icon: "🚀" },
  family:   { label: "가족과 함께",     icon: "👨‍👩‍👧" },
  thriller: { label: "긴장감 넘치게",   icon: "🎯" },
};

const CineStore = Vue.reactive({
  movies: [],
  genres: [],
  genreMap: {},
  reviews: [],
  leaderboard: [],
  favorites: [],
  loaded: false,
  error: null,

  // Auth state
  token: localStorage.getItem("cineai_token") || null,
  user:  JSON.parse(localStorage.getItem("cineai_user") || "null"),

  async init() {
    try {
      const [mr, gr] = await Promise.all([
        fetch("/data/movies.json"),
        fetch("/data/genres.json"),
      ]);
      this.movies = await mr.json();
      this.genres = await gr.json();
      this.genreMap = Object.fromEntries(this.genres.map(g => [g.id, g.name]));
      this.reviews     = JSON.parse(localStorage.getItem("cineai_reviews")     || "[]");
      this.leaderboard = JSON.parse(localStorage.getItem("cineai_leaderboard") || "[]");
      this.favorites   = JSON.parse(localStorage.getItem("cineai_favorites")   || "[]");
      this.loaded = true;
    } catch (e) {
      this.error = e.message;
      this.loaded = true;
    }
  },

  // ── Auth helpers ──────────────────────────────────────────────────────
  login(token, user) {
    this.token = token; this.user = user;
    localStorage.setItem("cineai_token", token);
    localStorage.setItem("cineai_user", JSON.stringify(user));
  },
  logout() {
    this.token = null; this.user = null;
    localStorage.removeItem("cineai_token");
    localStorage.removeItem("cineai_user");
  },
  get authHeaders() {
    return this.token ? { Authorization: `Bearer ${this.token}` } : {};
  },
  async apiGet(url) {
    const r = await fetch(url, { headers: this.authHeaders });
    const d = await r.json();
    if (!r.ok) throw new Error(d.error || "API 오류");
    return d;
  },
  async apiPost(url, body, method = "POST") {
    const r = await fetch(url, {
      method,
      headers: { "Content-Type": "application/json", ...this.authHeaders },
      body: JSON.stringify(body)
    });
    if (r.status === 204) return null;
    const d = await r.json();
    if (!r.ok) throw new Error(d.error || "API 오류");
    return d;
  },
  apiPut(url, body)    { return this.apiPost(url, body, "PUT"); },
  apiDelete(url)       { return this.apiPost(url, {}, "DELETE"); },

  // ── Image helpers ─────────────────────────────────────
  getPosterUrl(path, size) {
    if (!path) return "https://via.placeholder.com/300x450/1a1a28/f0b429?text=No+Image";
    return TMDB_BASE + (size || "w500") + path;
  },
  getBackdropUrl(path) {
    if (!path) return "";
    return TMDB_BASE + "w1280" + path;
  },

  // ── Date helpers ──────────────────────────────────────
  getYear(d) { return d ? d.substring(0, 4) : "?"; },
  formatDate(d) {
    if (!d) return "";
    return new Date(d).toLocaleDateString("ko-KR", { year: "numeric", month: "long", day: "numeric" });
  },

  // ── Genre helpers ─────────────────────────────────────
  getGenreName(id) { return this.genreMap[id] || "기타"; },
  getMovieGenres(movie) {
    return (movie.genres || []).map(id => this.genreMap[id]).filter(Boolean);
  },

  // ── Queries ───────────────────────────────────────────
  getMovieById(id) { return this.movies.find(m => m.id === parseInt(id)); },
  getTopMovies(count) {
    return [...this.movies].sort((a, b) => b.popularity - a.popularity).slice(0, count || 5);
  },
  getMoviesByGenre(genreId, count) {
    return this.movies
      .filter(m => m.genres.includes(genreId))
      .sort((a, b) => b.vote_average - a.vote_average)
      .slice(0, count || 12);
  },
  searchMovies(query, genreId, page, pageSize) {
    page = page || 1; pageSize = pageSize || 20;
    let r = [...this.movies];
    if (query) {
      const q = query.toLowerCase();
      r = r.filter(m => m.title.toLowerCase().includes(q) || (m.original_title || "").toLowerCase().includes(q));
    }
    if (genreId) r = r.filter(m => m.genres.includes(parseInt(genreId)));
    r.sort((a, b) => b.popularity - a.popularity);
    const total = r.length;
    const start = (page - 1) * pageSize;
    return { results: r.slice(start, start + pageSize), total, pages: Math.ceil(total / pageSize), page };
  },

  // ── AI Engine — 장르 벡터 코사인 유사도 ────────────────────
  _GENRE_IDS: [12, 14, 16, 18, 27, 28, 35, 36, 37, 53, 80, 99, 878,
               9648, 10402, 10749, 10751, 10752, 10770],
  _genreVec(movie) {
    const gs = new Set(movie.genres || []);
    return this._GENRE_IDS.map(id => (gs.has(id) ? 1 : 0));
  },
  _cosineSim(va, vb) {
    let dot = 0, na = 0, nb = 0;
    for (let i = 0; i < va.length; i++) {
      dot += va[i] * vb[i]; na += va[i] * va[i]; nb += vb[i] * vb[i];
    }
    return (na === 0 || nb === 0) ? 0 : dot / (Math.sqrt(na) * Math.sqrt(nb));
  },
  _sim(a, b) {
    const gSim = this._cosineSim(this._genreVec(a), this._genreVec(b));
    const rSim = 1 - Math.abs((a.vote_average || 0) - (b.vote_average || 0)) / 10;
    const yA   = parseInt((a.release_date || "2000").substring(0, 4));
    const yB   = parseInt((b.release_date || "2000").substring(0, 4));
    const ySim = 1 - Math.min(Math.abs(yA - yB), 30) / 30;
    return gSim * 0.70 + rSim * 0.20 + ySim * 0.10;
  },
  getSimilarMovies(movieId, count) {
    const t = this.getMovieById(movieId);
    if (!t) return [];
    return this.movies
      .filter(m => m.id !== t.id)
      .map(m => ({ ...m, _sim: this._sim(t, m) }))
      .sort((a, b) => b._sim - a._sim)
      .slice(0, count || 6);
  },
  getRecommendations({ genreIds, mood, excludeIds, count }) {
    genreIds = genreIds || []; excludeIds = excludeIds || []; count = count || 8;
    const moodG = mood ? (MOOD_GENRES[mood] || []) : [];
    const allTarget = [...new Set([...genreIds, ...moodG])];
    return this.movies
      .filter(m => !excludeIds.includes(m.id))
      .map(m => {
        const gScore = allTarget.length
          ? m.genres.filter(g => allTarget.includes(g)).length / allTarget.length * 0.55 : 0;
        const exactBonus = genreIds.length
          ? m.genres.filter(g => genreIds.includes(g)).length / genreIds.length * 0.15 : 0;
        const rScore = (m.vote_average || 0) / 10 * 0.25;
        const pScore = Math.min((m.popularity || 0) / 600, 1) * 0.05;
        return { ...m, _score: gScore + exactBonus + rScore + pScore };
      })
      .sort((a, b) => b._score - a._score)
      .slice(0, count);
  },
  getHomeRecommendations() {
    const seen = new Set(); const result = [];
    const sorted = [...this.movies].sort((a, b) =>
      (b.vote_average * 0.7 + Math.min(b.popularity / 600, 1) * 3) -
      (a.vote_average * 0.7 + Math.min(a.popularity / 600, 1) * 3)
    );
    for (const m of sorted) {
      if (result.length >= 3) break;
      const gKey = m.genres[0];
      if (!seen.has(gKey)) { seen.add(gKey); result.push(m); }
    }
    return result;
  },

  // ── Quiz (client-side fallback) ─────────────────────────────────────────
  generateQuestions(mode, count) {
    count = count || 10;
    const sh = a => [...a].sort(() => Math.random() - 0.5);
    let pool = this.movies.filter(m => m.poster_path && m.title);
    if (mode === "director") pool = pool.filter(m => m.director);
    if (mode === "cast")     pool = pool.filter(m => m.cast && m.cast.length);
    if (mode === "genre")    pool = pool.filter(m => m.genres && m.genres.length);
    if (mode === "overview") pool = pool.filter(m => m.overview && m.overview.length >= 40);
    const shuffled = sh(pool), qs = []; let i = 0;
    while (qs.length < count && i < shuffled.length) {
      const t = shuffled[i++];
      const distr = sh(pool.filter(m => m.id !== t.id)).slice(0, 3);
      if (mode === "poster") {
        qs.push({ type: "poster", prompt: "이 포스터의 영화 제목은?",
          image: this.getPosterUrl(t.poster_path), correctId: t.id,
          choices: sh([t, ...distr]).map(m => ({ id: m.id, label: m.title })), timeLimit: 30 });
      } else if (mode === "director") {
        const dirs = [...new Set(distr.filter(m => m.director && m.director !== t.director).map(m => m.director))];
        if (dirs.length < 3) continue;
        qs.push({ type: "director", prompt: "이 영화를 연출한 감독은?",
          image: this.getPosterUrl(t.poster_path), movieTitle: t.title, correctId: t.director,
          choices: sh([t.director, ...dirs.slice(0, 3)]).map(d => ({ id: d, label: d })), timeLimit: 25 });
      } else if (mode === "cast") {
        const actor = t.cast[0];
        const wa = [...new Set(distr.flatMap(m => m.cast || []).filter(a => a !== actor))].slice(0, 3);
        if (wa.length < 3) continue;
        qs.push({ type: "cast", prompt: "이 영화의 주연 배우는?",
          image: this.getPosterUrl(t.poster_path), movieTitle: t.title, correctId: actor,
          choices: sh([actor, ...wa]).map(a => ({ id: a, label: a })), timeLimit: 25 });
      } else if (mode === "genre") {
        const tg = t.genres[0]; if (!tg) continue;
        const wg = sh(this.genres.filter(g => g.id !== tg)).slice(0, 3);
        qs.push({ type: "genre", prompt: `"${t.title}"의 주요 장르는?`,
          image: this.getPosterUrl(t.poster_path, "w300"), correctId: tg,
          choices: sh([{ id: tg, label: this.genreMap[tg] }, ...wg.map(g => ({ id: g.id, label: g.name }))]), timeLimit: 20 });
      } else if (mode === "year") {
        const cy = t.year || parseInt((t.release_date || "2000").slice(0, 4)) || 2000;
        const yrs = [cy];
        for (const o of sh([-4,-3,-2,-1,1,2,3,4])) { if (yrs.length >= 4) break; const y = cy + o; if (!yrs.includes(y)) yrs.push(y); }
        qs.push({ type: "year", prompt: `"${t.title}" 개봉 연도는?`,
          image: this.getPosterUrl(t.poster_path, "w300"), correctId: cy,
          choices: sh(yrs).map(y => ({ id: y, label: y + "년" })), timeLimit: 15 });
      } else if (mode === "overview") {
        const snippet = t.overview.slice(0, 100) + "...";
        qs.push({ type: "overview", prompt: "다음 줄거리의 영화는?", snippet, correctId: t.id,
          choices: sh([t, ...distr]).map(m => ({ id: m.id, label: m.title })), timeLimit: 28 });
      }
    }
    return qs.slice(0, count);
  },

  // ── Reviews ───────────────────────────────────────────
  addReview(r) {
    const entry = { ...r, id: Date.now(), createdAt: new Date().toISOString() };
    this.reviews.unshift(entry);
    localStorage.setItem("cineai_reviews", JSON.stringify(this.reviews));
    return entry;
  },
  getReviews(movieId) {
    if (movieId != null) return this.reviews.filter(r => r.movieId === parseInt(movieId));
    return this.reviews;
  },

  // ── Leaderboard ───────────────────────────────────────
  addLeaderboardEntry(entry) {
    this.leaderboard.push({ ...entry, date: new Date().toISOString() });
    this.leaderboard.sort((a, b) => b.score - a.score);
    this.leaderboard = this.leaderboard.slice(0, 100);
    localStorage.setItem("cineai_leaderboard", JSON.stringify(this.leaderboard));
  },

  // ── Favorites ─────────────────────────────────────────
  toggleFavorite(id) {
    const idx = this.favorites.indexOf(id);
    if (idx >= 0) this.favorites.splice(idx, 1);
    else this.favorites.push(id);
    localStorage.setItem("cineai_favorites", JSON.stringify(this.favorites));
  },
  isFavorite(id) { return this.favorites.includes(id); },

  get moodLabels() { return MOOD_LABELS; },
  get moodGenreMap() { return MOOD_GENRES; },
});
