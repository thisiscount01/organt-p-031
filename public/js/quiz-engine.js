// quiz-engine.js — CineAI 공통 퀴즈 엔진 (UMD)
;(function (root, factory) {
  if (typeof module === "object" && module.exports) { module.exports = factory(); }
  else { root.QuizEngine = factory(); }
}(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";
  function shuffle(arr) {
    const a = arr.slice();
    for (let i = a.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [a[i], a[j]] = [a[j], a[i]];
    }
    return a;
  }
  function pickDistractors(movies, targetId, count) {
    return shuffle(movies.filter(m => m.id !== targetId)).slice(0, count);
  }
  function buildChoices(correct, distractors) {
    return shuffle([correct, ...distractors.slice(0, 3)]);
  }
  function calcScore({ baseScore = 100, timeLimit = 20, timeLeft = 0, streak = 0, hintPenalty = 0 }) {
    const ratio   = timeLimit > 0 ? Math.max(0, Math.min(1, timeLeft / timeLimit)) : 0;
    const timePts = Math.round(baseScore * (0.5 + 0.5 * ratio));
    const streakPts = streak >= 3 ? (streak - 2) * 15 : 0;
    return Math.max(0, timePts + streakPts - hintPenalty);
  }
  function gradeResult(score, total) {
    const pct = total > 0 ? score / (total * 100) : 0;
    if (pct >= 0.90) return { grade: "S", label: "전설", trophy: "🏆" };
    if (pct >= 0.75) return { grade: "A", label: "대단해요!", trophy: "🥇" };
    if (pct >= 0.55) return { grade: "B", label: "잘 했어요!", trophy: "🥈" };
    if (pct >= 0.35) return { grade: "C", label: "좋은 시도!", trophy: "🥉" };
    return { grade: "D", label: "다음엔 더 잘 할 수 있어요!", trophy: "😅" };
  }
  return { shuffle, pickDistractors, buildChoices, calcScore, gradeResult };
}));
