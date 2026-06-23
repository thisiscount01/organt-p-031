// ─── Hash Router ─────────────────────────────────────────────────────────────
const AppRouter = Vue.reactive({ path: '/', params: {}, query: {} });

function parseRoute() {
  const hash = location.hash.replace(/^#/, '') || '/';
  const [pathStr, qs] = hash.split('?');
  const segs = pathStr.split('/').filter(Boolean);
  AppRouter.query = qs ? Object.fromEntries(new URLSearchParams(qs)) : {};
  if (!segs.length)                          { AppRouter.path = '/';              AppRouter.params = {}; }
  else if (segs[0] === 'movie'  && segs[1]) { AppRouter.path = '/movie';         AppRouter.params = { id: segs[1] }; }
  else if (segs[0] === 'quiz')               { AppRouter.path = '/quiz';          AppRouter.params = {}; }
  else if (segs[0] === 'community' && segs[1]) { AppRouter.path = '/community/post'; AppRouter.params = { id: segs[1] }; }
  else if (segs[0] === 'community')          { AppRouter.path = '/community';     AppRouter.params = {}; }
  else if (segs[0] === 'leaderboard')        { AppRouter.path = '/leaderboard';   AppRouter.params = {}; }
  else if (segs[0] === 'auth')               { AppRouter.path = '/auth';          AppRouter.params = {}; }
  // /movies/:id — 직접 URL 접근·새로고침·공유 링크 지원
  else if (segs[0] === 'movies' && segs[1]) { AppRouter.path = '/movie';          AppRouter.params = { id: segs[1] }; }
  else if (segs[0] === 'movies')             { AppRouter.path = '/movies';        AppRouter.params = {}; }
  else                                       { AppRouter.path = '/';              AppRouter.params = {}; }
}
window.addEventListener('hashchange', parseRoute);
parseRoute();

function nav(path) { location.hash = path; }

// ─── Toast ───────────────────────────────────────────────────────────────────
const ToastState = Vue.reactive({ msg: '', type: 'info', show: false });
let _toastTimer = null;
function showToast(msg, type = 'info') {
  clearTimeout(_toastTimer);
  ToastState.msg = msg; ToastState.type = type; ToastState.show = true;
  _toastTimer = setTimeout(() => { ToastState.show = false; }, 2800);
}

const ToastComp = {
  template: `<transition name="toast-fade">
    <div v-if="t.show" :class="['toast', t.type]" style="cursor:pointer" @click="t.show=false">
      <i :class="icon"></i> {{ t.msg }}
    </div>
  </transition>`,
  setup() {
    const t = ToastState;
    const icon = Vue.computed(() =>
      t.type === 'success' ? 'fa-solid fa-check-circle' :
      t.type === 'error'   ? 'fa-solid fa-circle-xmark' : 'fa-solid fa-circle-info'
    );
    return { t, icon };
  }
};

// ─── StarRating ──────────────────────────────────────────────────────────────
const StarRating = {
  props: { rating: Number, size: { default: 'md' } },
  template: `<span class="star-rating">
    <span v-for="i in 5" :key="i" class="star"
      :class="rating>=i?'full':rating>=i-0.5?'half':'empty'">★</span>
    <span class="rating-label">{{ rating?.toFixed(1) }}</span>
  </span>`
};

// ─── MovieCard ───────────────────────────────────────────────────────────────
const MovieCard = {
  props: { movie: Object, showRec: Boolean },
  emits: ['click'],
  template: `
  <div class="movie-card" @click="$emit('click', movie)">
    <div class="card-poster">
      <img :src="poster" :alt="movie.title" loading="lazy"
           @error="e => e.target.src='https://placehold.co/300x450/1a1a28/f0b429?text=No+Image'" />
      <div class="card-overlay">
        <div class="overlay-rating"><i class="fa-solid fa-star"></i> {{ movie.vote_average?.toFixed(1) }}</div>
        <button class="overlay-detail">자세히 보기</button>
        <button class="overlay-fav" :class="{ active: isFav }" @click.stop="toggleFav" :title="isFav?'즐겨찾기 해제':'즐겨찾기'">
          <i :class="isFav?'fa-solid fa-heart':'fa-regular fa-heart'"></i>
        </button>
      </div>
    </div>
    <div class="card-info">
      <div class="card-title">{{ movie.title }}</div>
      <div class="card-meta">
        <span class="card-year">{{ movie.year || movie.release_date?.slice(0,4) }}</span>
        <span class="card-genres" v-if="genreLabel">· {{ genreLabel }}</span>
        <span v-if="showRec && movie.score" class="badge bg-warning text-dark ms-auto" style="font-size:.7rem">
          {{ Math.round(movie.score*100) }}%
        </span>
      </div>
    </div>
  </div>`,
  setup(props) {
    const poster    = Vue.computed(() => CineStore.getPosterUrl(props.movie.poster_path));
    const isFav     = Vue.computed(() => CineStore.isFavorite(props.movie.id));
    const genreLabel= Vue.computed(() => {
      const g = (props.movie.genres || []).slice(0, 2).map(id => CineStore.genreMap[id]).filter(Boolean);
      return g.join(' · ');
    });
    const toggleFav = () => CineStore.toggleFavorite(props.movie.id);
    return { poster, isFav, genreLabel, toggleFav };
  }
};

// ─── NavBar ──────────────────────────────────────────────────────────────────
const NavBar = {
  template: `
  <nav class="navbar">
    <a class="nav-logo" href="#/"><span class="logo-cine">Cine</span><span class="logo-ai">AI</span></a>
    <ul class="nav-links">
      <li><a href="#/" :class="{active: r.path==='/'}"><i class="fa-solid fa-house"></i> 홈</a></li>
      <li><a href="#/movies" :class="{active: r.path==='/movies'}"><i class="fa-solid fa-film"></i> 영화</a></li>
      <li><a href="#/quiz" :class="{active: r.path==='/quiz'}"><i class="fa-solid fa-gamepad"></i> 퀴즈</a></li>
      <li><a href="#/community" :class="{active: r.path.startsWith('/community')}"><i class="fa-solid fa-users"></i> 커뮤니티</a></li>
      <li><a href="#/leaderboard" :class="{active: r.path==='/leaderboard'}"><i class="fa-solid fa-trophy"></i> 랭킹</a></li>
    </ul>
    <div class="d-flex align-items-center gap-2">
      <template v-if="store.user">
        <span class="text-gold fw-bold" style="font-size:.85rem">{{ store.user.username }}</span>
        <button class="btn-secondary" style="padding:.4rem .9rem;font-size:.82rem" @click="logout">로그아웃</button>
      </template>
      <template v-else>
        <a href="#/auth" class="btn-primary" style="padding:.45rem 1rem;font-size:.85rem">로그인</a>
      </template>
    </div>
  </nav>`,
  setup() {
    const r = AppRouter;
    const store = CineStore;
    function logout() { store.logout(); showToast('로그아웃 됐습니다', 'info'); }
    return { r, store, logout };
  }
};

// ─── HomePage ────────────────────────────────────────────────────────────────
const HomePage = {
  template: `
  <div class="page fade-in">
    <!-- Hero Carousel -->
    <div class="hero-wrap" v-if="heroes.length">
      <div class="hero-track" :style="{ transform: \`translateX(-\${heroIdx*100}%)\` }">
        <div class="hero-slide" v-for="m in heroes" :key="m.id">
          <div class="hero-backdrop" :style="backdropStyle(m)"></div>
          <div class="hero-overlay"></div>
          <div class="hero-content">
            <div class="hero-badge"><i class="fa-solid fa-star"></i> 추천 영화</div>
            <h1 class="hero-title">{{ m.title }}</h1>
            <div class="hero-genres">
              <span class="genre-tag" v-for="gid in (m.genres||[]).slice(0,3)" :key="gid">{{ store.genreMap[gid] }}</span>
            </div>
            <div class="hero-meta">
              <span class="hero-rating"><i class="fa-solid fa-star"></i> {{ m.vote_average?.toFixed(1) }}</span>
              <span>{{ m.year || m.release_date?.slice(0,4) }}</span>
              <span v-if="m.director"><i class="fa-solid fa-video"></i> {{ m.director }}</span>
            </div>
            <p class="hero-overview">{{ m.overview }}</p>
            <div class="hero-actions">
              <button class="btn-primary" @click="goDetail(m)"><i class="fa-solid fa-play"></i> 상세보기</button>
              <button class="btn-secondary" @click="nav('#/quiz')"><i class="fa-solid fa-gamepad"></i> 퀴즈 도전</button>
            </div>
          </div>
        </div>
      </div>
      <button class="carousel-prev" @click="prevHero"><i class="fa-solid fa-chevron-left"></i></button>
      <button class="carousel-next" @click="nextHero"><i class="fa-solid fa-chevron-right"></i></button>
      <div class="carousel-dots">
        <button v-for="(_, i) in heroes" :key="i" :class="['carousel-dot', {active: i===heroIdx}]" @click="heroIdx=i"></button>
      </div>
    </div>

    <!-- Popular Section -->
    <div class="section">
      <div class="section-header">
        <h2 class="section-title"><i class="fa-solid fa-fire"></i> 인기 영화</h2>
        <button class="see-all" @click="nav('#/movies')">전체보기 →</button>
      </div>
      <div class="card-grid">
        <MovieCard v-for="m in popular" :key="m.id" :movie="m" @click="goDetail" />
      </div>
    </div>

    <!-- Genre Picks -->
    <div class="section" style="padding-top:0">
      <div class="section-header">
        <h2 class="section-title"><i class="fa-solid fa-masks-theater"></i> 장르별 추천</h2>
      </div>
      <div class="genre-tabs mb-3">
        <button v-for="g in topGenres" :key="g.id"
          :class="['genre-tab', {active: activeGenre===g.id}]"
          @click="activeGenre=g.id">{{ g.name }}</button>
      </div>
      <div class="card-grid">
        <MovieCard v-for="m in genreMovies" :key="m.id" :movie="m" @click="goDetail" />
      </div>
    </div>

    <!-- AI Rec Banner -->
    <div class="section" style="padding-top:0">
      <div class="section-header">
        <h2 class="section-title"><i class="fa-solid fa-robot"></i> AI 큐레이션</h2>
      </div>
      <div class="ai-recs-row" style="overflow-x:auto;padding-bottom:.5rem">
        <MovieCard v-for="m in aiRecs" :key="m.id" :movie="m" :showRec="true" @click="goDetail" />
      </div>
    </div>
  </div>`,
  components: { MovieCard },
  setup() {
    const store = CineStore;
    const heroIdx = Vue.ref(0);
    const activeGenre = Vue.ref(28); // Action
    let heroTimer = null;

    const heroes  = Vue.computed(() => store.getTopMovies(5).filter(m => m.poster_path));
    const popular = Vue.computed(() => store.getTopMovies(12));
    const topGenres = Vue.computed(() => store.genres.slice(0, 8));
    const genreMovies = Vue.computed(() => store.getMoviesByGenre(activeGenre.value, 12));
    const aiRecs  = Vue.computed(() => store.getRecommendations({ mood: 'action', count: 8 }));

    function backdropStyle(m) {
      const u = m.backdrop_path ? store.getBackdropUrl(m.backdrop_path)
              : store.getPosterUrl(m.poster_path, 'w1280');
      return { backgroundImage: `url(${u})` };
    }
    function goDetail(m) { nav(`#/movie/${m.id}`); }
    function nextHero() { heroIdx.value = (heroIdx.value + 1) % (heroes.value.length || 1); }
    function prevHero() { heroIdx.value = (heroIdx.value - 1 + (heroes.value.length || 1)) % (heroes.value.length || 1); }

    Vue.onMounted(() => { heroTimer = setInterval(nextHero, 5000); });
    Vue.onUnmounted(() => clearInterval(heroTimer));
    return { store, heroIdx, heroes, popular, topGenres, activeGenre, genreMovies, aiRecs, backdropStyle, goDetail, nextHero, prevHero, nav };
  }
};

// ─── MoviesPage ──────────────────────────────────────────────────────────────
const MoviesPage = {
  template: `
  <div class="page fade-in">
    <div class="movies-header">
      <h1>🎬 영화 전체 목록</h1>
      <div class="search-bar"><i class="fa-solid fa-search"></i>
        <input v-model="q" placeholder="제목, 감독으로 검색..." @input="onSearch" />
      </div>
      <div class="genre-tabs">
        <button :class="['genre-tab',{active:!genre}]" @click="genre=null;load()">전체</button>
        <button v-for="g in store.genres" :key="g.id"
          :class="['genre-tab',{active:genre===g.id}]" @click="genre=g.id;load()">{{ g.name }}</button>
      </div>
    </div>
    <div class="movies-grid-wrap">
      <div class="movies-count" v-if="total">총 {{ total }}편 ({{ page }}/{{ pages }}페이지)</div>
      <div class="card-grid">
        <MovieCard v-for="m in movies" :key="m.id" :movie="m" @click="m=>nav('#/movie/'+m.id)" />
      </div>
      <div class="empty-state" v-if="!movies.length && !loading">
        <div class="empty-icon"><i class="fa-solid fa-film"></i></div>
        <div class="empty-title">검색 결과가 없어요</div>
        <div class="empty-sub">다른 키워드로 검색해보세요</div>
      </div>
      <div class="pagination" v-if="pages > 1">
        <button class="pg-btn" :disabled="page<=1" @click="changePage(page-1)"><i class="fa-solid fa-chevron-left"></i></button>
        <button v-for="p in pageNums" :key="p" :class="['pg-btn',{active:p===page}]" @click="changePage(p)">{{ p }}</button>
        <button class="pg-btn" :disabled="page>=pages" @click="changePage(page+1)"><i class="fa-solid fa-chevron-right"></i></button>
      </div>
    </div>
  </div>`,
  components: { MovieCard },
  setup() {
    const store = CineStore;
    const q = Vue.ref(''), genre = Vue.ref(null), page = Vue.ref(1), pages = Vue.ref(1), total = Vue.ref(0);
    const movies = Vue.ref([]), loading = Vue.ref(false);
    let _st = null;

    async function load() {
      loading.value = true;
      try {
        const url = q.value
          ? `/api/movies/search?q=${encodeURIComponent(q.value)}&genre=${genre.value||''}&page=${page.value}&limit=24`
          : `/api/movies?genre=${genre.value||''}&page=${page.value}&limit=24`;
        const d = await store.apiGet(url);
        movies.value = d.results; pages.value = d.pages; total.value = d.total;
      } catch(e) { showToast(e.message, 'error'); }
      loading.value = false;
    }
    function onSearch() {
      clearTimeout(_st); page.value = 1;
      _st = setTimeout(load, 350);
    }
    function changePage(p) { page.value = p; load(); window.scrollTo(0,0); }
    const pageNums = Vue.computed(() => {
      const r = [], total = pages.value, cur = page.value;
      const s = Math.max(1, cur-2), e = Math.min(total, s+4);
      for (let i = s; i <= e; i++) r.push(i);
      return r;
    });
    Vue.onMounted(load);
    return { store, q, genre, page, pages, total, movies, loading, onSearch, changePage, pageNums, nav };
  }
};

// ─── MovieDetailPage ─────────────────────────────────────────────────────────
const MovieDetailPage = {
  template: `
  <div class="page fade-in" v-if="movie">
    <!-- Backdrop Hero -->
    <div class="detail-hero">
      <div class="detail-backdrop" :style="backdropStyle"></div>
      <div class="detail-hero-overlay"></div>
      <div class="detail-hero-content">
        <div class="detail-poster-wrap">
          <img :src="store.getPosterUrl(movie.poster_path)" :alt="movie.title" />
        </div>
        <div class="detail-hero-info">
          <h1 class="detail-title">{{ movie.title }}</h1>
          <p class="detail-orig" v-if="movie.original_title !== movie.title">{{ movie.original_title }}</p>
          <div class="detail-tags">
            <span class="genre-tag" v-for="gid in (movie.genres||[])" :key="gid">{{ store.genreMap[gid] }}</span>
          </div>
          <div class="detail-meta">
            <span><i class="fa-solid fa-star"></i>{{ movie.vote_average?.toFixed(1) }} ({{ movie.vote_count?.toLocaleString() }}표)</span>
            <span v-if="movie.release_date"><i class="fa-regular fa-calendar"></i>{{ movie.year || movie.release_date?.slice(0,4) }}</span>
            <span v-if="movie.director"><i class="fa-solid fa-video"></i>{{ movie.director }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Body -->
    <div class="detail-body">
      <div class="detail-cols">
        <div>
          <h3 class="detail-overview-title">줄거리</h3>
          <p class="detail-overview-text">{{ movie.overview }}</p>

          <!-- Cast -->
          <div class="mt-4" v-if="movie.cast && movie.cast.length">
            <h4 style="font-size:1rem;font-weight:700;margin-bottom:.75rem">출연진</h4>
            <div class="d-flex gap-2 flex-wrap">
              <span class="badge rounded-pill bg-secondary" style="font-size:.85rem;padding:.45rem .9rem"
                v-for="a in movie.cast" :key="a">{{ a }}</span>
            </div>
          </div>

          <!-- YouTube Trailer -->
          <div class="mt-4" v-if="movie.trailer_yt">
            <h4 style="font-size:1rem;font-weight:700;margin-bottom:.75rem"><i class="fa-brands fa-youtube text-danger"></i> 예고편</h4>
            <div style="position:relative;padding-bottom:56.25%;border-radius:12px;overflow:hidden;background:#000">
              <iframe :src="'https://www.youtube.com/embed/'+movie.trailer_yt+'?rel=0&modestbranding=1'"
                allowfullscreen frameborder="0"
                style="position:absolute;inset:0;width:100%;height:100%"></iframe>
            </div>
          </div>

          <!-- Review Form -->
          <div class="reviews-section mt-4">
            <h4 style="font-size:1rem;font-weight:700;margin-bottom:1rem">리뷰 작성</h4>
            <div class="review-form-wrap">
              <div class="form-row">
                <div class="form-field">
                  <label>닉네임</label>
                  <input v-model="rv.author" placeholder="닉네임" />
                </div>
                <div class="form-field">
                  <label>평점</label>
                  <div class="star-picker">
                    <button v-for="s in 5" :key="s" :class="{active: rv.rating >= s}" @click="rv.rating=s">★</button>
                  </div>
                </div>
              </div>
              <div class="form-field">
                <label>리뷰</label>
                <textarea v-model="rv.body" placeholder="이 영화에 대한 감상을 남겨주세요..."></textarea>
              </div>
              <button class="btn-primary mt-2" @click="submitReview" :disabled="!rv.author||!rv.body">
                <i class="fa-solid fa-paper-plane"></i> 리뷰 등록
              </button>
            </div>
            <div v-for="r in reviews" :key="r.id" class="review-card">
              <div class="review-header">
                <div>
                  <div class="reviewer-name">{{ r.author }}</div>
                  <div class="star-rating">
                    <span v-for="s in 5" :key="s" class="star" :class="r.rating>=s?'full':'empty'">★</span>
                  </div>
                </div>
                <span class="review-date">{{ fmtDate(r.createdAt) }}</span>
              </div>
              <p class="review-body">{{ r.body }}</p>
            </div>
          </div>
        </div>

        <!-- Sidebar -->
        <div>
          <div class="detail-stats">
            <div class="stat-row"><span class="stat-label">평점</span><span class="stat-value gold">★ {{ movie.vote_average?.toFixed(1) }}</span></div>
            <div class="stat-row" v-if="movie.vote_count"><span class="stat-label">투표수</span><span class="stat-value">{{ movie.vote_count?.toLocaleString() }}</span></div>
            <div class="stat-row" v-if="movie.release_date"><span class="stat-label">개봉일</span><span class="stat-value">{{ movie.release_date }}</span></div>
            <div class="stat-row" v-if="movie.director"><span class="stat-label">감독</span><span class="stat-value">{{ movie.director }}</span></div>
            <div class="stat-row">
              <span class="stat-label">즐겨찾기</span>
              <button @click="store.toggleFavorite(movie.id)"
                :style="{ color: store.isFavorite(movie.id) ? 'var(--red)' : 'var(--text2)' }">
                <i :class="store.isFavorite(movie.id)?'fa-solid fa-heart':'fa-regular fa-heart'"></i>
                {{ store.isFavorite(movie.id) ? '저장됨' : '저장하기' }}
              </button>
            </div>
            <button class="btn-primary w-100 mt-2" @click="nav('#/quiz')">
              <i class="fa-solid fa-gamepad"></i> 퀴즈 도전
            </button>
          </div>
        </div>
      </div>

      <!-- AI Recommendations -->
      <div class="similar-section mt-4" v-if="movie.recommendations && movie.recommendations.length">
        <h3 class="section-title"><i class="fa-solid fa-robot"></i> AI 연관 추천 영화</h3>
        <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:1rem;margin-top:1rem">
          <MovieCard v-for="r in movie.recommendations" :key="r.id" :movie="r" :showRec="true"
            @click="m => nav('#/movie/'+m.id)" />
        </div>
      </div>
    </div>
  </div>
  <div class="empty-state" v-else-if="notFound">
    <div class="empty-icon"><i class="fa-solid fa-circle-exclamation"></i></div>
    <div class="empty-title">영화를 찾을 수 없어요</div>
    <button class="btn-secondary mt-3" @click="nav('#/')">홈으로</button>
  </div>
  <div class="empty-state" v-else>
    <div class="empty-icon"><i class="fa-solid fa-spinner fa-spin"></i></div>
    <div class="empty-title">불러오는 중...</div>
  </div>`,
  components: { MovieCard, StarRating },
  setup() {
    const store = CineStore;
    const movie = Vue.ref(null), notFound = Vue.ref(false);
    const rv = Vue.reactive({ author: store.user?.username || '', rating: 5, body: '' });
    const reviews = Vue.computed(() => store.getReviews(AppRouter.params.id));
    const backdropStyle = Vue.computed(() => {
      if (!movie.value) return {};
      const u = movie.value.backdrop_path
        ? store.getBackdropUrl(movie.value.backdrop_path)
        : store.getPosterUrl(movie.value.poster_path, 'w1280');
      return { backgroundImage: `url(${u})` };
    });
    async function load() {
      movie.value = null; notFound.value = false;
      try {
        const d = await store.apiGet(`/api/movies/${AppRouter.params.id}`);
        movie.value = d;
      } catch(e) { notFound.value = true; }
    }
    function submitReview() {
      if (!rv.author || !rv.body) return;
      store.addReview({ movieId: parseInt(AppRouter.params.id), author: rv.author, rating: rv.rating, body: rv.body });
      rv.body = ''; showToast('리뷰가 등록됐습니다!', 'success');
    }
    function fmtDate(d) { return new Date(d).toLocaleDateString('ko-KR'); }
    Vue.onMounted(load);
    Vue.watch(() => AppRouter.params.id, load);
    return { store, movie, notFound, backdropStyle, rv, reviews, submitReview, fmtDate, nav };
  }
};

// ─── QuizPage ────────────────────────────────────────────────────────────────
const MODES = [
  { key: 'poster',   icon: '🎬', title: '포스터 → 제목',   desc: '포스터를 보고 영화 제목을 맞춰요',     time: 30 },
  { key: 'director', icon: '🎥', title: '포스터 → 감독',   desc: '포스터를 보고 감독 이름을 맞춰요',     time: 25 },
  { key: 'cast',     icon: '⭐', title: '포스터 → 배우',   desc: '포스터를 보고 주연 배우를 맞춰요',     time: 25 },
  { key: 'genre',    icon: '🎭', title: '장르 맞추기',     desc: '영화 제목으로 주요 장르를 맞춰요',     time: 20 },
  { key: 'year',     icon: '📅', title: '개봉년도 맞추기', desc: '영화 포스터로 개봉 연도를 맞춰요',     time: 15 },
  { key: 'overview', icon: '📖', title: '줄거리 → 제목',   desc: '줄거리 힌트로 영화 제목을 맞춰요',    time: 28 },
];

const QuizPage = {
  template: `
  <div class="quiz-page">

    <!-- SELECT SCREEN -->
    <div class="quiz-select-screen" v-if="screen==='select'">
      <div class="quiz-logo-big">🎮</div>
      <h2 class="quiz-select-title">CineAI 퀴즈</h2>
      <p class="quiz-select-sub">영화 지식을 겨뤄봐요! 모드를 선택하고 도전하세요.</p>
      <div class="mode-grid">
        <div v-for="m in modes" :key="m.key"
          :class="['mode-card', {active: selectedMode===m.key}]"
          @click="selectedMode=m.key">
          <div class="mode-icon">{{ m.icon }}</div>
          <div class="mode-title">{{ m.title }}</div>
          <p class="mode-desc">{{ m.desc }}</p>
          <div class="mode-time"><i class="fa-regular fa-clock"></i> {{ m.time }}초 제한</div>
        </div>
      </div>
      <div class="d-flex align-items-center gap-3 mb-4">
        <span class="text-secondary">문제 수:</span>
        <select v-model.number="qCount" class="form-select" style="width:100px;background:var(--bg-card);color:var(--text);border-color:var(--border2)">
          <option :value="5">5문제</option>
          <option :value="10">10문제</option>
          <option :value="15">15문제</option>
          <option :value="20">20문제</option>
        </select>
        <span class="text-secondary">생명:</span>
        <select v-model.number="startLives" class="form-select" style="width:90px;background:var(--bg-card);color:var(--text);border-color:var(--border2)">
          <option :value="3">❤️❤️❤️</option>
          <option :value="5">❤️❤️❤️❤️❤️</option>
          <option :value="99">무한</option>
        </select>
      </div>
      <button class="btn-start" @click="startQuiz" :disabled="loading">
        <i class="fa-solid fa-play"></i> {{ loading ? '불러오는 중...' : '게임 시작!' }}
      </button>
    </div>

    <!-- GAME SCREEN -->
    <div class="quiz-game-screen" v-else-if="screen==='game' && q">
      <!-- HUD -->
      <div class="quiz-hud">
        <div class="hud-stat">
          <span class="hud-label">점수</span>
          <span class="hud-value gold">{{ score }}</span>
        </div>
        <div class="hud-divider"></div>
        <div class="hud-stat">
          <span class="hud-label">생명</span>
          <span class="hud-value red">{{ '❤️'.repeat(lives) }}{{ lives===99?'∞':'' }}</span>
        </div>
        <div class="hud-divider"></div>
        <div class="hud-stat">
          <span class="hud-label">연속</span>
          <span class="hud-value green">🔥 x{{ streak }}</span>
        </div>
        <div class="hud-divider"></div>
        <div class="hud-stat">
          <span class="hud-label">진도</span>
          <span class="hud-value">{{ qIdx+1 }}/{{ questions.length }}</span>
        </div>
        <div class="hud-progress ms-auto">
          <div class="hud-progress-fill" :style="{width: ((qIdx+1)/questions.length*100)+'%'}"></div>
        </div>
      </div>

      <!-- Timer Bar -->
      <div class="quiz-timer-bar">
        <div class="quiz-timer-fill"
          :style="{ width: (timeLeft/q.timeLimit*100)+'%',
            background: timeLeft/q.timeLimit > 0.5 ? 'var(--green)' : timeLeft/q.timeLimit > 0.25 ? 'var(--gold)' : 'var(--red)' }"></div>
      </div>

      <!-- Question Card -->
      <div class="quiz-question-card">
        <div class="quiz-q-type">{{ modeLabel }} · {{ timeLeft }}초</div>
        <div class="quiz-q-prompt">{{ q.prompt }}</div>
        <div class="quiz-img-wrap" v-if="q.image">
          <img :src="q.image" :alt="q.movieTitle||''" loading="lazy"
               @error="e => e.target.style.display='none'" />
        </div>
        <div class="quiz-snippet" v-if="q.snippet">{{ q.snippet }}</div>
        <div class="quiz-choices">
          <button v-for="(c, ci) in q.choices" :key="c.id"
            :class="['quiz-choice', choiceClass(c)]"
            :disabled="answered"
            @click="answer(c)">
            <span class="choice-letter">{{ 'ABCD'[ci] }}</span>
            {{ c.label }}
          </button>
        </div>
        <div v-if="answered" :class="['quiz-feedback', isCorrect?'correct-fb':'wrong-fb']">
          {{ isCorrect ? '🎉 정답! +' + lastPoints + '점' : '😢 오답! 정답: ' + correctLabel }}
        </div>
      </div>
    </div>

    <!-- RESULT SCREEN -->
    <div class="quiz-result-screen" v-else-if="screen==='result'">
      <div class="result-trophy">{{ grade.trophy }}</div>
      <h2 class="result-title">{{ grade.label }}</h2>
      <div class="result-score">{{ score }}점</div>
      <p class="result-sub">{{ grade.grade }}등급 · {{ correct }}/{{ questions.length }} 정답</p>
      <div class="result-stats">
        <div class="result-stat"><div class="result-stat-val" style="color:var(--green)">{{ correct }}</div><div class="result-stat-label">정답</div></div>
        <div class="result-stat"><div class="result-stat-val" style="color:var(--red)">{{ questions.length-correct }}</div><div class="result-stat-label">오답</div></div>
        <div class="result-stat"><div class="result-stat-val" style="color:var(--gold)">{{ maxStreak }}</div><div class="result-stat-label">최고 연속</div></div>
      </div>

      <!-- Leaderboard Register -->
      <div class="leaderboard-register">
        <div class="lb-reg-title">🏆 랭킹 등록</div>
        <div class="lb-reg-form">
          <input v-model="lbName" :placeholder="store.user?.username||'닉네임 입력'" />
          <button class="btn-primary" @click="registerScore" :disabled="lbDone">
            {{ lbDone ? '등록 완료!' : '등록하기' }}
          </button>
        </div>
        <div v-if="lbRank" class="mt-2 text-center" style="color:var(--gold);font-weight:700">
          🎖️ 전체 {{ lbRank }}위 달성!
        </div>
      </div>

      <!-- Local Leaderboard -->
      <div class="leaderboard-wrap">
        <div class="lb-title">이번 모드 TOP 10</div>
        <div v-for="(e, i) in localLb" :key="e.id" :class="['lb-row', {' my-row': e._isMe}]">
          <span :class="['lb-rank', i===0?'gold-rank':i===1?'silver-rank':i===2?'bronze-rank':'']">
            {{ i===0?'🥇':i===1?'🥈':i===2?'🥉':i+1 }}
          </span>
          <span class="lb-name">{{ e.username }}<span class="lb-mode">{{ e.mode }}</span></span>
          <span class="lb-score">{{ e.score?.toLocaleString() }}</span>
        </div>
      </div>

      <div class="quiz-result-btns">
        <button class="btn-primary" @click="restart"><i class="fa-solid fa-rotate-right"></i> 다시 도전</button>
        <button class="btn-secondary" @click="nav('#/')"><i class="fa-solid fa-house"></i> 홈으로</button>
        <button class="btn-secondary" @click="nav('#/leaderboard')"><i class="fa-solid fa-trophy"></i> 전체 랭킹</button>
      </div>
    </div>
  </div>`,
  setup() {
    const store = CineStore;
    const screen = Vue.ref('select'), selectedMode = Vue.ref('poster');
    const qCount = Vue.ref(10), startLives = Vue.ref(3);
    const questions = Vue.ref([]), qIdx = Vue.ref(0), score = Vue.ref(0);
    const correctMovieIds = Vue.ref([]);
    const lives = Vue.ref(3), streak = Vue.ref(0), maxStreak = Vue.ref(0), correct = Vue.ref(0);
    const timeLeft = Vue.ref(30), answered = Vue.ref(false), isCorrect = Vue.ref(false);
    const lastPoints = Vue.ref(0), correctLabel = Vue.ref('');
    const lbName = Vue.ref(''), lbDone = Vue.ref(false), lbRank = Vue.ref(null);
    const localLb = Vue.ref([]), loading = Vue.ref(false);
    let timer = null;

    const q = Vue.computed(() => questions.value[qIdx.value]);
    const modeLabel = Vue.computed(() => MODES.find(m => m.key === selectedMode.value)?.title || '');
    const grade = Vue.computed(() => QuizEngine.gradeResult(score.value, questions.value.length));
    const modes = MODES;

    async function startQuiz() {
      loading.value = true;
      try {
        const d = await store.apiGet(`/api/quiz/questions?mode=${selectedMode.value}&count=${qCount.value}`);
        questions.value = d.questions;
      } catch(e) {
        questions.value = store.generateQuestions(selectedMode.value, qCount.value);
      }
      qIdx.value = 0; score.value = 0; lives.value = startLives.value;
      streak.value = 0; maxStreak.value = 0; correct.value = 0;
      correctMovieIds.value = [];
      answered.value = false; lbDone.value = false; lbRank.value = null;
      screen.value = 'game'; loading.value = false;
      startTimer();
    }

    function startTimer() {
      clearInterval(timer);
      timeLeft.value = q.value?.timeLimit || 20;
      timer = setInterval(() => {
        timeLeft.value--;
        if (timeLeft.value <= 0) { clearInterval(timer); timeUp(); }
      }, 1000);
    }

    function timeUp() {
      if (answered.value) return;
      answered.value = true; isCorrect.value = false; lastPoints.value = 0;
      correctLabel.value = findCorrectLabel();
      if (lives.value !== 99) lives.value = Math.max(0, lives.value - 1);
      streak.value = 0;
      if (lives.value <= 0 && lives.value !== 99) { setTimeout(endGame, 1200); return; }
      setTimeout(nextQ, 1500);
    }

    function answer(choice) {
      if (answered.value) return;
      clearInterval(timer);
      answered.value = true;
      const ok = choice.id === q.value.correctId || String(choice.id) === String(q.value.correctId);
      isCorrect.value = ok;
      if (ok) {
        streak.value++; correct.value++;
        if (streak.value > maxStreak.value) maxStreak.value = streak.value;
        const pts = QuizEngine.calcScore({ baseScore: 100, timeLimit: q.value.timeLimit, timeLeft: timeLeft.value, streak: streak.value });
        lastPoints.value = pts; score.value += pts;
        // AI 개인화 피드백: 정답 영화 ID 수집
        const qType = q.value.type;
        let mId = null;
        if (qType === 'poster' || qType === 'overview') {
          mId = q.value.correctId;
        } else if (q.value.movieId) {
          mId = q.value.movieId;
        } else if (q.value.movieTitle) {
          const found = store.movies?.find(m => m.title === q.value.movieTitle);
          if (found) mId = found.id;
        }
        if (mId != null) correctMovieIds.value.push(mId);
      } else {
        correctLabel.value = findCorrectLabel();
        if (lives.value !== 99) lives.value = Math.max(0, lives.value - 1);
        streak.value = 0;
        if (lives.value <= 0 && lives.value !== 99) { setTimeout(endGame, 1500); return; }
      }
      setTimeout(nextQ, 1300);
    }

    function findCorrectLabel() {
      const c = q.value.choices.find(x => x.id === q.value.correctId || String(x.id) === String(q.value.correctId));
      return c ? c.label : String(q.value.correctId);
    }

    function nextQ() {
      if (qIdx.value + 1 >= questions.value.length) { endGame(); return; }
      qIdx.value++; answered.value = false; startTimer();
    }

    function endGame() {
      clearInterval(timer); screen.value = 'result';
      loadLocalLb(); lbName.value = store.user?.username || '';
    }

    async function loadLocalLb() {
      try {
        const d = await store.apiGet(`/api/leaderboard?mode=${selectedMode.value}`);
        localLb.value = d.leaderboard.slice(0, 10);
      } catch(e) { localLb.value = []; }
    }

    async function registerScore() {
      const name = lbName.value.trim() || store.user?.username || '익명';
      try {
        if (store.user) {
          // 로그인: 인증 엔드포인트 → AI 개인화 피드백 루프
          const d = await store.apiPost('/api/game/scores', {
            score: score.value, mode: selectedMode.value,
            correct: correct.value, total: questions.value.length,
            movieIds: correctMovieIds.value
          });
          lbDone.value = true;
          const lb = await store.apiGet(`/api/leaderboard?mode=${selectedMode.value}`);
          localLb.value = lb.leaderboard.slice(0, 10);
          const rankIdx = lb.leaderboard.findIndex(e => e.id === d.entry?.id);
          lbRank.value = rankIdx >= 0 ? rankIdx + 1 : null;
          showToast(lbRank.value ? `🏆 ${lbRank.value}위 등록!` : '점수가 등록됐습니다!', 'success');
        } else {
          // 비로그인: 기존 공개 엔드포인트
          const d = await store.apiPost('/api/leaderboard', {
            username: name, score: score.value, mode: selectedMode.value,
            correct: correct.value, total: questions.value.length
          });
          lbDone.value = true; lbRank.value = d.rank;
          showToast(`🏆 ${d.rank}위 등록!`, 'success');
          loadLocalLb();
        }
      } catch(e) { showToast(e.message || '등록 실패', 'error'); }
    }

    function restart() { screen.value = 'select'; clearInterval(timer); }

    function choiceClass(c) {
      if (!answered.value) return '';
      const cId = c.id; const qId = q.value.correctId;
      const match = cId === qId || String(cId) === String(qId);
      if (match) return 'correct';
      if (isCorrect.value) return 'neutral-fade';
      return 'wrong';
    }

    Vue.onUnmounted(() => clearInterval(timer));

    return { store, screen, modes, selectedMode, qCount, startLives, loading,
             questions, qIdx, q, score, lives, streak, maxStreak, correct,
             timeLeft, answered, isCorrect, lastPoints, correctLabel, grade,
             lbName, lbDone, lbRank, localLb, modeLabel, correctMovieIds,
             startQuiz, answer, restart, registerScore, choiceClass, nav };
  }
};

// ─── CommunityPage ───────────────────────────────────────────────────────────
const CommunityPage = {
  template: `
  <div class="page fade-in">
    <div class="community-header">
      <h1>💬 커뮤니티</h1>
      <p>영화 이야기를 나눠요 — 리뷰, 토론, 추천!</p>
    </div>
    <div class="community-controls">
      <select v-model="sort" @change="load" class="form-select" style="width:140px;background:var(--bg-card);color:var(--text);border-color:var(--border2)">
        <option value="latest">최신순</option>
        <option value="likes">인기순</option>
      </select>
      <select v-model="category" @change="load" class="form-select" style="width:140px;background:var(--bg-card);color:var(--text);border-color:var(--border2)">
        <option value="">전체</option>
        <option value="review">리뷰</option>
        <option value="discuss">토론</option>
        <option value="recommend">추천</option>
        <option value="general">자유</option>
      </select>
      <button v-if="store.user" class="write-toggle" @click="showForm=!showForm">
        <i class="fa-solid fa-pen"></i> {{ showForm?'닫기':'글쓰기' }}
      </button>
      <a v-else href="#/auth" class="write-toggle" style="text-decoration:none">
        <i class="fa-solid fa-lock"></i> 로그인 후 작성
      </a>
    </div>

    <!-- Write Form -->
    <div v-if="showForm" class="community-content" style="padding-top:0">
      <div class="review-form-wrap">
        <div class="review-form-title">새 글 작성</div>
        <div class="form-row">
          <div class="form-field" style="flex:2">
            <label>제목</label>
            <input v-model="form.title" placeholder="제목을 입력하세요" />
          </div>
          <div class="form-field" style="flex:1">
            <label>카테고리</label>
            <select v-model="form.category" class="form-select" style="background:var(--bg-card);color:var(--text);border-color:var(--border2)">
              <option value="general">자유</option>
              <option value="review">리뷰</option>
              <option value="discuss">토론</option>
              <option value="recommend">추천</option>
            </select>
          </div>
        </div>
        <div class="form-field">
          <label>내용</label>
          <textarea v-model="form.content" placeholder="내용을 입력하세요..." style="min-height:120px"></textarea>
        </div>
        <button class="btn-primary mt-2" @click="submitPost" :disabled="!form.title||!form.content">
          <i class="fa-solid fa-paper-plane"></i> 등록
        </button>
      </div>
    </div>

    <div class="community-content">
      <div class="reviews-feed" v-if="posts.length">
        <div v-for="p in posts" :key="p.id" class="review-card" style="cursor:pointer" @click="nav('#/community/'+p.id)">
          <div class="review-header">
            <div>
              <div style="display:flex;align-items:center;gap:.5rem">
                <span class="badge rounded-pill"
                  :style="catStyle(p.category)">{{ catLabel(p.category) }}</span>
                <span class="reviewer-name">{{ p.title }}</span>
              </div>
              <div style="font-size:.8rem;color:var(--text3);margin-top:.25rem">
                {{ p.author?.username }} · {{ fmtDate(p.createdAt) }}
              </div>
            </div>
            <div style="text-align:right;flex-shrink:0">
              <div style="color:var(--red);font-size:.85rem">❤️ {{ p.likes||0 }}</div>
              <div style="color:var(--text3);font-size:.8rem">💬 {{ p.commentCount||0 }}</div>
            </div>
          </div>
          <p class="review-body" style="display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden">{{ p.content }}</p>
        </div>
      </div>
      <div class="empty-state" v-else-if="!loading">
        <div class="empty-icon"><i class="fa-solid fa-comments"></i></div>
        <div class="empty-title">아직 게시글이 없어요</div>
        <div class="empty-sub">첫 번째 글을 작성해보세요!</div>
      </div>
      <!-- Pagination -->
      <div class="pagination" v-if="pages > 1">
        <button class="pg-btn" :disabled="page<=1" @click="changePage(page-1)"><i class="fa-solid fa-chevron-left"></i></button>
        <button v-for="p in pageNums" :key="p" :class="['pg-btn',{active:p===page}]" @click="changePage(p)">{{ p }}</button>
        <button class="pg-btn" :disabled="page>=pages" @click="changePage(page+1)"><i class="fa-solid fa-chevron-right"></i></button>
      </div>
    </div>
  </div>`,
  setup() {
    const store = CineStore;
    const posts = Vue.ref([]), loading = Vue.ref(false), showForm = Vue.ref(false);
    const sort = Vue.ref('latest'), category = Vue.ref('');
    const page = Vue.ref(1), pages = Vue.ref(1);
    const form = Vue.reactive({ title: '', content: '', category: 'general' });

    async function load() {
      loading.value = true;
      try {
        const url = `/api/community/posts?sort=${sort.value}&page=${page.value}&limit=10${category.value ? '&category='+category.value : ''}`;
        const d = await store.apiGet(url);
        posts.value = d.posts; pages.value = d.pages;
      } catch(e) { showToast(e.message, 'error'); }
      loading.value = false;
    }
    async function submitPost() {
      try {
        await store.apiPost('/api/community/posts', { ...form });
        form.title = ''; form.content = ''; showForm.value = false;
        showToast('게시글이 등록됐습니다!', 'success'); page.value = 1; load();
      } catch(e) { showToast(e.message, 'error'); }
    }
    function changePage(p) { page.value = p; load(); }
    const pageNums = Vue.computed(() => {
      const r = []; const s = Math.max(1, page.value-2); const e = Math.min(pages.value, s+4);
      for (let i = s; i <= e; i++) r.push(i); return r;
    });
    function fmtDate(d) { return new Date(d).toLocaleDateString('ko-KR'); }
    function catLabel(c) { return { review:'리뷰', discuss:'토론', recommend:'추천', general:'자유' }[c] || '자유'; }
    function catStyle(c) {
      const m = { review: '#3a86ff', discuss: '#9b5de5', recommend: '#06d6a0', general: '#f0b429' };
      return { background: (m[c]||'#888')+'33', color: m[c]||'#888', border: `1px solid ${m[c]||'#888'}55` };
    }
    Vue.onMounted(load);
    return { store, posts, loading, showForm, sort, category, page, pages, pageNums, form, load, submitPost, changePage, fmtDate, catLabel, catStyle, nav };
  }
};

// ─── PostDetailPage ──────────────────────────────────────────────────────────
const PostDetailPage = {
  template: `
  <div class="page fade-in" style="max-width:860px;margin:0 auto;padding:2rem">
    <button class="btn-secondary mb-4" @click="nav('#/community')">
      <i class="fa-solid fa-arrow-left"></i> 목록으로
    </button>
    <div v-if="post">
      <div class="d-flex align-items-start justify-content-between mb-3">
        <div>
          <h2 style="font-size:1.5rem;font-weight:800">{{ post.title }}</h2>
          <div style="color:var(--text3);font-size:.85rem;margin-top:.3rem">
            <span>{{ post.author?.username }}</span> · <span>{{ fmtDate(post.createdAt) }}</span>
          </div>
        </div>
        <div class="d-flex gap-2" v-if="isAuthor">
          <button class="btn-secondary" style="padding:.4rem .8rem;font-size:.82rem" @click="edit=!edit">수정</button>
          <button class="btn-secondary" style="padding:.4rem .8rem;font-size:.82rem;color:var(--red)" @click="deletePost">삭제</button>
        </div>
      </div>

      <!-- Edit Mode -->
      <div v-if="edit" class="review-form-wrap mb-4">
        <div class="form-field mb-3"><label>제목</label><input v-model="editForm.title" /></div>
        <div class="form-field mb-3"><label>내용</label><textarea v-model="editForm.content" style="min-height:120px"></textarea></div>
        <div class="d-flex gap-2">
          <button class="btn-primary" @click="updatePost">저장</button>
          <button class="btn-secondary" @click="edit=false">취소</button>
        </div>
      </div>

      <!-- Content -->
      <div v-else class="review-form-wrap mb-4">
        <p style="color:var(--text2);line-height:1.8;font-size:.95rem;white-space:pre-wrap">{{ post.content }}</p>
      </div>

      <!-- Like -->
      <div class="d-flex align-items-center gap-3 mb-4">
        <button class="btn-secondary" @click="like" :style="liked?{color:'var(--red)',borderColor:'var(--red)'}:{}">
          <i :class="liked?'fa-solid fa-heart':'fa-regular fa-heart'"></i> {{ post.likes || 0 }}
        </button>
      </div>

      <!-- Comments -->
      <hr style="border-color:var(--border)">
      <h4 style="font-size:1rem;font-weight:700;margin:1.25rem 0">댓글 {{ (post.comments||[]).length }}개</h4>
      <div v-for="c in (post.comments||[])" :key="c.id" class="review-card mb-2">
        <div class="review-header">
          <span class="reviewer-name">{{ c.author?.username }}</span>
          <span class="review-date">{{ fmtDate(c.createdAt) }}</span>
        </div>
        <p class="review-body">{{ c.content }}</p>
      </div>
      <div v-if="store.user" class="mt-3">
        <div class="d-flex gap-2">
          <input v-model="commentText" class="form-control" style="background:var(--bg-card);border-color:var(--border2);color:var(--text)"
            placeholder="댓글을 입력하세요..." @keyup.enter="addComment" />
          <button class="btn-primary" @click="addComment" :disabled="!commentText.trim()">등록</button>
        </div>
      </div>
      <div v-else class="mt-3"><a href="#/auth" class="btn-secondary">로그인 후 댓글 작성</a></div>
    </div>
    <div class="empty-state" v-else>
      <div class="empty-icon"><i class="fa-solid fa-spinner fa-spin"></i></div>
      <div class="empty-title">불러오는 중...</div>
    </div>
  </div>`,
  setup() {
    const store = CineStore;
    const post = Vue.ref(null), edit = Vue.ref(false), commentText = Vue.ref('');
    const liked = Vue.ref(false);
    const editForm = Vue.reactive({ title: '', content: '' });
    const isAuthor = Vue.computed(() => store.user && post.value && post.value.author?.id === store.user.id);

    async function load() {
      try {
        const d = await store.apiGet(`/api/community/posts/${AppRouter.params.id}`);
        post.value = d;
        editForm.title = d.title; editForm.content = d.content;
        liked.value = (d.likedBy || []).includes(store.user?.id);
      } catch(e) { showToast(e.message, 'error'); }
    }
    async function like() {
      if (!store.user) { showToast('로그인이 필요합니다', 'error'); return; }
      try {
        const d = await store.apiPost(`/api/community/posts/${post.value.id}/like`, {});
        post.value.likes = d.likes; liked.value = d.liked;
      } catch(e) { showToast(e.message, 'error'); }
    }
    async function updatePost() {
      try {
        const d = await store.apiPut(`/api/community/posts/${post.value.id}`, { title: editForm.title, content: editForm.content });
        post.value = d; edit.value = false; showToast('수정됐습니다', 'success');
      } catch(e) { showToast(e.message, 'error'); }
    }
    async function deletePost() {
      if (!confirm('삭제하시겠습니까?')) return;
      try {
        await store.apiDelete(`/api/community/posts/${post.value.id}`);
        showToast('삭제됐습니다', 'info'); nav('#/community');
      } catch(e) { showToast(e.message, 'error'); }
    }
    async function addComment() {
      if (!commentText.value.trim()) return;
      try {
        const c = await store.apiPost(`/api/community/posts/${post.value.id}/comments`, { content: commentText.value });
        post.value.comments = [...(post.value.comments || []), c];
        commentText.value = ''; showToast('댓글이 등록됐습니다', 'success');
      } catch(e) { showToast(e.message, 'error'); }
    }
    function fmtDate(d) { return new Date(d).toLocaleDateString('ko-KR'); }
    Vue.onMounted(load);
    return { store, post, edit, editForm, liked, commentText, isAuthor, like, updatePost, deletePost, addComment, fmtDate, nav };
  }
};

// ─── LeaderboardPage ─────────────────────────────────────────────────────────
const LeaderboardPage = {
  template: `
  <div class="page fade-in">
    <div class="community-header">
      <h1>🏆 명예의 전당</h1>
      <p>CineAI 퀴즈 최강자들의 기록</p>
    </div>
    <div class="community-controls">
      <select v-model="mode" @change="load" class="form-select" style="width:160px;background:var(--bg-card);color:var(--text);border-color:var(--border2)">
        <option value="all">전체 모드</option>
        <option value="poster">포스터 → 제목</option>
        <option value="director">포스터 → 감독</option>
        <option value="cast">포스터 → 배우</option>
        <option value="genre">장르 맞추기</option>
        <option value="year">연도 맞추기</option>
        <option value="overview">줄거리 → 제목</option>
      </select>
    </div>
    <div class="community-content">
      <div v-if="lb.length">
        <div v-for="(e, i) in lb" :key="e.id" class="lb-row">
          <span :class="['lb-rank', i===0?'gold-rank':i===1?'silver-rank':i===2?'bronze-rank':'']">
            {{ i===0?'🥇':i===1?'🥈':i===2?'🥉':i+1 }}
          </span>
          <span class="lb-name">
            {{ e.username }}
            <span class="lb-mode">{{ e.mode }} · {{ e.correct }}/{{ e.total }} 정답</span>
          </span>
          <span class="lb-score">{{ e.score?.toLocaleString() }}점</span>
          <span style="font-size:.78rem;color:var(--text3)">{{ fmtDate(e.date) }}</span>
        </div>
      </div>
      <div class="empty-state" v-else-if="!loading">
        <div class="empty-icon"><i class="fa-solid fa-trophy"></i></div>
        <div class="empty-title">아직 기록이 없어요</div>
        <div class="empty-sub">퀴즈에 도전해 첫 번째 기록을 남겨보세요!</div>
        <button class="btn-primary mt-3" @click="nav('#/quiz')">퀴즈 도전</button>
      </div>
    </div>
  </div>`,
  setup() {
    const store = CineStore;
    const lb = Vue.ref([]), loading = Vue.ref(false), mode = Vue.ref('all');
    async function load() {
      loading.value = true;
      try {
        const d = await store.apiGet(`/api/leaderboard?mode=${mode.value}`);
        lb.value = d.leaderboard;
      } catch(e) { showToast(e.message, 'error'); }
      loading.value = false;
    }
    function fmtDate(d) { return new Date(d).toLocaleDateString('ko-KR'); }
    Vue.onMounted(load);
    return { store, lb, loading, mode, load, fmtDate, nav };
  }
};

// ─── AuthPage ─────────────────────────────────────────────────────────────────
const AuthPage = {
  template: `
  <div class="page fade-in d-flex align-items-center justify-content-center" style="min-height:calc(100vh - 64px)">
    <div style="width:100%;max-width:420px;padding:2rem">
      <div class="text-center mb-4">
        <div style="font-size:2.5rem;margin-bottom:.5rem">🎬</div>
        <h2 style="font-size:1.6rem;font-weight:900">CineAI</h2>
        <p style="color:var(--text2);font-size:.9rem">영화 퀴즈와 커뮤니티를 즐겨보세요</p>
      </div>

      <!-- Tab -->
      <div class="d-flex gap-1 mb-4 p-1" style="background:var(--bg3);border-radius:var(--r)">
        <button :class="['btn-primary', 'w-50', tab==='login'?'':'btn-secondary']" style="border-radius:8px;padding:.55rem" @click="tab='login'">로그인</button>
        <button :class="['btn-primary', 'w-50', tab==='register'?'':'btn-secondary']" style="border-radius:8px;padding:.55rem" @click="tab='register'">회원가입</button>
      </div>

      <div class="review-form-wrap">
        <!-- Register -->
        <div v-if="tab==='register'">
          <div class="form-field mb-3">
            <label>닉네임</label>
            <input v-model="rf.username" placeholder="닉네임 (2자 이상)" @keyup.enter="register" />
          </div>
          <div class="form-field mb-3">
            <label>이메일</label>
            <input v-model="rf.email" type="email" placeholder="이메일 주소" @keyup.enter="register" />
          </div>
          <div class="form-field mb-4">
            <label>비밀번호</label>
            <input v-model="rf.password" type="password" placeholder="6자 이상" @keyup.enter="register" />
          </div>
          <button class="btn-primary w-100" @click="register" :disabled="loading">
            <i class="fa-solid fa-user-plus"></i> {{ loading ? '처리 중...' : '회원가입' }}
          </button>
        </div>

        <!-- Login -->
        <div v-else>
          <div class="form-field mb-3">
            <label>이메일</label>
            <input v-model="lf.email" type="email" placeholder="이메일 주소" @keyup.enter="login" />
          </div>
          <div class="form-field mb-4">
            <label>비밀번호</label>
            <input v-model="lf.password" type="password" placeholder="비밀번호" @keyup.enter="login" />
          </div>
          <button class="btn-primary w-100" @click="login" :disabled="loading">
            <i class="fa-solid fa-right-to-bracket"></i> {{ loading ? '처리 중...' : '로그인' }}
          </button>
        </div>

        <div v-if="errMsg" class="alert alert-danger mt-3 py-2 px-3" style="font-size:.87rem">{{ errMsg }}</div>
      </div>
    </div>
  </div>`,
  setup() {
    const store = CineStore;
    const tab = Vue.ref('login'), loading = Vue.ref(false), errMsg = Vue.ref('');
    const rf = Vue.reactive({ username: '', email: '', password: '' });
    const lf = Vue.reactive({ email: '', password: '' });

    async function register() {
      errMsg.value = ''; loading.value = true;
      try {
        const d = await store.apiPost('/api/auth/register', { ...rf });
        store.login(d.token, d.user);
        showToast(`${d.user.username}님, 환영합니다!`, 'success');
        nav('#/');
      } catch(e) { errMsg.value = e.message; }
      loading.value = false;
    }
    async function login() {
      errMsg.value = ''; loading.value = true;
      try {
        const d = await store.apiPost('/api/auth/login', { ...lf });
        store.login(d.token, d.user);
        showToast(`${d.user.username}님, 안녕하세요!`, 'success');
        nav('#/');
      } catch(e) { errMsg.value = e.message; }
      loading.value = false;
    }
    return { store, tab, loading, errMsg, rf, lf, register, login };
  }
};
