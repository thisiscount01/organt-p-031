// CineAI — Vue 3 App Initialization
const { createApp, computed, h } = Vue;

const App = {
  components: { NavBar, ToastComp, HomePage, MoviesPage, MovieDetailPage,
                QuizPage, CommunityPage, PostDetailPage, LeaderboardPage, AuthPage, DailyPage },
  setup() {
    const store = CineStore;
    const r = AppRouter;
    const CurrentPage = computed(() => {
      const p = r.path;
      if (p === '/')              return 'HomePage';
      if (p === '/movies')        return 'MoviesPage';
      if (p === '/movie')         return 'MovieDetailPage';
      if (p === '/quiz')          return 'QuizPage';
      if (p === '/community')     return 'CommunityPage';
      if (p === '/community/post')return 'PostDetailPage';
      if (p === '/leaderboard')   return 'LeaderboardPage';
      if (p === '/auth')          return 'AuthPage';
      if (p === '/daily')         return 'DailyPage';
      return 'HomePage';
    });
    return { store, CurrentPage };
  },
  template: `
  <div>
    <!-- Init Loader -->
    <div class="init-loader" v-if="!store.loaded">
      <div class="init-loader-inner">
        <div class="init-logo"><span class="logo-cine">Cine</span><span class="logo-ai">AI</span></div>
        <p class="init-tagline">AI 기반 영화 추천 · 퀴즈 · 커뮤니티</p>
        <div class="init-progress"><div class="init-progress-fill"></div></div>
      </div>
    </div>
    <template v-else>
      <NavBar />
      <main class="site-main">
        <component :is="CurrentPage" :key="CurrentPage" />
      </main>
      <footer class="site-footer">
        <div class="footer-logo"><span class="logo-cine">Cine</span><span class="logo-ai">AI</span></div>
        <p class="footer-desc">TMDB 영화 데이터 기반 AI 추천 · 퀴즈 게임 · 커뮤니티</p>
        <p class="footer-copy">© 2025 CineAI · This product uses the TMDB API but is not endorsed or certified by TMDB.</p>
      </footer>
      <ToastComp />
    </template>
  </div>`
};

const vueApp = createApp(App);
vueApp.mount('#app');

// Init data
CineStore.init();
