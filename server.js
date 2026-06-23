'use strict';
require('dotenv').config();
const express    = require('express');
const cors       = require('cors');
const path       = require('path');
const fs         = require('fs');
const bcrypt     = require('bcryptjs');
const jwt        = require('jsonwebtoken');
const compression = require('compression');

const app        = express();
const PORT       = process.env.PORT || 3000;
const JWT_SECRET = process.env.JWT_SECRET || 'cineai-dev-secret-change-in-prod';

// ── Middleware ────────────────────────────────────────────────────────────
app.use(compression());
app.use(cors({ origin: true, credentials: true }));
app.use(express.json({ limit: '2mb' }));

// ── Static Data ──────────────────────────────────────────────────────────
const PUBLIC_DATA = path.join(__dirname, 'public', 'data');
const SERVER_DATA = path.join(__dirname, 'data');

let MOVIES = [];
let GENRES = [];
let GENRE_MAP = {};

function loadStaticData() {
  MOVIES = JSON.parse(fs.readFileSync(path.join(PUBLIC_DATA, 'movies.json'), 'utf-8'));
  GENRES = JSON.parse(fs.readFileSync(path.join(PUBLIC_DATA, 'genres.json'), 'utf-8'));
  GENRE_MAP = Object.fromEntries(GENRES.map(g => [g.id, g.name]));
  console.log(`✅ Loaded ${MOVIES.length} movies, ${GENRES.length} genres`);
  buildRecommendationIndex();
}

// ── Persistent JSON Stores ────────────────────────────────────────────────
function loadStore(file, def) {
  const fp = path.join(SERVER_DATA, file);
  try { if (fs.existsSync(fp)) return JSON.parse(fs.readFileSync(fp, 'utf-8')); }
  catch (e) { /* ignore */ }
  return def;
}
function saveStore(file, data) {
  const fp = path.join(SERVER_DATA, file);
  if (!fs.existsSync(SERVER_DATA)) fs.mkdirSync(SERVER_DATA, { recursive: true });
  fs.writeFileSync(fp, JSON.stringify(data), 'utf-8');
}

let users          = loadStore('users.json',       []);
let posts          = loadStore('posts.json',        []);
let leaderboard    = loadStore('leaderboard.json',  []);
let userPrefs      = loadStore('userPrefs.json',    {});  // { [userId]: { genreWeights:{}, playCount:0 } }
let userStats      = loadStore('userStats.json',    {});  // { [userId]: { totalPlays, totalScore, bestScore, correctCount, totalQuestions, genreCount, viewHistory, ... } }
let userAchievements = {};                                // in-memory: { [userId]: Set<achievementId> }
let dailyLeaderboard = {};                               // in-memory: { [dateStr]: [{username, score, correct, total, time}] }
let viewCounts     = {};                                 // in-memory: { [movieId]: count }

// ── Advanced AI Recommendation Engine v2 ─────────────────────────────────
// 알고리즘: TF-IDF 장르(0.45) + 평점근접(0.15) + 연도근접(0.08)
//          + 감독보너스(0.15) + 배우오버랩(0.10) + popularity boost(0.07)
// 다양성:  MMR re-ranking (lambda=0.65) + 동일감독 2편 초과 패널티
// 개인화:  ?userId= → 퀴즈 정답 장르 누적 가중치 부스트

const GENRE_IDS = [12, 14, 16, 18, 27, 28, 35, 36, 37, 53, 80, 99, 878,
                   9648, 10402, 10749, 10751, 10752, 10770];

// ── 1. 인덱스 빌드 (loadStaticData 후 호출) ──────────────────────────────
let GENRE_IDF  = {};
let POP_LOG_MIN = 0, POP_LOG_MAX = 1;
let VOTE_LOG_MAX = 1;

function buildRecommendationIndex() {
  if (MOVIES.length === 0) return;

  const N  = MOVIES.length;
  const df = {};
  MOVIES.forEach(m => {
    const seen = new Set((m.genres || []).map(String));
    seen.forEach(g => { df[g] = (df[g] || 0) + 1; });
  });
  GENRE_IDF = {};
  Object.entries(df).forEach(([g, cnt]) => {
    GENRE_IDF[g] = Math.log((N + 1) / (cnt + 1)) + 1;
  });

  const pops  = MOVIES.map(m => Math.log1p(m.popularity  || 0));
  const votes = MOVIES.map(m => Math.log1p(m.vote_count  || 0));
  POP_LOG_MIN  = Math.min(...pops);
  POP_LOG_MAX  = Math.max(...pops)  || 1;
  VOTE_LOG_MAX = Math.max(...votes) || 1;

  console.log(`✅ Rec-index v2: ${Object.keys(GENRE_IDF).length} genres, ` +
              `IDF [${Math.min(...Object.values(GENRE_IDF)).toFixed(2)}, ` +
              `${Math.max(...Object.values(GENRE_IDF)).toFixed(2)}]`);
}

// ── 2. 기본 연산 ──────────────────────────────────────────────────────────
function cosineSim(va, vb) {
  let dot = 0, na = 0, nb = 0;
  for (let i = 0; i < va.length; i++) {
    dot += va[i] * vb[i];
    na  += va[i] * va[i];
    nb  += vb[i] * vb[i];
  }
  return (na === 0 || nb === 0) ? 0 : dot / (Math.sqrt(na) * Math.sqrt(nb));
}

function genreVectorTFIDF(movie, userGenreWeights) {
  const gs = new Set((movie.genres || []).map(String));
  return GENRE_IDS.map(id => {
    if (!gs.has(String(id))) return 0;
    const idf   = GENRE_IDF[String(id)] || 1;
    const boost = (userGenreWeights && userGenreWeights[String(id)]) || 1;
    return idf * boost;
  });
}

function directorBonus(a, b) {
  if (!a.director || !b.director) return 0;
  return a.director === b.director ? 1.0 : 0;
}

function castJaccard(a, b) {
  const ca = new Set((a.cast || []).slice(0, 5));
  const cb = new Set((b.cast || []).slice(0, 5));
  if (ca.size === 0 || cb.size === 0) return 0;
  let inter = 0;
  ca.forEach(actor => { if (cb.has(actor)) inter++; });
  return inter / (ca.size + cb.size - inter);
}

function popularityBoost(b) {
  const pNorm = POP_LOG_MAX > POP_LOG_MIN
    ? (Math.log1p(b.popularity || 0) - POP_LOG_MIN) / (POP_LOG_MAX - POP_LOG_MIN)
    : 0;
  const vNorm = Math.log1p(b.vote_count || 0) / VOTE_LOG_MAX;
  return pNorm * 0.6 + vNorm * 0.4;
}

function simScore(a, b, userGenreWeights) {
  const va   = genreVectorTFIDF(a, userGenreWeights);
  const vb   = genreVectorTFIDF(b, null);
  const gSim = cosineSim(va, vb);

  const rSim = 1 - Math.abs((a.vote_average || 0) - (b.vote_average || 0)) / 10;

  const yA   = a.year || parseInt((a.release_date || '2000').slice(0, 4)) || 2000;
  const yB   = b.year || parseInt((b.release_date || '2000').slice(0, 4)) || 2000;
  const ySim = 1 - Math.min(Math.abs(yA - yB), 30) / 30;

  const dirB  = directorBonus(a, b);
  const castB = castJaccard(a, b);
  const popB  = popularityBoost(b);

  return gSim  * 0.45
       + rSim  * 0.15
       + ySim  * 0.08
       + dirB  * 0.15
       + castB * 0.10
       + popB  * 0.07;
}

