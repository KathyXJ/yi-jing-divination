"use client";

import { useState } from "react";
import { castDivination, type DivinationResult } from "@/lib/api";

const COIN_FACES = [
  { label: "三正", sub: "老阳", color: "#d4a843", emoji: "☰" },
  { label: "二正一反", sub: "少阳", color: "#e8c060", emoji: "☰" },
  { label: "一正二反", sub: "少阴", color: "#8a8070", emoji: "☱" },
  { label: "三反", sub: "老阴", color: "#5a5040", emoji: "☱" },
];

interface Props {
  onComplete: (result: DivinationResult) => void;
}

// 模拟硬币投掷结果
function throwResult(): { coins: boolean[]; faceIndex: number; face: typeof COIN_FACES[0] } {
  const heads = Math.floor(Math.random() * 4);
  const needed: boolean[] =
    heads === 3 ? [true, true, true] :
    heads === 2 ? [true, true, false] :
    heads === 1 ? [true, false, false] :
                 [false, false, false];
  const shuffled = [...needed].sort(() => Math.random() - 0.5);
  const faceIndex = shuffled.filter(Boolean).length;
  return { coins: shuffled, faceIndex, face: COIN_FACES[faceIndex] };
}

export default function CoinCaster({ onComplete }: Props) {
  const [round, setRound] = useState(0);           // 当前轮次 1~6
  const [phase, setPhase] = useState<"idle" | "animating" | "done">("idle");
  // 当前轮次的三枚硬币状态
  const [coins, setCoins] = useState<boolean[]>([]);
  const [currentFace, setCurrentFace] = useState<typeof COIN_FACES[0] | null>(null);
  // 历史结果
  const [history, setHistory] = useState<typeof COIN_FACES[0][]>([]);
  // API 结果
  const [result, setResult] = useState<DivinationResult | null>(null);
  const [error, setError] = useState("");

  function handleThrow() {
    if (phase === "animating") return;

    const { coins: c, faceIndex, face } = throwResult();

    // 动画：先显示乱转的 ?
    setPhase("animating");
    setCoins([]); // 空 = 显示 ?
    setCurrentFace(null);

    // 600ms 后停止动画，显示结果
    setTimeout(() => {
      setCoins(c);
      setCurrentFace(face);
      setPhase("done");
      setHistory((prev) => [...prev, face]);

      if (round < 6) {
        // 还没投完，准备下一轮
        setTimeout(() => setPhase("idle"), 800);
      } else {
        // 投完了，调用 API
        setTimeout(async () => {
          try {
            const data = await castDivination();
            setResult(data);
            setTimeout(() => onComplete(data), 800);
          } catch (e) {
            setError("占卜失败，请重试");
            setPhase("idle");
          }
        }, 800);
      }
    }, 600);
  }

  function handleStart() {
    setRound(1);
    setHistory([]);
    setResult(null);
    setError("");
    setPhase("idle");
    handleThrow();
  }

  const isLastThrow = round === 6 && phase === "done";

  return (
    <div className="animate-fade-in space-y-6">
      {/* 主面板 */}
      <div className="glass rounded-2xl p-8">
        {/* 标题 */}
        <div className="text-center mb-8">
          <h2 className="text-xl font-semibold text-gold mb-1">
            {round === 0 ? "准备开始" : `第 ${round} / 6 次投掷`}
          </h2>
          <p className="text-xs text-[var(--color-text-muted)]">
            每次投掷三枚硬币，得一爻
          </p>
        </div>

        {/* 硬币区域 */}
        <div className="flex justify-center gap-6 mb-8">
          {[0, 1, 2].map((i) => {
            const coin = coins[i];
            const isAnimating = phase === "animating";
            return (
              <div key={i} className="flex flex-col items-center gap-1">
                <div
                  className={`
                    w-16 h-16 rounded-full flex items-center justify-center
                    text-2xl font-bold border-2 transition-all duration-300
                    ${isAnimating
                      ? "border-[var(--color-gold)]/60 bg-[var(--color-surface)] animate-coin"
                      : coin === true
                      ? "border-[var(--color-gold)] bg-gradient-to-br from-[var(--color-gold)]/20 to-[var(--color-gold-dark)]/20 shadow-[0_0_18px_rgba(212,168,67,0.5)]"
                      : coin === false
                      ? "border-[var(--color-text-muted)] bg-[var(--color-surface)]"
                      : "border-[var(--color-border)] bg-[var(--color-surface)] opacity-40"
                    }
                  `}
                >
                  {isAnimating ? (
                    <span className="text-[var(--color-text-muted)]">?</span>
                  ) : coin === true ? (
                    <span style={{ color: "#d4a843" }}>☰</span>
                  ) : coin === false ? (
                    <span className="text-[var(--color-text-muted)]">☱</span>
                  ) : null}
                </div>
              </div>
            );
          })}
        </div>

        {/* 当前结果提示 */}
        {currentFace && phase === "done" && (
          <div className="text-center mb-6 animate-fade-in">
            <div
              className="inline-flex items-center gap-3 px-5 py-2.5 rounded-xl"
              style={{
                backgroundColor: `${currentFace.color}18`,
                border: `1.5px solid ${currentFace.color}50`,
              }}
            >
              <span className="text-2xl">{currentFace.emoji}</span>
              <div className="text-left">
                <p className="text-sm font-semibold" style={{ color: currentFace.color }}>
                  {currentFace.label}
                </p>
                <p className="text-xs text-[var(--color-text-muted)]">{currentFace.sub}</p>
              </div>
            </div>
          </div>
        )}

        {/* 投掷按钮 */}
        <div className="text-center">
          {round === 0 ? (
            <button
              onClick={handleStart}
              className="px-10 py-3 rounded-xl bg-gradient-to-r from-[var(--color-gold-dark)] to-[var(--color-gold)] text-[var(--color-bg)] font-bold text-lg hover:from-[var(--color-gold)] hover:to-[var(--color-gold-light)] transition-all shadow-[0_0_20px_rgba(212,168,67,0.3)]"
            >
              🎲 开始投掷
            </button>
          ) : phase === "idle" || phase === "done" ? (
            <button
              onClick={() => {
                setRound((r) => Math.min(r + 1, 6));
                if (round < 6) {
                  setCoins([]);
                  setCurrentFace(null);
                  handleThrow();
                }
              }}
              className="px-10 py-3 rounded-xl bg-gradient-to-r from-[var(--color-gold-dark)] to-[var(--color-gold)] text-[var(--color-bg)] font-bold text-lg hover:from-[var(--color-gold)] hover:to-[var(--color-gold-light)] transition-all shadow-[0_0_20px_rgba(212,168,67,0.3)]"
            >
              {round >= 6 ? "查看结果 →" : "投掷第 " + (round + 1) + " 次"}
            </button>
          ) : (
            <div className="text-[var(--color-text-muted)] text-sm animate-pulse">
              投掷中...
            </div>
          )}
        </div>

        {error && (
          <p className="text-center text-red-400 text-sm mt-3">{error}</p>
        )}

        {/* 进度条 */}
        <div className="flex gap-2 justify-center mt-8">
          {Array.from({ length: 6 }).map((_, i) => (
            <div
              key={i}
              className="h-1.5 rounded-full transition-all duration-500"
              style={{
                width: "32px",
                background: i < history.length
                  ? "linear-gradient(90deg, #8b6914, #d4a843)"
                  : i === history.length && (phase === "animating" || phase === "idle")
                  ? "rgba(212,168,67,0.3)"
                  : "var(--color-border)",
                boxShadow: i < history.length ? "0 0 6px rgba(212,168,67,0.5)" : "none",
              }}
            />
          ))}
        </div>
      </div>

      {/* 历史记录 */}
      {history.length > 0 && (
        <div className="glass rounded-2xl p-5">
          <p className="text-xs text-[var(--color-text-muted)] mb-3 text-center">已得爻象</p>
          <div className="space-y-1.5">
            {history.map((face, i) => (
              <div key={i} className="flex items-center justify-between text-sm py-1 border-b border-[var(--color-border)] last:border-0">
                <span className="text-[var(--color-text-muted)] w-16">第 {i + 1} 爻</span>
                <div className="flex items-center gap-2">
                  <span className="text-lg">{face.emoji}</span>
                  <span
                    className="px-3 py-0.5 rounded text-xs"
                    style={{
                      backgroundColor: `${face.color}12`,
                      color: face.color,
                      border: `1px solid ${face.color}30`,
                    }}
                  >
                    {face.label} · {face.sub}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
