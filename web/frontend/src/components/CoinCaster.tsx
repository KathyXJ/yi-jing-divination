"use client";

import { useState, useRef } from "react";
import { computeDivination, type DivinationResult } from "@/lib/api";

// 硬币面颜色配置（与语言无关）
const COIN_FACE_COLORS = [
  { color: "#d4a843", isChange: true },
  { color: "#e8c060", isChange: false },
  { color: "#8a8070", isChange: false },
  { color: "#5a5040", isChange: true },
];

function getCoinFaces(t: {
  face3heads: string; face2heads1tail: string; face1head2tails: string; face0heads: string;
  faceOldYang: string; faceYoungYin: string; faceYoungYang: string; faceOldYin: string;
}) {
  return [
    { label: t.face3heads, sub: t.faceOldYang, ...COIN_FACE_COLORS[0] },
    { label: t.face2heads1tail, sub: t.faceYoungYin, ...COIN_FACE_COLORS[1] },
    { label: t.face1head2tails, sub: t.faceYoungYang, ...COIN_FACE_COLORS[2] },
    { label: t.face0heads, sub: t.faceOldYin, ...COIN_FACE_COLORS[3] },
  ];
}

// 历史记录项（运行时类型）
type HistoryEntry = {
  face: { label: string; sub: string; color: string; isChange: boolean };
  faceIdx: number;
};

interface Props {
  onComplete: (result: DivinationResult) => void;
  lang?: "zh" | "en";
}

type Phase = "idle" | "animating" | "result" | "generating" | "calling";