// ── 5. MMR Diversity Re-ranking ───────────────────────────────────────────
function mmrRerank(scored, lambda, k) {
  if (scored.length === 0) return [];
  const selected  = [];
  const remaining = scored.slice();

  while (selected.length < k && remaining.length > 0) {
    let bestIdx = 0, bestMmr = -Infinity;

    for (let i = 0; i < remaining.length; i++) {
      const c = remaining[i];

      let maxRedundancy = 0;
      for (const s of selected) {
        const sim = cosineSim(
          genreVectorTFIDF(c, null),
          genreVectorTFIDF(s, null)
        );
        if (sim > maxRedundancy) maxRedundancy = sim;
      }

      const sameDir   = selected.filter(s => s._dir && s._dir === c._dir).length;
      const dirPenalty = sameDir >= 2 ? 0.35 : 0;

      const mmr = lambda * c.rawScore - (1 - lambda) * maxRedundancy - dirPenalty;
      if (mmr > bestMmr) { bestMmr = mmr; bestIdx = i; }
    }

    selected.push(remaining[bestIdx]);
    remaining.splice(bestIdx, 1);
  }

  return selected;
}

// ── 6. 개인화: 유저 장르 선호도 관리 ─────────────────────────────────────
function getUserGenreWeights(userId) {
  const p = userPrefs[String(userId)];
  return (p && p.genreWeights && Object.keys(p.genreWeights).length > 0)
    ? p.genreWeights : null;
}

function updateUserPrefs(userId, movieIds) {
  if (!userId || !movieIds || movieIds.length === 0) return;
  const uid = String(userId);
  if (!userPrefs[uid]) userPrefs[uid] = { genreWeights: {}, playCount: 0 };

  const p = userPrefs[uid];
  p.playCount = (p.playCount || 0) + 1;

  Object.keys(p.genreWeights).forEach(g => { p.genreWeights[g] *= 0.9; });

  movieIds.forEach(mid => {
    const movie = MOVIES.find(m => m.id === parseInt(mid));
    if (!movie) return;
    (movie.genres || []).forEach(g => {
      const gk = String(g);
      p.genreWeights[gk] = (p.genreWeights[gk] || 1.0) + 0.15;
    });
  });

  const maxW = Math.max(...Object.values(p.genreWeights));
  if (maxW > 2.5) {
    const scale = 2.5 / maxW;
    Object.keys(p.genreWeights).forEach(g => { p.genreWeights[g] *= scale; });
  }

  userPrefs[uid] = p;
  saveStore('userPrefs.json', userPrefs);
}

// ── 7. 공개 추천 함수 ─────────────────────────────────────────────────────
function getRecommendations(movie, count, userId) {
  if (count === undefined) count = 5;
  const userGenreWeights = userId ? getUserGenreWeights(userId) : null;

  const scored = MOVIES
    .filter(m => m.id !== movie.id)
    .map(m => ({
      id:           m.id,
      title:        m.title,
      poster_path:  m.poster_path,
      vote_average: m.vote_average,
      genres:       m.genres,
      score:        0,
      rawScore:     simScore(movie, m, userGenreWeights),
      _dir:         m.director || null
    }))
    .sort((a, b) => b.rawScore - a.rawScore)
    .slice(0, count * 6);

  const reranked = mmrRerank(scored, 0.65, count);

  return reranked.map(({ rawScore, _dir, ...rest }) => ({
    ...rest,
    score: parseFloat(rawScore.toFixed(4))
  }));
}

// ── Achievement Definitions ───────────────────────────────────────────────
const ACHIEVEMENTS = [
  { id: 'first_win',    name: '첫 승리',       desc: '첫 퀴즈 완료',              icon: '🏆' },
  { id: 'streak_5',     name: '5연속 정답',    desc: '한 게임 5연속 정답',         icon: '🔥' },
  { id: 'streak_10',    name: '10연속 정답',   desc: '한 게임 10연속 정답',        icon: '💥' },
  { id: 'score_1000',   name: '1000점 달성',   desc: '한 게임 1000점 이상',        icon: '⭐' },
  { id: 'genre_master', name: '장르 마스터',   desc: '같은 장르 10번 플레이',      icon: '🎬' },
  { id: 'daily_3',      name: '3일 챌린지',    desc: '3일 연속 일일 챌린지 참여',  icon: '📅' },
  { id: 'movie_100',    name: '100편 감상',    desc: '영화 100편 상세 페이지 방문', icon: '🎞️' },
  { id: 'perfect_game', name: '퍼펙트 게임',   desc: '10문제 전부 정답',           icon: '💎' },
  { id: 'speed_demon',  name: '스피드 데몬',   desc: '타임아웃 없이 10문제 완료',  icon: '⚡' },
];
const ACHIEVEMENT_MAP = Object.fromEntries(ACHIEVEMENTS.map(a => [a.id, a]));

function getUserAchievements(userId) {
  const uid = String(userId);
  if (!userAchievements[uid]) userAchievements[uid] = new Set();
  return userAchievements[uid];
}

function checkAchievements(userId, { score, streak, genre, totalPlays, correct, total, viewCount }) {
  const gained = [];
  const existing = getUserAchievements(userId);
  const add = (id) => {
    if (!existing.has(id)) {
      existing.add(id);
      gained.push({ ...ACHIEVEMENT_MAP[id], newlyEarned: true });
    }
  };

  if (totalPlays >= 1)  add('first_win');
  if (streak >= 5)      add('streak_5');
  if (streak >= 10)     add('streak_10');
  if (score >= 1000)    add('score_1000');
  if (correct === 10 && total === 10) add('perfect_game');
  if (viewCount >= 100) add('movie_100');

  const stats = userStats[String(userId)];
  if (stats) {
    if (stats.totalPlays >= 1) add('first_win');
    const gCount = stats.genreCount || {};
    if (Object.values(gCount).some(c => c >= 10)) add('genre_master');
    if ((stats.viewHistory || []).length >= 100) add('movie_100');
  }

  return gained;
}

// ── User Stats Helpers ────────────────────────────────────────────────────
function getUserStats(userId) {
  const uid = String(userId);
  if (!userStats[uid]) userStats[uid] = {
    totalPlays: 0, totalScore: 0, bestScore: 0,
    correctCount: 0, totalQuestions: 0,
    genreCount: {}, viewHistory: [], dailyStreak: 0, lastDaily: null
  };
  return userStats[uid];
}

