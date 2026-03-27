"use client";

import { useState, useEffect, useRef } from "react";
import { castDivination, type DivinationResult } from "@/lib/api";

const COIN_FACES = [
  { label: "三正", sub: "老阳（变爻）", color: "#d4a843", isChange: true },
  { label: "二正一反", sub: "少阳", color: "#e8c060", isChange: false },
  { label: "一正二反", sub: "少阴", color: "#8a8070", isChange: false },
  { label: "三反", sub: "老阴（变爻）", color: "#5a5040", isChange: true },
];

interface Props {
  onComplete: (result: DivinationResult) => void;
}

export default function CoinCaster({ onComplete }: Props) {
  const [round, setRound] = useState(0);       // 当前轮次 0=未开始, 1~6
  const [phase, setPhase] = useState<"idle" | "animating" | "result" | "calling">("idle");
  const [coins, setCoins] = useState<boolean[]>([]);
  const [currentFace, setCurrentFace] = useState<typeof COIN_FACES[0] | null>(null);
  const [history, setHistory] = useState<typeof COIN_FACES[0][]>([]);
  const [result, setResult] = useState<DivinationResult | null>(null);
  const [error, setError] = useState("");
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // 清理 timeout
  function clearTimer() {
    if (timerRef.current) {
      clearTimeout(timerRef.current);
      timerRef.current = null;
    }
  }

  // 单次投掷逻辑
  function doThrow() {
    if (phase !== "idle") return;

    // 随机硬币
    const heads = Math.floor(Math.random() * 4);
    const needed: boolean[] =
      heads === 3 ? [true, true, true] :
      heads === 2 ? [true, true, false] :
      heads === 1 ? [true, false, false] :
                   [false, false, false];
    const shuffled = [...needed].sort(() => Math.random() - 0.5);
    const faceIdx = shuffled.filter(Boolean).length;
    const face = COIN_FACES[faceIdx];

    // 动画中
    setPhase("animating");
    setCoins([]);

    // 800ms 后显示结果
    timerRef.current = setTimeout(() => {
      setCoins(shuffled);
      setCurrentFace(face);
      setPhase("result");
    }, 800);
  }

  // 点击"投掷"按钮
  function handleThrowClick() {
    if (phase === "animating") return;

    if (phase === "idle") {
      // 开始新一轮
      const nextRound = round === 0 ? 1 : round + 1;
      setRound(nextRound);
      setHistory([]);
      setResult(null);
      setError("");
      doThrow();
    }
  }

  // 确认当前结果，进入下一轮或完成
  function handleNext() {
    if (phase !== "result") return;

    clearTimer();

    // 记录结果到历史
    if (currentFace) {
      setHistory((prev) => [...prev, currentFace]);
    }

    if (round >= 6) {
      // 6轮已满，直接调用 API 显示结果
      setPhase("calling");
      castDivination()
        .then((data) => {
          setResult(data);
          timerRef.current = setTimeout(() => onComplete(data), 600);
        })
        .catch(() => {
          setError("占卜失败，请重试");
          setPhase("result");
        });
    } else {
      // 准备下一轮
      setRound((r) => r + 1);
      setCoins([]);
      setCurrentFace(null);
      setPhase("idle");
    }
  }

  // 组件卸载清理
  useEffect(() => () => clearTimer(), []);

  // 进度条
  const progress = history.length;

  return (
    <div className="animate-fade-in space-y-6">
      {/* 主面板 */}
      <div className="glass rounded-2xl p-8">
        {/* 标题 */}
        <div className="text-center mb-8">
          <h2 className="text-xl font-semibold text-gold mb-1">
            {phase === "calling"
              ? "解读中..."
              : round === 0
              ? "准备开始"
              : `第 ${Math.min(round, 6)} / 6 次投掷`}
          </h2>
          <p className="text-xs text-[var(--color-text-muted)]">
            每次投掷三枚硬币，得一爻
          </p>
        </div>

        {/* 硬币 */}
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
                    <span style={{ color: "#d4a843" }} className="text-xs font-bold">正</span>
                  ) : coin === false ? (
                    <span className="text-[var(--color-text-muted)] text-xs font-bold">反</span>
                  ) : null}
                </div>
                <span className="text-[10px] text-[var(--color-text-muted)]">
                  {isAnim ? "?" : coin === true ? "正面" : coin === false ? "反面" : ""}
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
          {/* 初始状态 */}
          {phase === "idle" && round === 0 && (
            <button
              onClick={handleThrowClick}
              className="px-10 py-3 rounded-xl bg-gradient-to-r from-[var(--color-gold-dark)] to-[var(--color-gold)] text-[var(--color-bg)] font-bold text-lg hover:from-[var(--color-gold)] hover:to-[var(--color-gold-light)] transition-all shadow-[0_0_20px_rgba(212,168,67,0.3)]"
            >
              🎲 开始投掷
            </button>
          )}

          {/* 投掷按钮（1~5轮） */}
          {phase === "idle" && round > 0 && round < 6 && (
            <button
              onClick={doThrow}
              className="px-8 py-3 rounded-xl bg-gradient-to-r from-[var(--color-gold-dark)] to-[var(--color-gold)] text-[var(--color-bg)] font-bold text-base hover:from-[var(--color-gold)] hover:to-[var(--color-gold-light)] transition-all shadow-[0_0_20px_rgba(212,168,67,0.3)]"
            >
              投掷第 {round + 1} 次
            </button>
          )}

          {/* 6轮投完，显示查看结果 */}
          {phase === "idle" && round >= 6 && (
            <button
              onClick={handleNext}
              className="px-10 py-3 rounded-xl bg-gradient-to-r from-[var(--color-gold-dark)] to-[var(--color-gold)] text-[var(--color-bg)] font-bold text-lg hover:from-[var(--color-gold)] hover:to-[var(--color-gold-light)] transition-all shadow-[0_0_20px_rgba(212,168,67,0.3)]"
            >
              🔮 查看结果
            </button>
          )}

          {phase === "animating" && (
            <div className="text-[var(--color-text-muted)] text-sm animate-pulse">
              投掷中...
            </div>
          )}

          {phase === "result" && (
            <button
              onClick={handleNext}
              className="px-8 py-3 rounded-xl bg-gradient-to-r from-[var(--color-gold-dark)] to-[var(--color-gold)] text-[var(--color-bg)] font-bold text-base hover:from-[var(--color-gold)] hover:to-[var(--color-gold-light)] transition-all shadow-[0_0_20px_rgba(212,168,67,0.3)]"
            >
              {round >= 6 ? "🔮 查看结果" : `确认第 ${round} 爻 →`}
            </button>
          )}

          {phase === "calling" && (
            <div className="text-[var(--color-text-muted)] text-sm animate-pulse">
              正在生成卦象...
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
          <p className="text-xs text-[var(--color-text-muted)] mb-3 text-center">已得爻象</p>
          <div className="space-y-1.5">
            {history.map((face, i) => (
              <div
                key={i}
                className="flex items-center justify-between text-sm py-1 border-b border-[var(--color-border)] last:border-0"
              >
                <span className="text-[var(--color-text-muted)] w-16">第 {i + 1} 爻</span>
                <div className="flex items-center gap-2">
                  <span
                    className="px-3 py-0.5 rounded text-xs"
                    style={{
                      backgroundColor: `${face.color}12`,
                      color: face.color,
                      border: `1px solid ${face.color}30`,
                    }}
                  >
                    {face.label}
                  </span>
                  <span className="text-[var(--color-text-muted)] text-xs">{face.sub}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