export default function CoinCaster({ onComplete, lang = "zh" }: Props) {
  const [completed, setCompleted] = useState(0);
  const [phase, setPhase] = useState<Phase>("idle");
  const [coins, setCoins] = useState<boolean[]>([]);
  const [currentFace, setCurrentFace] = useState<typeof coinFaces[0] | null>(null);
  const [currentFaceIdx, setCurrentFaceIdx] = useState<number>(-1);
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const [result, setResult] = useState<DivinationResult | null>(null);
  const [error, setError] = useState("");
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const t = lang === "zh" ? {
    titleIdle: completed === 0 ? "准备开始" : completed >= 6 ? "六爻已定" : `第 ${completed} / 6 次投掷`,
    generating: "解读中...",
    hint: "每次投掷三枚硬币，得一爻",
    btnStart: "🎲 开始投掷",
    btnNext: `投掷第 ${completed + 1} 次`,
    btnView: "🔮 查看结果",
    btnConfirm: completed >= 6 ? "🔮 查看结果" : `确认第 ${completed} 爻 →`,
    btnGenerate: "🌟 生成卦象",
    tossing: "投掷中...",
    history: "已得爻象",
    yaoN: (n: number) => `第 ${n} 爻`,
    errorMsg: "占卜失败，请重试",
    coinHeads: "正面", coinTails: "反面",
    coinHeadsShort: "正", coinTailsShort: "反",
    castingImage: "投掷的图像",
    face3heads: "三正", face2heads1tail: "二正一反", face1head2tails: "一正二反", face0heads: "三反",
    faceOldYang: "老阳（变爻）", faceYoungYin: "少阴", faceYoungYang: "少阳", faceOldYin: "老阴（变爻）",
    faceOldYangShrt: "老阳", faceOldYinShrt: "老阴", faceYoungYinShrt: "少阴", faceYoungYangShrt: "少阳",
  } : {
    titleIdle: completed === 0 ? "Ready to Begin" : completed >= 6 ? "Six Lines Complete" : `Toss ${completed} / 6`,
    generating: "Interpreting...",
    hint: "Toss three coins each time to obtain one yao",
    btnStart: "🎲 Begin Tossing",
    btnNext: `Toss #${completed + 1}`,
    btnView: "🔮 View Results",
    btnConfirm: completed >= 6 ? "🔮 View Results" : `Confirm Line ${completed} →`,
    btnGenerate: "🌟 Generate Hexagram",
    tossing: "Tossing...",
    history: "Recorded Lines",
    yaoN: (n: number) => `Line ${n}`,
    errorMsg: "Divination failed, please try again",
    coinHeads: "Heads", coinTails: "Tails",
    coinHeadsShort: "H", coinTailsShort: "T",
    castingImage: "Casting Image",
    face3heads: "3 Heads", face2heads1tail: "2 Heads 1 Tail", face1head2tails: "1 Head 2 Tails", face0heads: "3 Tails",
    faceOldYang: "Old Yang (changing)", faceYoungYin: "Young Yin", faceYoungYang: "Young Yang", faceOldYin: "Old Yin (changing)",
    faceOldYangShrt: "Old Yang", faceOldYinShrt: "Old Yin", faceYoungYinShrt: "Young Yin", faceYoungYangShrt: "Young Yang",
  };

  const coinFaces = getCoinFaces(t);

  function clearTimer() {
    if (timerRef.current) {
      clearTimeout(timerRef.current);
      timerRef.current = null;
    }
  }

  function doThrow() {
    const heads = Math.floor(Math.random() * 4);
    const needed: boolean[] =
      heads === 3 ? [true, true, true] :
      heads === 2 ? [true, true, false] :
      heads === 1 ? [true, false, false] :
                   [false, false, false];
    const faceIdx = 3 - needed.filter(Boolean).length;
    const face = coinFaces[faceIdx];
    const shuffled = [...needed].sort(() => Math.random() - 0.5);

    setPhase("animating");
    setCoins([]);

    timerRef.current = setTimeout(() => {
      setCoins(shuffled);
      setCurrentFace(face);
      setCurrentFaceIdx(faceIdx);
      setPhase("result");
    }, 800);
  }

  function handleThrow() {
    if (phase !== "idle") return;
    if (completed === 0) {
      setCompleted(1);
    } else {
      setCompleted(completed + 1);
    }
    doThrow();
  }

  function handleConfirm() {
    if (phase !== "result") return;
    clearTimer();

    if (currentFace && currentFaceIdx >= 0) {
      setHistory((prev) => [...prev, { face: currentFace, faceIdx: currentFaceIdx }]);
    }

    if (completed >= 6) {
      setPhase("generating");
    } else {
      setCoins([]);
      setCurrentFace(null);
      setCurrentFaceIdx(-1);
      setPhase("idle");
    }
  }

  function triggerDivination() {
    if (phase !== "generating") return;
    setPhase("calling");
    const faceIndices = history.map((entry) => entry.faceIdx);
    computeDivination(faceIndices)
      .then((data) => {
        setResult(data);
        timerRef.current = setTimeout(() => onComplete(data), 600);
      })
      .catch(() => {
        setError(t.errorMsg);
        setPhase("generating");
      });
  }

  const progress = history.length;

  return (
    <div className="animate-fade-in space-y-6">
      {/* 主面板 */}
      <div className="glass rounded-2xl p-8">
        {/* 标题 */}
        <div className="text-center mb-8">
          <h2 className="text-xl font-semibold text-gold mb-1">
            {phase === "calling"
              ? t.generating
              : t.titleIdle}
          </h2>
          <p className="text-xs text-[var(--color-text-muted)]">
            {t.hint}
          </p>
        </div>

        {/* 硬币 */}
        <p className="text-xs text-[var(--color-text-muted)] text-center mb-4">{t.castingImage}</p>
        <div className="flex justify-center gap-6 mb-8">
          {[0, 1, 2].map((i) => {
            const coin = coins[i];
            const isAnim = phase === "animating";
            return (
              <div key={i} className="flex flex-col items-center gap-1">
                <div
                  className={`
                    w-16 h-16 rounded-full flex flex-col items-center justify-center
                    border-2 transition-all duration-300
                    ${isAnim
                      ? "border-[var(--color-gold)]/60 bg-[var(--color-surface)] animate-coin"
                      : coin === true
                      ? "border-[var(--color-gold)] bg-gradient-to-br from-[var(--color-gold)]/15 to-[var(--color-gold-dark)]/15 shadow-[0_0_18px_rgba(212,168,67,0.5)]"
                      : coin === false
                      ? "border-[var(--color-text-muted)] bg-[var(--color-surface)]"
                      : "border-[var(--color-border)] bg-[var(--color-surface)] opacity-30"
                    }
                  `}
                >
                  {isAnim ? (
                    <span className="text-[var(--color-text-muted)] text-lg">?</span>
                  ) : coin === true ? (
                    <span style={{ color: "#d4a843" }} className="text-xs font-bold">{t.coinHeadsShort}</span>
                  ) : coin === false ? (
                    <span className="text-[var(--color-text-muted)] text-xs font-bold">{t.coinTailsShort}</span>
                  ) : null}
                </div>
                <span className="text-[10px] text-[var(--color-text-muted)]">
                  {isAnim ? "?" : coin === true ? t.coinHeads : coin === false ? t.coinTails : ""}
                </span>
              </div>
            );
          })}
        </div>

        {/* 当前结果 */}
        {currentFace && phase === "result" && (
          <div className="text-center mb-6 animate-fade-in">
            <div
              className="inline-flex items-center gap-3 px-5 py-2.5 rounded-xl"
              style={{
                backgroundColor: `${currentFace.color}18`,
                border: `1.5px solid ${currentFace.color}50`,
              }}
            >
              <div className="text-left">
                <p className="text-sm font-semibold" style={{ color: currentFace.color }}>
                  {currentFace.label}
                </p>
                <p className="text-xs text-[var(--color-text-muted)]">{currentFace.sub}</p>
              </div>
            </div>
          </div>
        )}

        {/* 按钮 */}
        <div className="text-center min-h-[56px] flex items-center justify-center">
          {completed === 0 && phase === "idle" && (
            <button
              onClick={handleThrow}
              className="px-10 py-3 rounded-xl bg-gradient-to-r from-[var(--color-gold-dark)] to-[var(--color-gold)] text-[var(--color-bg)] font-bold text-lg hover:from-[var(--color-gold)] hover:to-[var(--color-gold-light)] transition-all shadow-[0_0_20px_rgba(212,168,67,0.3)]"
            >
              {t.btnStart}
            </button>
          )}

          {phase === "idle" && completed >= 1 && completed < 6 && (
            <button
              onClick={handleThrow}
              className="px-8 py-3 rounded-xl bg-gradient-to-r from-[var(--color-gold-dark)] to-[var(--color-gold)] text-[var(--color-bg)] font-bold text-base hover:from-[var(--color-gold)] hover:to-[var(--color-gold-light)] transition-all shadow-[0_0_20px_rgba(212,168,67,0.3)]"
            >
              {t.btnNext}
            </button>
          )}

          {phase === "idle" && completed >= 6 && (
            <button
              onClick={handleConfirm}
              className="px-10 py-3 rounded-xl bg-gradient-to-r from-[var(--color-gold-dark)] to-[var(--color-gold)] text-[var(--color-bg)] font-bold text-lg hover:from-[var(--color-gold)] hover:to-[var(--color-gold-light)] transition-all shadow-[0_0_20px_rgba(212,168,67,0.3)]"
            >
              {t.btnView}
            </button>
          )}

          {phase === "animating" && (
            <div className="text-[var(--color-text-muted)] text-sm animate-pulse">
              {t.tossing}
            </div>
          )}

          {phase === "result" && (
            <button
              onClick={handleConfirm}
              className="px-8 py-3 rounded-xl bg-gradient-to-r from-[var(--color-gold-dark)] to-[var(--color-gold)] text-[var(--color-bg)] font-bold text-base hover:from-[var(--color-gold)] hover:to-[var(--color-gold-light)] transition-all shadow-[0_0_20px_rgba(212,168,67,0.3)]"
            >
              {t.btnConfirm}
            </button>
          )}

          {phase === "generating" && (
            <button
              onClick={triggerDivination}
              className="px-10 py-3 rounded-xl bg-gradient-to-r from-[var(--color-gold-dark)] to-[var(--color-gold)] text-[var(--color-bg)] font-bold text-lg hover:from-[var(--color-gold)] hover:to-[var(--color-gold-light)] transition-all shadow-[0_0_20px_rgba(212,168,67,0.3)]"
            >
              {t.btnGenerate}
            </button>
          )}

          {phase === "calling" && (
            <div className="text-[var(--color-text-muted)] text-sm animate-pulse">
              {t.generating}
            </div>
          )}
        </div>

        {error && (
          <p className="text-center text-red-400 text-sm mt-2">{error}</p>
        )}

        {/* 进度条 */}
        <div className="flex gap-2 justify-center mt-8">
          {Array.from({ length: 6 }).map((_, i) => (
            <div
              key={i}
              className="h-1.5 rounded-full transition-all duration-500"
              style={{
                width: "32px",
                background: i < progress
                  ? "linear-gradient(90deg, #8b6914, #d4a843)"
                  : i === progress && phase === "animating"
                  ? "rgba(212,168,67,0.4)"
                  : "var(--color-border)",
                boxShadow: i < progress ? "0 0 6px rgba(212,168,67,0.5)" : "none",
              }}
            />
          ))}
        </div>
      </div>

      {/* 历史记录 */}
      {history.length > 0 && (
        <div className="glass rounded-2xl p-5">
          <p className="text-xs text-[var(--color-text-muted)] mb-3 text-center">{t.history}</p>
          <div className="space-y-1.5">
            {[...history].reverse().map((entry, i) => {
              if (!entry.face) return null;
              return (
                <div
                  key={history.length - 1 - i}
                  className="flex items-center justify-between text-sm py-1 border-b border-[var(--color-border)] last:border-0"
                >
                  <span className="text-[var(--color-text-muted)] w-16">{t.yaoN(history.length - i)}</span>
                  <div className="flex items-center gap-2">
                    <span
                      className="px-3 py-0.5 rounded text-xs"
                      style={{
                        backgroundColor: `${entry.face.color}12`,
                        color: entry.face.color,
                        border: `1px solid ${entry.face.color}30`,
                      }}
                    >
                      {entry.face.label}
                    </span>
                    <span className="text-[var(--color-text-muted)] text-xs">{entry.face.sub}</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