function updateUserStats(userId, { score, correct, total, movieIds, mode }) {
  const uid = String(userId);
  const s   = getUserStats(uid);
  s.totalPlays    += 1;
  s.totalScore    += score || 0;
  s.bestScore      = Math.max(s.bestScore, score || 0);
  s.correctCount  += correct || 0;
  s.totalQuestions+= total  || 0;

  // 장르 카운트 누적
  (movieIds || []).forEach(mid => {
    const movie = MOVIES.find(m => m.id === parseInt(mid));
    if (!movie) return;
    (movie.genres || []).forEach(g => {
      const gk = String(g);
      s.genreCount[gk] = (s.genreCount[gk] || 0) + 1;
    });
  });
  userStats[uid] = s;
  saveStore('userStats.json', userStats);
}

// ── Quiz Generator ────────────────────────────────────────────────────────
function shuffle(arr) {
  const a = arr.slice();
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

const TIME_LIMITS = { poster: 30, director: 25, cast: 25, genre: 20, year: 15, overview: 28 };

function generateQuiz(mode, count = 10) {
  let pool = MOVIES.filter(m => m.poster_path && m.title);

  if (mode === 'director')  pool = pool.filter(m => m.director);
  if (mode === 'cast')      pool = pool.filter(m => m.cast && m.cast.length > 0);
  if (mode === 'genre')     pool = pool.filter(m => m.genres && m.genres.length > 0);
  if (mode === 'overview')  pool = pool.filter(m => m.overview && m.overview.length >= 40);

  const shuffled  = shuffle(pool);
  const questions = [];
  let i = 0;

  while (questions.length < count && i < shuffled.length) {
    const t = shuffled[i++];
    const distract = shuffle(pool.filter(m => m.id !== t.id));

    if (mode === 'poster') {
      const choices = shuffle([t, ...distract.slice(0, 3)]);
      questions.push({
        type: 'poster',
        prompt: '이 포스터의 영화 제목은?',
        image: `https://image.tmdb.org/t/p/w500${t.poster_path}`,
        correctId: t.id,
        choices: choices.map(m => ({ id: m.id, label: m.title })),
        timeLimit: TIME_LIMITS.poster
      });

    } else if (mode === 'director') {
      const directors = [...new Set(distract.filter(m => m.director && m.director !== t.director).map(m => m.director))].slice(0, 3);
      if (directors.length < 3) continue;
      const choices = shuffle([t.director, ...directors]).map(d => ({ id: d, label: d }));
      questions.push({
        type: 'director',
        prompt: '이 영화를 연출한 감독은?',
        image: `https://image.tmdb.org/t/p/w500${t.poster_path}`,
        movieTitle: t.title,
        correctId: t.director,
        choices,
        timeLimit: TIME_LIMITS.director
      });

    } else if (mode === 'cast') {
      const actor = t.cast[0];
      const wrongActors = [...new Set(
        distract.flatMap(m => m.cast || []).filter(a => a !== actor)
      )].slice(0, 3);
      if (wrongActors.length < 3) continue;
      const choices = shuffle([actor, ...wrongActors]).map(a => ({ id: a, label: a }));
      questions.push({
        type: 'cast',
        prompt: '이 영화의 주연 배우는?',
        image: `https://image.tmdb.org/t/p/w500${t.poster_path}`,
        movieTitle: t.title,
        correctId: actor,
        choices,
        timeLimit: TIME_LIMITS.cast
      });

    } else if (mode === 'genre') {
      const tg = t.genres[0];
      if (!tg) continue;
      const wrongGenres = shuffle(GENRES.filter(g => g.id !== tg)).slice(0, 3);
      const choices = shuffle([
        { id: tg, label: GENRE_MAP[tg] || String(tg) },
        ...wrongGenres.map(g => ({ id: g.id, label: g.name }))
      ]);
      questions.push({
        type: 'genre',
        prompt: `"${t.title}"의 주요 장르는?`,
        image: `https://image.tmdb.org/t/p/w300${t.poster_path}`,
        correctId: tg,
        choices,
        timeLimit: TIME_LIMITS.genre
      });

    } else if (mode === 'year') {
      const cy = t.year || parseInt((t.release_date || '2000').slice(0, 4)) || 2000;
      const years = [cy];
      for (const o of shuffle([-4,-3,-2,-1,1,2,3,4])) {
        if (years.length >= 4) break;
        const y = cy + o;
        if (!years.includes(y) && y > 1900) years.push(y);
      }
      questions.push({
        type: 'year',
        prompt: `"${t.title}" 개봉 연도는?`,
        image: `https://image.tmdb.org/t/p/w300${t.poster_path}`,
        correctId: cy,
        choices: shuffle(years).map(y => ({ id: y, label: `${y}년` })),
        timeLimit: TIME_LIMITS.year
      });

    } else if (mode === 'overview') {
      if (!t.overview || t.overview.length < 40) continue;
      const snippet = t.overview.slice(0, 100) + '...';
      const choices = shuffle([t, ...distract.slice(0, 3)]).map(m => ({ id: m.id, label: m.title }));
      questions.push({
        type: 'overview',
        prompt: '다음 줄거리의 영화는?',
        snippet,
        correctId: t.id,
        choices,
        timeLimit: TIME_LIMITS.overview
      });
    }
  }
  return questions.slice(0, count);
}

// ── Auth Middleware ───────────────────────────────────────────────────────
function authRequired(req, res, next) {
  const h = req.headers.authorization;
  if (!h || !h.startsWith('Bearer '))
    return res.status(401).json({ error: '로그인이 필요합니다' });
  try {
    req.user = jwt.verify(h.slice(7), JWT_SECRET);
    next();
  } catch (e) {
    return res.status(401).json({ error: '유효하지 않은 토큰입니다' });
  }
}
function authOptional(req, res, next) {
  const h = req.headers.authorization;
  if (h && h.startsWith('Bearer ')) {
    try { req.user = jwt.verify(h.slice(7), JWT_SECRET); } catch (e) { /* ok */ }
  }
  next();
}

// ═══════════════════════════════════════════════════════════════════════════
//  API Routes — all /api/* before static files
// ═══════════════════════════════════════════════════════════════════════════

// GET /api/genres
app.get('/api/genres', (_req, res) => {
  res.json({ genres: GENRES, total: GENRES.length });
});

// GET /api/movies/search  ← must be before /:id
app.get('/api/movies/search', (req, res) => {
  const { q, genre, sort = 'popularity' } = req.query;
  const page  = Math.max(1, parseInt(req.query.page)  || 1);
  const limit = Math.min(50, Math.max(1, parseInt(req.query.limit) || 20));

  let r = [...MOVIES];
  if (q) {
    const ql = q.toLowerCase();
    r = r.filter(m =>
      m.title.toLowerCase().includes(ql) ||
      (m.original_title || '').toLowerCase().includes(ql) ||
      (m.director || '').toLowerCase().includes(ql)
    );
  }
  if (genre) { const gid = parseInt(genre); r = r.filter(m => (m.genres || []).includes(gid)); }
  if (sort === 'rating') r.sort((a, b) => b.vote_average - a.vote_average);
  else if (sort === 'year') r.sort((a, b) => (b.year || 0) - (a.year || 0));
  else r.sort((a, b) => (b.popularity || 0) - (a.popularity || 0));

  const total = r.length;
  const start = (page - 1) * limit;
  res.json({ results: r.slice(start, start + limit), page, limit, total, pages: Math.ceil(total / limit) });
});

// GET /api/movies
app.get('/api/movies', (req, res) => {
  const page  = Math.max(1, parseInt(req.query.page)  || 1);
  const limit = Math.min(50, Math.max(1, parseInt(req.query.limit) || 20));
  const genre = req.query.genre ? parseInt(req.query.genre) : null;
  const sort  = req.query.sort || 'popularity';

  let r = [...MOVIES];
  if (genre) r = r.filter(m => (m.genres || []).includes(genre));
  if (sort === 'rating') r.sort((a, b) => b.vote_average - a.vote_average);
  else if (sort === 'year') r.sort((a, b) => (b.year || 0) - (a.year || 0));
  else r.sort((a, b) => (b.popularity || 0) - (a.popularity || 0));

  const total = r.length;
  const start = (page - 1) * limit;
  res.json({ results: r.slice(start, start + limit), page, limit, total, pages: Math.ceil(total / limit) });
});

// GET /api/movies/recommend/personalized  — 로그인 사용자 시청 이력 + 장르 선호도 기반 추천 10편
app.get('/api/movies/recommend/personalized', authOptional, (req, res) => {
  const count = Math.min(20, Math.max(1, parseInt(req.query.count) || 10));

  if (!req.user) {
    // 비로그인: popularity 기반 기본 추천
    const picks = MOVIES.slice()
      .sort((a, b) => ((b.popularity || 0) * 0.6 + (b.vote_average || 0) * 0.4)
                    - ((a.popularity || 0) * 0.6 + (a.vote_average || 0) * 0.4))
      .slice(0, count)
      .map(m => ({ id: m.id, title: m.title, poster_path: m.poster_path,
                   vote_average: m.vote_average, genres: m.genres }));
    return res.json({ recommendations: picks, personalized: false });
  }

  const uid    = req.user.id;
  const stats  = getUserStats(String(uid));
  const history = stats.viewHistory || [];
  const viewedIds = new Set(history.map(v => parseInt(v)));

  // 시청 이력 기반 프로파일 영화 → 각각에 대한 추천 집계
  const userGenreWeights = getUserGenreWeights(uid);

  let candidateScores = {};
  const profileMovies = history.slice(-10).map(id => MOVIES.find(m => m.id === parseInt(id))).filter(Boolean);

  if (profileMovies.length > 0) {
    profileMovies.forEach(pm => {
      MOVIES
        .filter(m => !viewedIds.has(m.id))
        .forEach(m => {
          const s = simScore(pm, m, userGenreWeights);
          candidateScores[m.id] = (candidateScores[m.id] || 0) + s;
        });
    });
  } else {
    // 이력 없으면 장르 선호도만 활용
    const fakeProfile = { genres: Object.keys(userGenreWeights || {}).map(Number),
                          vote_average: 7, popularity: 100, year: 2015, director: null, cast: [] };
    MOVIES.forEach(m => {
      candidateScores[m.id] = simScore(fakeProfile, m, userGenreWeights);
    });
  }

  const sorted = Object.entries(candidateScores)
    .sort((a, b) => b[1] - a[1])
    .slice(0, count * 3)
    .map(([id, sc]) => {
      const m = MOVIES.find(mv => mv.id === parseInt(id));
      return m ? { id: m.id, title: m.title, poster_path: m.poster_path,
                   vote_average: m.vote_average, genres: m.genres, score: parseFloat(sc.toFixed(4)) } : null;
    })
    .filter(Boolean);

  const reranked = sorted.slice(0, count);
  res.json({ recommendations: reranked, personalized: true });
});

// GET /api/movies/recommend  — AI-curated trending picks (no seed needed)
app.get('/api/movies/recommend', (req, res) => {
  const count = Math.min(20, Math.max(1, parseInt(req.query.count) || 10));
  // daily-stable seed: shuffle changes once per day, consistent within a day
  const daySeed = Math.floor(Date.now() / 86400000);
  const picks = MOVIES.slice()
    .sort((a, b) => {
      const rankA = (a.popularity || 0) * 0.6 + (a.vote_average || 0) * 0.4;
      const rankB = (b.popularity || 0) * 0.6 + (b.vote_average || 0) * 0.4;
      // deterministic pseudo-shuffle per day using id+daySeed
      const jitter = ((a.id * 1103515245 + daySeed) & 0x7fffffff) / 0x7fffffff * 2 - 1;
      return rankB - rankA + jitter * 2;
    })
    .slice(0, count)
    .map(m => ({
      id: m.id, title: m.title, poster_path: m.poster_path,
      vote_average: m.vote_average, genres: m.genres,
      release_date: m.release_date, popularity: m.popularity
    }));
  res.json({ recommendations: picks });
});

// GET /api/movies/:id/recommend   (단수형)
// GET /api/movies/:id/recommendations  (복수형 alias — 인터페이스 계약 경로)
function handleRecommendations(req, res) {
  const movie = MOVIES.find(m => m.id === parseInt(req.params.id));
  if (!movie) return res.status(404).json({ error: '영화를 찾을 수 없습니다' });
  const userId = req.query.userId || null;
  res.json({ recommendations: getRecommendations(movie, 5, userId) });
}
app.get('/api/movies/:id/recommend', handleRecommendations);
app.get('/api/movies/:id/recommendations', handleRecommendations);

// GET /api/movies/:id
app.get('/api/movies/:id', (req, res) => {
  const movie = MOVIES.find(m => m.id === parseInt(req.params.id));
  if (!movie) return res.status(404).json({ error: '영화를 찾을 수 없습니다' });
  const trailer_url = movie.trailer_yt ? `https://www.youtube.com/embed/${movie.trailer_yt}` : null;
  const userId = req.query.userId || null;
  res.json({ ...movie, trailer_url, recommendations: getRecommendations(movie, 5, userId) });
});

// POST /api/auth/register
app.post('/api/auth/register', async (req, res) => {
  const { username, email, password } = req.body || {};
  if (!username || !email || !password)
    return res.status(400).json({ error: '모든 항목을 입력해주세요' });
  if (password.length < 6)
    return res.status(400).json({ error: '비밀번호는 6자 이상이어야 합니다' });
  if (users.find(u => u.email === email))
    return res.status(409).json({ error: '이미 사용 중인 이메일입니다' });
  if (users.find(u => u.username === username))
    return res.status(409).json({ error: '이미 사용 중인 닉네임입니다' });
  const hash = await bcrypt.hash(password, 10);
  const user = { id: Date.now(), username, email, hash, createdAt: new Date().toISOString() };
  users.push(user);
  saveStore('users.json', users);
  const token = jwt.sign({ id: user.id, username: user.username }, JWT_SECRET, { expiresIn: '7d' });
  res.status(201).json({ token, user: { id: user.id, username: user.username, email: user.email } });
});

// POST /api/auth/login
app.post('/api/auth/login', async (req, res) => {
  const { email, password } = req.body || {};
  if (!email || !password) return res.status(400).json({ error: '이메일과 비밀번호를 입력해주세요' });
  const user = users.find(u => u.email === email);
  if (!user || !(await bcrypt.compare(password, user.hash)))
    return res.status(401).json({ error: '이메일 또는 비밀번호가 올바르지 않습니다' });
  const token = jwt.sign({ id: user.id, username: user.username }, JWT_SECRET, { expiresIn: '7d' });
  res.json({ token, user: { id: user.id, username: user.username, email: user.email } });
});

// GET /api/quiz/questions
app.get('/api/quiz/questions', (req, res) => {
  const MODES = ['poster', 'director', 'cast', 'genre', 'year', 'overview'];
  const mode  = MODES.includes(req.query.mode) ? req.query.mode : 'poster';
  const count = Math.min(20, Math.max(1, parseInt(req.query.count) || 10));
  const questions = generateQuiz(mode, count);
  res.json({ mode, count: questions.length, timeLimit: TIME_LIMITS[mode], questions });
});

// Alias routes — /api/quiz/{poster|title|actor}
app.get('/api/quiz/poster', (req, res) => {
  const count = Math.min(20, Math.max(1, parseInt(req.query.count) || 10));
  const questions = generateQuiz('poster', count);
  res.json({ mode: 'poster', count: questions.length, timeLimit: TIME_LIMITS['poster'], questions });
});
app.get('/api/quiz/title', (req, res) => {
  const count = Math.min(20, Math.max(1, parseInt(req.query.count) || 10));
  const questions = generateQuiz('overview', count);
  res.json({ mode: 'title', count: questions.length, timeLimit: TIME_LIMITS['overview'], questions });
});
app.get('/api/quiz/actor', (req, res) => {
  const count = Math.min(20, Math.max(1, parseInt(req.query.count) || 10));
  const questions = generateQuiz('cast', count);
  res.json({ mode: 'actor', count: questions.length, timeLimit: TIME_LIMITS['cast'], questions });
});
app.get('/api/quiz/director', (req, res) => {
  const count = Math.min(20, Math.max(1, parseInt(req.query.count) || 10));
  const questions = generateQuiz('director', count);
  res.json({ mode: 'director', count: questions.length, timeLimit: TIME_LIMITS['director'], questions });
});
app.get('/api/quiz/cast', (req, res) => {
  const count = Math.min(20, Math.max(1, parseInt(req.query.count) || 10));
  const questions = generateQuiz('cast', count);
  res.json({ mode: 'cast', count: questions.length, timeLimit: TIME_LIMITS['cast'], questions });
});

// GET /api/leaderboard
app.get('/api/leaderboard', (req, res) => {
  const mode = req.query.mode;
  let lb = mode && mode !== 'all' ? leaderboard.filter(e => e.mode === mode) : [...leaderboard];
  lb = lb.sort((a, b) => b.score - a.score).slice(0, 100);
  res.json({ leaderboard: lb, total: lb.length });
});

// POST /api/leaderboard
app.post('/api/leaderboard', (req, res) => {
  const { username, score, mode, correct, total, time } = req.body || {};
  if (!username || score == null) return res.status(400).json({ error: '닉네임과 점수가 필요합니다' });
  const entry = {
    id: Date.now(), username, score: +score, mode: mode || 'poster',
    correct: +correct || 0, total: +total || 0,
    time: +time || 0, date: new Date().toISOString()
  };
  leaderboard.push(entry);
  leaderboard.sort((a, b) => b.score - a.score);
  if (leaderboard.length > 500) leaderboard.length = 500;
  saveStore('leaderboard.json', leaderboard);
  const rank = leaderboard.findIndex(e => e.id === entry.id) + 1;
  res.status(201).json({ entry, rank });
});

// Alias /api/game/scores (interface contract)
app.get('/api/game/scores',  (req, res) => {
  const lb = [...leaderboard].sort((a, b) => b.score - a.score).slice(0, 100);
  res.json({ leaderboard: lb, total: lb.length });
});
app.post('/api/game/scores', authRequired, (req, res) => {
  const { score, mode, correct, total, time, movieIds } = req.body || {};
  // username은 JWT 토큰에서 추출 — 파라미터 무시(어뷰징 차단)
  const username = req.user.username;
  if (score == null) return res.status(400).json({ error: '점수가 필요합니다' });
  const entry = { id: Date.now(), username, score: +score, mode: mode || 'poster',
    correct: +correct || 0, total: +total || 0, time: +time || 0, date: new Date().toISOString() };
  leaderboard.push(entry);
  leaderboard.sort((a, b) => b.score - a.score);
  saveStore('leaderboard.json', leaderboard);
  // 개인화: 퀴즈에서 맞춘 영화 ID 배열로 장르 선호도 누적
  if (Array.isArray(movieIds) && movieIds.length > 0) {
    updateUserPrefs(req.user.id, movieIds);
  }
  // 사용자 통계 업데이트
  updateUserStats(req.user.id, { score: +score, correct: +correct||0, total: +total||0, movieIds, mode });
  // 업적 확인
  const stats = getUserStats(String(req.user.id));
  checkAchievements(req.user.id, { score: +score, streak: 0, correct: +correct||0,
    total: +total||0, totalPlays: stats.totalPlays,
    viewCount: (stats.viewHistory||[]).length });
  res.status(201).json({ entry });
});

// GET /api/community/posts
app.get('/api/community/posts', (req, res) => {
  const page  = Math.max(1, parseInt(req.query.page)  || 1);
  const limit = Math.min(30, Math.max(1, parseInt(req.query.limit) || 10));
  const sort  = req.query.sort || 'latest';
  let r = [...posts];
  if (sort === 'likes') r.sort((a, b) => (b.likes || 0) - (a.likes || 0));
  else r.sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt));
  const total = r.length;
  const items = r.slice((page - 1) * limit, (page - 1) * limit + limit)
    .map(p => ({ ...p, commentCount: (p.comments || []).length }));
  res.json({ posts: items, page, limit, total, pages: Math.ceil(total / limit) });
});

