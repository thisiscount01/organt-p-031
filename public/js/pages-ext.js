// ─── CineAI Frontend Extension ─────────────────────────────────────────────
// pages-ext.js: DailyPage + QuizPage 기능 확장(힌트·AI추천·업적)
// pages.js / app.js 소유 경계로 인해 별도 파일에 구현하고
// router patch + component 재정의 방식으로 통합.
// 로딩 순서: pages.js → pages-ext.js → app.js

// ─── 1. Router patch: /daily 경로 추가 ─────────────────────────────────────
// pages.js의 parseRoute는 'daily' 세그먼트를 '/'로 fallback 처리.
// hashchange 이벤트를 추가로 수신해 AppRouter를 '/daily'로 덮어씀.
(function patchDailyRoute() {
  function applyDailyPatch() {
    const hash = location.hash.replace(/^#/, '') || '/';
    const segs = hash.split('?')[0].split('/').filter(Boolean);
    if (segs[0] === 'daily') {
      AppRouter.path = '/daily';
      AppRouter.params = {};
    }
  }
  window.addEventListener('hashchange', applyDailyPatch);
  applyDailyPatch(); // 현재 URL 즉시 적용
})();

// ─── 2. NavBar 재정의 (daily 링크 추가) ────────────────────────────────────
// pages.js에서 const NavBar로 선언되므로 window.NavBarPatched로 우회
// → App 컴포넌트 등록 시 NavBarPatched를 우선 사용 (app.js 패치와 연동)
var NavBarPatched = {
  template: `
  <nav class="navbar">
    <a class="nav-logo" href="#/"><span class="logo-cine">Cine</span><span class="logo-ai">AI</span></a>
    <ul class="nav-links">
      <li><a href="#/" :class="{active: r.path==='/'}"><i class="fa-solid fa-house"></i> 홈</a></li>
      <li><a href="#/movies" :class="{active: r.path==='/movies'}"><i class="fa-solid fa-film"></i> 영화</a></li>
      <li><a href="#/quiz" :class="{active: r.path==='/quiz'}"><i class="fa-solid fa-gamepad"></i> 퀴즈</a></li>
      <li><a href="#/daily" :class="{active: r.path==='/daily'}"><i class="fa-solid fa-calendar-star"></i> 오늘의 퀴즈</a></li>
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

// ─── 3. QuizPage 확장판 ─────────────────────────────────────────────────────
// 힌트 시스템 + AI 추천 + 업적 Toast를 추가한 QuizPage
var QuizPageExt = {
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
        <!-- 힌트 버튼 -->
        <button class="hint-btn ms-2" @click="useHint" :disabled="hintUsed||answered"
          :title="hintUsed?'힌트 사용됨':'힌트 사용 (1회)'">
          💡 {{ hintUsed ? '사용됨' : '힌트' }}
        </button>
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
        <!-- 힌트 텍스트 -->
        <div v-if="hintText" class="quiz-hint-text">{{ hintText }}</div>
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

      <!-- AI 기반 퀴즈 결과 추천 -->
      <div class="ai-quiz-recs" v-if="recMovies.length">
        <div class="rec-title"><i class="fa-solid fa-robot"></i> 퀴즈 결과 기반 AI 추천</div>
        <p style="color:var(--text2);font-size:.85rem;margin-bottom:1rem">
          오답 영화와 유사한 작품들을 골라봤어요
        </p>
        <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(140px,1fr));gap:.75rem">
          <MovieCard v-for="m in recMovies" :key="m.id" :movie="m" :showRec="true"
            @click="goMovieRec" />
        </div>
      </div>

      <!-- Local Leaderboard -->
      <div class="leaderboard-wrap">
        <div class="lb-title">이번 모드 TOP 10</div>
        <div v-for="(e, i) in localLb" :key="e.id" :class="['lb-row', e._isMe?' my-row':'']">
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
  components: { MovieCard },
  setup() {
    const store = CineStore;
    const QUIZ_MODES = [
      { key: 'poster',   icon: '🎬', title: '포스터 → 제목',   desc: '포스터를 보고 영화 제목을 맞춰요',     time: 30 },
      { key: 'director', icon: '🎥', title: '포스터 → 감독',   desc: '포스터를 보고 감독 이름을 맞춰요',     time: 25 },
      { key: 'cast',     icon: '⭐', title: '포스터 → 배우',   desc: '포스터를 보고 주연 배우를 맞춰요',     time: 25 },
      { key: 'genre',    icon: '🎭', title: '장르 맞추기',     desc: '영화 제목으로 주요 장르를 맞춰요',     time: 20 },
      { key: 'year',     icon: '📅', title: '개봉년도 맞추기', desc: '영화 포스터로 개봉 연도를 맞춰요',     time: 15 },
      { key: 'overview', icon: '📖', title: '줄거리 → 제목',   desc: '줄거리 힌트로 영화 제목을 맞춰요',    time: 28 },
    ];

    const screen = Vue.ref('select'), selectedMode = Vue.ref('poster');
    const qCount = Vue.ref(10), startLives = Vue.ref(3);
    const questions = Vue.ref([]), qIdx = Vue.ref(0), score = Vue.ref(0);
    const correctMovieIds = Vue.ref([]);
    const lives = Vue.ref(3), streak = Vue.ref(0), maxStreak = Vue.ref(0), correct = Vue.ref(0);
    const timeLeft = Vue.ref(30), answered = Vue.ref(false), isCorrect = Vue.ref(false);
    const lastPoints = Vue.ref(0), correctLabel = Vue.ref('');
    const lbName = Vue.ref(''), lbDone = Vue.ref(false), lbRank = Vue.ref(null);
    const localLb = Vue.ref([]), loading = Vue.ref(false);
    const recMovies = Vue.ref([]);
    const hintUsed = Vue.ref(false), hintText = Vue.ref('');
    let timer = null;

    const q = Vue.computed(() => questions.value[qIdx.value]);
    const modeLabel = Vue.computed(() => QUIZ_MODES.find(m => m.key === selectedMode.value)?.title || '');
    const grade = Vue.computed(() => QuizEngine.gradeResult(score.value, questions.value.length));
    const modes = QUIZ_MODES;

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
      recMovies.value = []; hintUsed.value = false; hintText.value = '';
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
      qIdx.value++;
      answered.value = false;
      hintUsed.value = false; hintText.value = '';
      startTimer();
    }

    function useHint() {
      if (hintUsed.value || answered.value) return;
      hintUsed.value = true;
      const curr = q.value;
      const correctChoice = curr.choices.find(c =>
        c.id === curr.correctId || String(c.id) === String(curr.correctId)
      );
      if (correctChoice) {
        const label = correctChoice.label;
        const hint = label[0] + label.slice(1).replace(/[^\s]/g, '_');
        hintText.value = `💡 힌트: ${hint}`;
      }
    }

    async function endGame() {
      clearInterval(timer);
      screen.value = 'result';
      loadLocalLb();
      lbName.value = store.user?.username || '';
      // 오답 영화 기반 AI 추천
      const allMovieIds = questions.value.map(q => q.correctId || q.movieId).filter(Boolean);
      const wrongMovieIds = allMovieIds.filter(id => !correctMovieIds.value.includes(id));
      const targetId = wrongMovieIds[0] || allMovieIds[0];
      if (targetId) {
        try {
          const d = await store.apiGet(`/api/recommend/${targetId}`);
          recMovies.value = (d.recommendations || []).slice(0, 6);
        } catch(e) { recMovies.value = []; }
      }
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
          const d = await store.apiPost('/api/leaderboard', {
            username: name, score: score.value, mode: selectedMode.value,
            correct: correct.value, total: questions.value.length
          });
          lbDone.value = true; lbRank.value = d.rank;
          showToast(`🏆 ${d.rank}위 등록!`, 'success');
          loadLocalLb();
        }
      } catch(e) { showToast(e.message || '등록 실패', 'error'); }

      // 업적 체크 (로그인 여부 무관)
      try {
        const ach = await store.apiPost('/api/achievements/check', {
          score: score.value,
          streak: maxStreak.value,
          correct: correct.value,
          total: questions.value.length,
          mode: selectedMode.value
        });
        const gained = ach.gained || ach.unlocked || [];
        gained.forEach((a, i) => {
          setTimeout(() => showToast(`${a.icon || '🏅'} 업적 해금: ${a.name}!`, 'success'), 500 + i * 800);
        });
      } catch(e) { /* 무시 */ }
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

    function goMovieRec(m) { nav('#/movie/' + m.id); }

    Vue.onUnmounted(() => clearInterval(timer));

    return { store, screen, modes, selectedMode, qCount, startLives, loading,
             questions, qIdx, q, score, lives, streak, maxStreak, correct,
             timeLeft, answered, isCorrect, lastPoints, correctLabel, grade,
             lbName, lbDone, lbRank, localLb, modeLabel, correctMovieIds,
             recMovies, hintUsed, hintText,
             startQuiz, answer, restart, registerScore, choiceClass, useHint, goMovieRec, nav };
  }
};

// ─── 4. DailyPage 컴포넌트 ──────────────────────────────────────────────────
var DailyPage = {
  template: `
  <div class="quiz-page">

    <!-- 이미 완료한 경우 -->
    <div v-if="alreadyDone" class="daily-done-card fade-in">
      <div class="daily-badge">📅 오늘의 영화 퀴즈</div>
      <h2 style="font-size:1.5rem;font-weight:800;margin:.75rem 0 .5rem">오늘은 이미 도전했어요!</h2>
      <div class="result-score" style="font-size:2.5rem;margin:.5rem 0">{{ doneData.score?.toLocaleString() }}점</div>
      <p style="color:var(--text2)">{{ doneData.correct }}/{{ doneData.total }} 정답 · {{ fmtTime(doneData.time) }} 소요</p>
      <p class="mt-3" style="color:var(--text3);font-size:.9rem">내일 새로운 문제가 찾아와요 🌅</p>
      <div v-if="leaderboard.length" class="leaderboard-wrap mt-4" style="max-width:480px;margin-left:auto;margin-right:auto">
        <div class="lb-title">오늘의 TOP 10</div>
        <div v-for="(e,i) in leaderboard" :key="e.id||i" class="lb-row">
          <span :class="['lb-rank',i===0?'gold-rank':i===1?'silver-rank':i===2?'bronze-rank':'']">
            {{ i===0?'🥇':i===1?'🥈':i===2?'🥉':i+1 }}
          </span>
          <span class="lb-name">{{ e.username }}</span>
          <span class="lb-score">{{ e.score?.toLocaleString() }}</span>
        </div>
      </div>
      <div class="d-flex gap-2 justify-content-center mt-4">
        <button class="btn-primary" @click="nav('#/quiz')"><i class="fa-solid fa-gamepad"></i> 일반 퀴즈</button>
        <button class="btn-secondary" @click="nav('#/')"><i class="fa-solid fa-house"></i> 홈으로</button>
      </div>
    </div>

    <!-- 로딩 -->
    <div v-else-if="loading" class="empty-state">
      <div class="empty-icon"><i class="fa-solid fa-spinner fa-spin"></i></div>
      <div class="empty-title">오늘의 퀴즈 불러오는 중...</div>
    </div>

    <!-- 게임 화면 -->
    <div class="quiz-game-screen" v-else-if="screen==='game' && q">
      <div class="daily-header">
        <div class="daily-badge">📅 오늘의 영화 퀴즈 — {{ todayStr }}</div>
      </div>
      <!-- HUD -->
      <div class="quiz-hud">
        <div class="hud-stat"><span class="hud-label">점수</span><span class="hud-value gold">{{ score }}</span></div>
        <div class="hud-divider"></div>
        <div class="hud-stat"><span class="hud-label">연속</span><span class="hud-value green">🔥 x{{ streak }}</span></div>
        <div class="hud-divider"></div>
        <div class="hud-stat"><span class="hud-label">진도</span><span class="hud-value">{{ qIdx+1 }}/{{ questions.length }}</span></div>
        <div class="hud-progress ms-auto">
          <div class="hud-progress-fill" :style="{width: ((qIdx+1)/questions.length*100)+'%'}"></div>
        </div>
        <button class="hint-btn ms-2" @click="useHint" :disabled="hintUsed||answered"
          :title="hintUsed?'힌트 사용됨':'힌트 사용 (1회)'">
          💡 {{ hintUsed ? '사용됨' : '힌트' }}
        </button>
      </div>
      <!-- Timer Bar -->
      <div class="quiz-timer-bar">
        <div class="quiz-timer-fill"
          :style="{ width: (timeLeft/q.timeLimit*100)+'%',
            background: timeLeft/q.timeLimit > 0.5 ? 'var(--green)' : timeLeft/q.timeLimit > 0.25 ? 'var(--gold)' : 'var(--red)' }"></div>
      </div>
      <!-- Question Card -->
      <div class="quiz-question-card">
        <div class="quiz-q-type">오늘의 퀴즈 · {{ timeLeft }}초</div>
        <div class="quiz-q-prompt">{{ q.prompt }}</div>
        <div class="quiz-img-wrap" v-if="q.image">
          <img :src="q.image" :alt="q.movieTitle||''" loading="lazy"
               @error="e => e.target.style.display='none'" />
        </div>
        <div class="quiz-snippet" v-if="q.snippet">{{ q.snippet }}</div>
        <div v-if="hintText" class="quiz-hint-text">{{ hintText }}</div>
        <div class="quiz-choices">
          <button v-for="(c,ci) in q.choices" :key="c.id"
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

    <!-- 결과 화면 -->
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
      <div v-if="leaderboard.length" class="leaderboard-wrap mt-4" style="max-width:480px;margin-left:auto;margin-right:auto">
        <div class="lb-title">오늘의 TOP 10</div>
        <div v-for="(e,i) in leaderboard" :key="e.id||i" class="lb-row">
          <span :class="['lb-rank',i===0?'gold-rank':i===1?'silver-rank':i===2?'bronze-rank':'']">
            {{ i===0?'🥇':i===1?'🥈':i===2?'🥉':i+1 }}
          </span>
          <span class="lb-name">{{ e.username }}</span>
          <span class="lb-score">{{ e.score?.toLocaleString() }}</span>
        </div>
      </div>
      <p class="mt-3" style="color:var(--text3);font-size:.9rem">내일 새로운 문제가 찾아와요 🌅</p>
      <div class="quiz-result-btns">
        <button class="btn-primary" @click="nav('#/quiz')"><i class="fa-solid fa-gamepad"></i> 일반 퀴즈</button>
        <button class="btn-secondary" @click="nav('#/')"><i class="fa-solid fa-house"></i> 홈으로</button>
        <button class="btn-secondary" @click="nav('#/leaderboard')"><i class="fa-solid fa-trophy"></i> 전체 랭킹</button>
      </div>
    </div>
  </div>`,
  setup() {
    const store = CineStore;
    const today = new Date().toISOString().slice(0, 10);
    const todayStr = today.slice(0, 4) + '년 ' + today.slice(5, 7) + '월 ' + today.slice(8, 10) + '일';
    const DONE_KEY = 'daily_done_' + today;

    const screen = Vue.ref('loading');
    const loading = Vue.ref(true);
    const alreadyDone = Vue.ref(false);
    const doneData = Vue.ref({});
    const questions = Vue.ref([]);
    const qIdx = Vue.ref(0);
    const score = Vue.ref(0);
    const correct = Vue.ref(0);
    const streak = Vue.ref(0), maxStreak = Vue.ref(0);
    const timeLeft = Vue.ref(20);
    const answered = Vue.ref(false), isCorrect = Vue.ref(false);
    const lastPoints = Vue.ref(0), correctLabel = Vue.ref('');
    const hintUsed = Vue.ref(false), hintText = Vue.ref('');
    const leaderboard = Vue.ref([]);
    const startTime = Vue.ref(0);
    let timer = null;

    const q = Vue.computed(() => questions.value[qIdx.value]);
    const grade = Vue.computed(() => QuizEngine.gradeResult(score.value, questions.value.length));

    function fmtTime(ms) {
      const s = Math.floor((ms || 0) / 1000);
      return Math.floor(s / 60) + '분 ' + (s % 60) + '초';
    }

    async function loadLeaderboard() {
      try {
        const d = await store.apiGet('/api/daily/leaderboard');
        leaderboard.value = (d.leaderboard || []).slice(0, 10);
      } catch(e) { leaderboard.value = []; }
    }

    async function init() {
      const saved = localStorage.getItem(DONE_KEY);
      if (saved) {
        try { doneData.value = JSON.parse(saved); } catch(e) { doneData.value = {}; }
        alreadyDone.value = true;
        loading.value = false;
        await loadLeaderboard();
        return;
      }
      try {
        const d = await store.apiGet('/api/daily');
        questions.value = d.questions || [];
        loading.value = false;
        if (questions.value.length) {
          screen.value = 'game';
          startTime.value = Date.now();
          startTimer();
        }
      } catch(e) {
        showToast('오늘의 퀴즈를 불러올 수 없어요', 'error');
        loading.value = false;
      }
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
      streak.value = 0;
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
      } else {
        correctLabel.value = findCorrectLabel();
        streak.value = 0;
      }
      setTimeout(nextQ, 1300);
    }

    function findCorrectLabel() {
      const c = q.value.choices.find(x =>
        x.id === q.value.correctId || String(x.id) === String(q.value.correctId)
      );
      return c ? c.label : String(q.value.correctId);
    }

    function nextQ() {
      if (qIdx.value + 1 >= questions.value.length) { endGame(); return; }
      qIdx.value++;
      answered.value = false;
      hintUsed.value = false; hintText.value = '';
      startTimer();
    }

    function useHint() {
      if (hintUsed.value || answered.value) return;
      hintUsed.value = true;
      const curr = q.value;
      const correctChoice = curr.choices.find(c =>
        c.id === curr.correctId || String(c.id) === String(curr.correctId)
      );
      if (correctChoice) {
        const label = correctChoice.label;
        const hint = label[0] + label.slice(1).replace(/[^\s]/g, '_');
        hintText.value = '💡 힌트: ' + hint;
      }
    }

    function choiceClass(c) {
      if (!answered.value) return '';
      const cId = c.id; const qId = q.value.correctId;
      const match = cId === qId || String(cId) === String(qId);
      if (match) return 'correct';
      if (isCorrect.value) return 'neutral-fade';
      return 'wrong';
    }

    async function endGame() {
      clearInterval(timer);
      screen.value = 'result';
      const elapsed = Date.now() - startTime.value;
      const result = {
        score: score.value,
        correct: correct.value,
        total: questions.value.length,
        time: elapsed
      };
      // localStorage 저장 (재방문 차단)
      localStorage.setItem(DONE_KEY, JSON.stringify(result));
      // 서버 제출
      try {
        await store.apiPost('/api/daily/submit', result);
      } catch(e) { /* 무시 */ }
      await loadLeaderboard();
    }

    Vue.onMounted(init);
    Vue.onUnmounted(() => clearInterval(timer));

    return { store, screen, loading, alreadyDone, doneData, questions, qIdx, q,
             score, correct, streak, maxStreak, timeLeft, answered, isCorrect,
             lastPoints, correctLabel, hintUsed, hintText, grade, leaderboard,
             todayStr, fmtTime, answer, choiceClass, useHint, nav };
  }
};

// ─── 5. 기존 컴포넌트 객체 패치 (Object.assign) ─────────────────────────────
// pages.js의 const NavBar/QuizPage는 재할당 불가하지만 객체 내용(프로퍼티)은 mutate 가능.
// app.js 수정 없이 NavBar·QuizPage를 교체하는 유일한 non-destructive 방법.
// 이 코드는 pages.js 로드 직후, app.js createApp() 호출 전에 실행된다.
Object.assign(NavBar, NavBarPatched);    // NavBar에 daily 링크 추가
Object.assign(QuizPage, QuizPageExt);   // QuizPage에 힌트·AI추천·업적 추가

// DailyPage는 app.js에서 신규 등록이 필요 — window 프로퍼티로 노출
window.DailyPage = DailyPage;