// POST /api/community/posts
app.post('/api/community/posts', authRequired, (req, res) => {
  const { title, content, movieId, movieTitle, category } = req.body || {};
  if (!title || !content) return res.status(400).json({ error: '제목과 내용을 입력해주세요' });
  const post = {
    id: Date.now(),
    title: title.trim(), content: content.trim(),
    movieId: movieId || null, movieTitle: movieTitle || null,
    category: category || 'general',
    author: { id: req.user.id, username: req.user.username },
    likes: 0, likedBy: [], comments: [],
    createdAt: new Date().toISOString(), updatedAt: new Date().toISOString()
  };
  posts.unshift(post);
  saveStore('posts.json', posts);
  res.status(201).json({ ...post, commentCount: 0 });
});

// GET /api/community/posts/:id
app.get('/api/community/posts/:id', (req, res) => {
  const post = posts.find(p => p.id === parseInt(req.params.id));
  if (!post) return res.status(404).json({ error: '게시글을 찾을 수 없습니다' });
  res.json(post);
});

// PUT /api/community/posts/:id
app.put('/api/community/posts/:id', authRequired, (req, res) => {
  const idx = posts.findIndex(p => p.id === parseInt(req.params.id));
  if (idx < 0) return res.status(404).json({ error: '게시글을 찾을 수 없습니다' });
  if (posts[idx].author.id !== req.user.id) return res.status(403).json({ error: '권한이 없습니다' });
  const { title, content } = req.body || {};
  posts[idx] = { ...posts[idx],
    title: (title || posts[idx].title).trim(),
    content: (content || posts[idx].content).trim(),
    updatedAt: new Date().toISOString()
  };
  saveStore('posts.json', posts);
  res.json(posts[idx]);
});

// DELETE /api/community/posts/:id
app.delete('/api/community/posts/:id', authRequired, (req, res) => {
  const idx = posts.findIndex(p => p.id === parseInt(req.params.id));
  if (idx < 0) return res.status(404).json({ error: '게시글을 찾을 수 없습니다' });
  if (posts[idx].author.id !== req.user.id) return res.status(403).json({ error: '권한이 없습니다' });
  posts.splice(idx, 1);
  saveStore('posts.json', posts);
  res.status(204).end();
});

// POST /api/community/posts/:id/like
app.post('/api/community/posts/:id/like', authRequired, (req, res) => {
  const post = posts.find(p => p.id === parseInt(req.params.id));
  if (!post) return res.status(404).json({ error: '게시글을 찾을 수 없습니다' });
  const uid  = req.user.id;
  post.likedBy = post.likedBy || [];
  const idx  = post.likedBy.indexOf(uid);
  if (idx >= 0) { post.likedBy.splice(idx, 1); post.likes = Math.max(0, (post.likes || 1) - 1); }
  else          { post.likedBy.push(uid);       post.likes = (post.likes || 0) + 1; }
  saveStore('posts.json', posts);
  res.json({ likes: post.likes, liked: idx < 0 });
});

// POST /api/community/posts/:id/comments
app.post('/api/community/posts/:id/comments', authRequired, (req, res) => {
  const post = posts.find(p => p.id === parseInt(req.params.id));
  if (!post) return res.status(404).json({ error: '게시글을 찾을 수 없습니다' });
  const { content } = req.body || {};
  if (!content) return res.status(400).json({ error: '댓글 내용을 입력해주세요' });
  const comment = {
    id: Date.now(), content: content.trim(),
    author: { id: req.user.id, username: req.user.username },
    createdAt: new Date().toISOString()
  };
  post.comments = post.comments || [];
  post.comments.push(comment);
  saveStore('posts.json', posts);
  res.status(201).json(comment);
});

// Alias /api/posts (interface contract)
app.get('/api/posts',     (req, res) => { req.url = '/api/community/posts'; app.handle(req, res); });
app.post('/api/posts',    authRequired, (req, res) => { req.url = '/api/community/posts'; app.handle(req, res); });
app.post('/api/posts/:id/like',     (req, res) => { req.url = `/api/community/posts/${req.params.id}/like`;     app.handle(req, res); });
app.post('/api/posts/:id/comments', (req, res) => { req.url = `/api/community/posts/${req.params.id}/comments`; app.handle(req, res); });

// ── Quiz Single-Question API (G1, G3) ────────────────────────────────────
// In-memory session store for server-side answer verification (G3)
// { questionId: { correctId, type, movieId, movieTitle, correctLabel, createdAt } }
const quizSessions = new Map();
const QUIZ_SESSION_TTL = 5 * 60 * 1000; // 5분

// 만료 세션 주기적 정리
setInterval(() => {
  const now = Date.now();
  for (const [id, s] of quizSessions) {
    if (now - s.createdAt > QUIZ_SESSION_TTL) quizSessions.delete(id);
  }
}, 60 * 1000);

// GET /api/quiz/question?type=poster|director|cast
// Returns single question: {type, questionId, question, image, movie, choices, timeLimit}
app.get('/api/quiz/question', (req, res) => {
  if (MOVIES.length === 0) return res.status(503).json({ error: '데이터 로드 중입니다' });

  const VALID_TYPES = ['poster', 'director', 'cast'];
  const type = VALID_TYPES.includes(req.query.type) ? req.query.type : 'poster';

  let pool = MOVIES.filter(m => m.poster_path && m.title);
  if (type === 'director') pool = pool.filter(m => m.director);
  if (type === 'cast')     pool = pool.filter(m => m.cast && m.cast.length > 0);

  if (pool.length < 4) return res.status(500).json({ error: '문제 생성에 필요한 영화 데이터가 부족합니다' });

  // 랜덤으로 정답 영화 선택
  const target = pool[Math.floor(Math.random() * pool.length)];
  const others  = shuffle(pool.filter(m => m.id !== target.id));

  let question, image, correctId, correctLabel, choices;

  if (type === 'poster') {
    question    = '이 포스터의 영화 제목은?';
    image       = `https://image.tmdb.org/t/p/w500${target.poster_path}`;
    correctId   = target.id;
    correctLabel = target.title;
    choices = shuffle([target, ...others.slice(0, 3)]).map(m => ({ id: m.id, label: m.title }));

  } else if (type === 'director') {
    const wrongDirectors = [...new Set(
      others.filter(m => m.director && m.director !== target.director).map(m => m.director)
    )].slice(0, 3);
    if (wrongDirectors.length < 3)
      return res.status(500).json({ error: '오답 후보가 부족합니다. 다시 시도해주세요' });

    question    = `"${target.title}"을(를) 연출한 감독은?`;
    image       = `https://image.tmdb.org/t/p/w500${target.poster_path}`;
    correctId   = target.director;
    correctLabel = target.director;
    choices = shuffle([target.director, ...wrongDirectors]).map(d => ({ id: d, label: d }));

  } else { // cast
    const actor = target.cast[0];
    const wrongActors = [...new Set(
      others.flatMap(m => m.cast || []).filter(a => a !== actor)
    )].slice(0, 3);
    if (wrongActors.length < 3)
      return res.status(500).json({ error: '오답 후보가 부족합니다. 다시 시도해주세요' });

    question    = `"${target.title}"의 주연 배우는?`;
    image       = `https://image.tmdb.org/t/p/w500${target.poster_path}`;
    correctId   = actor;
    correctLabel = actor;
    choices = shuffle([actor, ...wrongActors]).map(a => ({ id: a, label: a }));
  }

  // 서버 세션 저장 (G3 — 서버 측 정답 보관)
  const questionId = `${type}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
  quizSessions.set(questionId, {
    correctId, type, movieId: target.id,
    movieTitle: target.title, correctLabel,
    createdAt: Date.now()
  });

  res.json({
    type,
    questionId,
    question,
    image,
    movie: { id: target.id, title: target.title, poster_path: target.poster_path },
    choices,
    timeLimit: TIME_LIMITS[type]
  });
});

// POST /api/quiz/submit (G1, G3)
// Body: { questionId?, movieId, answer, type, timeLeft }
// → { correct, score, explanation, correctAnswer }
app.post('/api/quiz/submit', (req, res) => {
  const { questionId, movieId, answer, type, timeLeft = 0 } = req.body || {};

  // 1차: questionId 세션 기반 검증 (가장 안전)
  if (questionId && quizSessions.has(questionId)) {
    const session = quizSessions.get(questionId);
    // TTL 체크
    if (Date.now() - session.createdAt > QUIZ_SESSION_TTL) {
      quizSessions.delete(questionId);
      return res.status(410).json({ error: '문제 세션이 만료되었습니다. 새 문제를 받아주세요' });
    }

    const correct  = String(answer) === String(session.correctId);
    const tLeft    = Math.max(0, Math.min(parseInt(timeLeft) || 0, TIME_LIMITS[session.type] || 30));
    const score    = correct ? 100 + Math.floor(tLeft * 10) : 0;
    const movie    = MOVIES.find(m => m.id === session.movieId);
    const yearStr  = movie ? ` (${movie.year || (movie.release_date || '').slice(0,4)})` : '';
    const explanation = correct
      ? `정답! 🎉 "${session.movieTitle}"${yearStr}`
      : `오답. 정답은 "${session.correctLabel}"이었습니다.`;

    quizSessions.delete(questionId); // 재제출 방지

    return res.json({
      correct, score, explanation,
      correctAnswer: { id: session.correctId, label: session.correctLabel },
      movie: movie ? { id: movie.id, title: movie.title, poster_path: movie.poster_path } : null
    });
  }

  // 2차: movieId + type 기반 서버 검증 (questionId 없거나 만료 시 fallback)
  if (!movieId || !type) {
    return res.status(400).json({ error: 'questionId 또는 movieId+type이 필요합니다' });
  }

  const movie = MOVIES.find(m => m.id === parseInt(movieId));
  if (!movie) return res.status(404).json({ error: '영화를 찾을 수 없습니다' });

  let serverCorrectId, serverCorrectLabel;
  if (type === 'poster') {
    serverCorrectId    = movie.id;
    serverCorrectLabel = movie.title;
  } else if (type === 'director') {
    serverCorrectId    = movie.director;
    serverCorrectLabel = movie.director;
  } else if (type === 'cast') {
    serverCorrectId    = movie.cast && movie.cast[0];
    serverCorrectLabel = serverCorrectId;
  } else {
    return res.status(400).json({ error: '유효하지 않은 type입니다. poster|director|cast 중 하나여야 합니다' });
  }

  if (!serverCorrectId) return res.status(400).json({ error: '이 영화의 해당 유형 정보가 없습니다' });

  const correct   = String(answer) === String(serverCorrectId);
  const tLeft     = Math.max(0, Math.min(parseInt(timeLeft) || 0, TIME_LIMITS[type] || 30));
  const score     = correct ? 100 + Math.floor(tLeft * 10) : 0;
  const yearStr   = ` (${movie.year || (movie.release_date || '').slice(0,4)})`;
  const explanation = correct
    ? `정답! 🎉 "${movie.title}"${yearStr}`
    : `오답. 정답은 "${serverCorrectLabel}"이었습니다.`;

  res.json({
    correct, score, explanation,
    correctAnswer: { id: serverCorrectId, label: serverCorrectLabel },
    movie: { id: movie.id, title: movie.title, poster_path: movie.poster_path }
  });
});

// POST /api/movies/:id/view  — 조회수 +1, 시청 기록 추가 (업적용)
app.post('/api/movies/:id/view', authOptional, (req, res) => {
  const mid = parseInt(req.params.id);
  const movie = MOVIES.find(m => m.id === mid);
  if (!movie) return res.status(404).json({ error: '영화를 찾을 수 없습니다' });

  viewCounts[mid] = (viewCounts[mid] || 0) + 1;

  if (req.user) {
    const uid   = String(req.user.id);
    const stats = getUserStats(uid);
    const hist  = stats.viewHistory || [];
    if (!hist.includes(mid)) hist.push(mid);
    stats.viewHistory = hist.slice(-500); // 최대 500편
    userStats[uid] = stats;
    saveStore('userStats.json', userStats);
  }

  res.json({ movieId: mid, views: viewCounts[mid] });
});

// ── Daily Challenge ───────────────────────────────────────────────────────
function getDailyDateStr() {
  const d = new Date();
  return `${d.getUTCFullYear()}-${String(d.getUTCMonth()+1).padStart(2,'0')}-${String(d.getUTCDate()).padStart(2,'0')}`;
}

function getDailyQuestions() {
  // 날짜 기반 시드로 동일 10문제 고정 (같은 날 모든 유저 동일)
  const dateStr  = getDailyDateStr();
  const dateSeed = dateStr.split('-').reduce((acc, v) => acc * 100 + parseInt(v), 0);

  const pool = MOVIES.filter(m => m.poster_path && m.title);
  if (pool.length < 40) return [];

  // LCG shuffle — 날짜 기반 결정적
  const lcgShuffle = (arr, seed) => {
    const a = arr.slice();
    let s = seed;
    for (let i = a.length - 1; i > 0; i--) {
      s = (s * 1664525 + 1013904223) & 0x7fffffff;
      const j = s % (i + 1);
      [a[i], a[j]] = [a[j], a[i]];
    }
    return a;
  };

  const shuffled = lcgShuffle(pool, dateSeed);
  const questions = [];
  const MODES = ['poster', 'director', 'cast'];

  for (let i = 0; i < shuffled.length && questions.length < 10; i++) {
    const t    = shuffled[i];
    const mode = MODES[questions.length % 3];

    if (mode === 'director' && !t.director) continue;
    if (mode === 'cast' && (!t.cast || !t.cast.length)) continue;

    const others = lcgShuffle(pool.filter(m => m.id !== t.id), dateSeed + i);

    let q;
    if (mode === 'poster') {
      const choices = lcgShuffle([t, ...others.slice(0, 3)], dateSeed + i * 7);
      q = { type: 'poster', prompt: '이 포스터의 영화 제목은?',
            image: `https://image.tmdb.org/t/p/w500${t.poster_path}`,
            correctId: t.id,
            choices: choices.map(m => ({ id: m.id, label: m.title })),
            timeLimit: 30 };
    } else if (mode === 'director') {
      const dirs = [...new Set(others.filter(m => m.director && m.director !== t.director).map(m => m.director))].slice(0, 3);
      if (dirs.length < 3) continue;
      const choices = lcgShuffle([t.director, ...dirs], dateSeed + i * 11);
      q = { type: 'director', prompt: '이 영화를 연출한 감독은?',
            image: `https://image.tmdb.org/t/p/w500${t.poster_path}`,
            movieTitle: t.title, correctId: t.director,
            choices: choices.map(d => ({ id: d, label: d })),
            timeLimit: 25 };
    } else {
      const actor = t.cast[0];
      const wrongs = [...new Set(others.flatMap(m => m.cast || []).filter(a => a !== actor))].slice(0, 3);
      if (wrongs.length < 3) continue;
      const choices = lcgShuffle([actor, ...wrongs], dateSeed + i * 13);
      q = { type: 'cast', prompt: '이 영화의 주연 배우는?',
            image: `https://image.tmdb.org/t/p/w500${t.poster_path}`,
            movieTitle: t.title, correctId: actor,
            choices: choices.map(a => ({ id: a, label: a })),
            timeLimit: 25 };
    }
    questions.push(q);
  }
  return questions;
}

// GET /api/daily
app.get('/api/daily', (_req, res) => {
  const dateStr   = getDailyDateStr();
  const questions = getDailyQuestions();
  res.json({ date: dateStr, count: questions.length, questions });
});

// POST /api/daily/submit
app.post('/api/daily/submit', authOptional, (req, res) => {
  const { username, score, correct, total, time } = req.body || {};
  if (!username || score == null) return res.status(400).json({ error: '닉네임과 점수가 필요합니다' });

  const dateStr = getDailyDateStr();
  if (!dailyLeaderboard[dateStr]) dailyLeaderboard[dateStr] = [];
  const existing = dailyLeaderboard[dateStr].findIndex(e => e.username === username);
  const entry = { username, score: +score, correct: +correct||0, total: +total||0,
                  time: +time||0, submittedAt: new Date().toISOString() };
  if (existing >= 0) {
    if (entry.score > dailyLeaderboard[dateStr][existing].score)
      dailyLeaderboard[dateStr][existing] = entry; // 최고점만 갱신
  } else {
    dailyLeaderboard[dateStr].push(entry);
  }
  dailyLeaderboard[dateStr].sort((a, b) => b.score - a.score);

  // 사용자 통계 dailyStreak 업데이트
  if (req.user) {
    const uid  = String(req.user.id);
    const s    = getUserStats(uid);
    const yesterday = new Date();
    yesterday.setUTCDate(yesterday.getUTCDate() - 1);
    const yStr = `${yesterday.getUTCFullYear()}-${String(yesterday.getUTCMonth()+1).padStart(2,'0')}-${String(yesterday.getUTCDate()).padStart(2,'0')}`;
    s.dailyStreak = (s.lastDaily === yStr) ? (s.dailyStreak || 0) + 1 : 1;
    s.lastDaily   = dateStr;
    userStats[uid] = s;
    saveStore('userStats.json', userStats);
    if (s.dailyStreak >= 3) checkAchievements(uid, { score: entry.score, streak: 0,
      totalPlays: s.totalPlays, correct: entry.correct, total: entry.total, viewCount: (s.viewHistory||[]).length });
  }

  const rank = dailyLeaderboard[dateStr].findIndex(e => e.username === username) + 1;
  res.status(201).json({ entry, rank, date: dateStr });
});

// GET /api/daily/leaderboard
app.get('/api/daily/leaderboard', (_req, res) => {
  const dateStr = getDailyDateStr();
  const lb = (dailyLeaderboard[dateStr] || []).slice(0, 10);
  res.json({ date: dateStr, leaderboard: lb, total: lb.length });
});

// ── Achievements ──────────────────────────────────────────────────────────

// GET /api/achievements
app.get('/api/achievements', authOptional, (req, res) => {
  if (!req.user) return res.json({ achievements: ACHIEVEMENTS, earned: [] });
  const earned = [...getUserAchievements(req.user.id)];
  res.json({
    achievements: ACHIEVEMENTS,
    earned,
    earnedDetails: earned.map(id => ACHIEVEMENT_MAP[id]).filter(Boolean)
  });
});

// POST /api/achievements/check
app.post('/api/achievements/check', authOptional, (req, res) => {
  const { score, streak, genre, correct, total } = req.body || {};
  if (!req.user) return res.json({ gained: [] });

  const uid    = String(req.user.id);
  const stats  = getUserStats(uid);
  const gained = checkAchievements(uid, {
    score:       +score      || 0,
    streak:      +streak     || 0,
    genre:       genre       || null,
    totalPlays:  stats.totalPlays,
    correct:     +correct    || 0,
    total:       +total      || 0,
    viewCount:   (stats.viewHistory || []).length
  });
  res.json({ gained, total: gained.length });
});

// ── User Stats / Profile ──────────────────────────────────────────────────

// GET /api/users/:id/stats
app.get('/api/users/:id/stats', (req, res) => {
  const uid  = String(req.params.id);
  const s    = userStats[uid];
  if (!s) return res.json({
    userId: uid, totalPlays: 0, totalScore: 0, bestScore: 0,
    correctRate: 0, avgScore: 0, favoriteGenres: [], achievements: []
  });

  const correctRate = s.totalQuestions > 0
    ? parseFloat((s.correctCount / s.totalQuestions * 100).toFixed(1)) : 0;
  const avgScore    = s.totalPlays > 0
    ? parseFloat((s.totalScore / s.totalPlays).toFixed(1)) : 0;

  // 선호 장르 상위 3개
  const favoriteGenres = Object.entries(s.genreCount || {})
    .sort((a, b) => b[1] - a[1])
    .slice(0, 3)
    .map(([gid, cnt]) => ({ id: +gid, name: GENRE_MAP[+gid] || gid, count: cnt }));

  const earned = [...(userAchievements[uid] || new Set())];

  res.json({
    userId: uid, totalPlays: s.totalPlays, totalScore: s.totalScore,
    bestScore: s.bestScore, correctRate, avgScore,
    favoriteGenres, achievements: earned, dailyStreak: s.dailyStreak || 0,
    viewedMovies: (s.viewHistory || []).length
  });
});

// GET /api/recommend/:id  (interface contract alias)
app.get('/api/recommend/:id', (req, res) => {
  const movie = MOVIES.find(m => m.id === parseInt(req.params.id));
  if (!movie) return res.status(404).json({ error: '영화를 찾을 수 없습니다' });
  res.json({ recommendations: getRecommendations(movie, 5) });
});

// Health check
app.get('/api/health', (_req, res) => res.json({ status: 'ok', movies: MOVIES.length, genres: GENRES.length }));

// ── API 미매칭 경로 → 404 JSON (정적 경로보다 먼저) ────────────────────────
app.use('/api', (_req, res) => res.status(404).json({ error: 'Not Found' }));

// ── 정적 파일 서빙 + SPA 폴백 ─────────────────────────────────────────────
// Render Static Site가 정상 동작할 때는 여기까지 오지 않음.
// organt-p-031 이 Web Service로 배포된 경우(현 실제 상황)를 위한 안전망.
app.use(express.static(path.join(__dirname, 'public')));
app.get('*', (_req, res) => {
  res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

// ── Boot ──────────────────────────────────────────────────────────────────
if (!fs.existsSync(SERVER_DATA)) fs.mkdirSync(SERVER_DATA, { recursive: true });

// 포트 바인딩 전에 데이터 로드 → 초기 요청에서도 즉시 응답 가능
loadStaticData();

app.listen(PORT, () => {
  console.log(`🎬 CineAI on http://localhost:${PORT}  [${MOVIES.length} movies]`);

  // Render free tier keep-alive (RENDER_EXTERNAL_URL은 Render가 자동 주입)
  if (process.env.RENDER_EXTERNAL_URL) {
    const https = require('https');
    const _ping = () => {
      https.get(`${process.env.RENDER_EXTERNAL_URL}/api/health`, r => r.resume())
        .on('error', () => setTimeout(_ping, 30 * 1000)); // 실패 시 30초 후 재시도
    };
    setTimeout(_ping, 5 * 1000);             // 5초 후 첫 ping (cold-start 즉시 워밍)
    setInterval(_ping, 5 * 60 * 1000);      // 이후 5분 간격 (Render 15분 슬립 기준 여유 10분)
    console.log(`⏰ Keep-alive 활성화(5분 간격): ${process.env.RENDER_EXTERNAL_URL}`);
  }
});
