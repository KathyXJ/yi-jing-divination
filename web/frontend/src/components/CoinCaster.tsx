"use client";

import { useState, useEffect, useRef } from "react";
import { computeDivination, type DivinationResult } from "@/lib/api";

const COIN_FACES = [
  { label: "三正", sub: "老阳（变爻）", color: "#d4a843", isChange: true },
  { label: "二正一反", sub: "少阴", color: "#e8c060", isChange: false },
  { label: "一正二反", sub: "少阳", color: "#8a8070", isChange: false },
  { label: "三反", sub: "老阴（变爻）", color: "#5a5040", isChange: true },
];

// 历史记录项：包含爻象数据和对应的faceIdx
type HistoryEntry = {
  face: typeof COIN_FACES[0];
  faceIdx: number;
};

interface Props {
  onComplete: (result: DivinationResult) => void;
}

type Phase = "idle" | "animating" | "result" | "generating" | "calling";

export default function CoinCaster({ onComplete }: Props) {
  // completed = 已完成的投掷次数 (0~6)
  const [completed, setCompleted] = useState(0);
  const [phase, setPhase] = useState<Phase>("idle");
  const [coins, setCoins] = useState<boolean[]>([]);
  const [currentFace, setCurrentFace] = useState<typeof COIN_FACES[0] | null>(null);
  const [currentFaceIdx, setCurrentFaceIdx] = useState<number>(-1);
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const [result, setResult] = useState<DivinationResult | null>(null);
  const [error, setError] = useState("");
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  function clearTimer() {
    if (timerRef.current) {
      clearTimeout(timerRef.current);
      timerRef.current = null;
    }
  }

  function doThrow() {
    // 随机硬币
    const heads = Math.floor(Math.random() * 4);
    const needed: boolean[] =
      heads === 3 ? [true, true, true] :
      heads === 2 ? [true, true, false] :
      heads === 1 ? [true, false, false] :
                   [false, false, false];
    // faceIdx: 3-正面数，对应 COIN_FACES[0]=3正面, [1]=2正面, [2]=1正面, [3]=0正面
    const faceIdx = 3 - needed.filter(Boolean).length;
    const face = COIN_FACES[faceIdx];
    // shuffled 仅用于动画展示，随机打乱硬币位置
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

  // 点击"开始投掷"或"投掷第X次"
  function handleThrow() {
    if (phase !== "idle") return;

    if (completed === 0) {
      // 第一次投掷
      setCompleted(1);
    } else {
      // 后续投掷：在投掷前递增
      setCompleted(completed + 1);
    }
    doThrow();
  }

  // 确认当前结果
  function handleConfirm() {
    if (phase !== "result") return;
    clearTimer();

    if (currentFace && currentFaceIdx >= 0) {
      setHistory((prev) => [...prev, { face: currentFace, faceIdx: currentFaceIdx }]);
    }

    if (completed >= 6) {
      // 6次全部完成，等待用户主动触发卦象生成
      setPhase("generating");
    } else {
      // 准备下一轮
      setCoins([]);
      setCurrentFace(null);
      setCurrentFaceIdx(-1);
      setPhase("idle");
    }
  }

  // 用户主动触发卦象生成（增加仪式感）
  function triggerDivination() {
    if (phase !== "generating") return;
    setPhase("calling");
    // 提取6次投掷的faceIdx，发送给后端计算卦象
    const faceIndices = history.map((entry) => entry.faceIdx);
    computeDivination(faceIndices)
      .then((data) => {
        setResult(data);
        timerRef.current = setTimeout(() => onComplete(data), 600);
      })
      .catch(() => {
        setError("占卜失败，请重试");
        setPhase("generating");
      });
  }

  // 进度
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
              : completed === 0 && phase === "idle"
              ? "准备开始"
              : completed >= 6
              ? "六爻已定"
              : `第 ${completed} / 6 次投掷`}
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
          {completed === 0 && phase === "idle" && (
            <button
              onClick={handleThrow}
              className="px-10 py-3 rounded-xl bg-gradient-to-r from-[var(--color-gold-dark)] to-[var(--color-gold)] text-[var(--color-bg)] font-bold text-lg hover:from-[var(--color-gold)] hover:to-[var(--color-gold-light)] transition-all shadow-[0_0_20px_rgba(212,168,67,0.3)]"
            >
              🎲 开始投掷
            </button>
          )}

          {/* 投掷按钮：completed 表示已完成次数，+1 表示下一次投掷的编号 */}
          {phase === "idle" && completed >= 1 && completed < 6 && (
            <button
              onClick={handleThrow}
              className="px-8 py-3 rounded-xl bg-gradient-to-r from-[var(--color-gold-dark)] to-[var(--color-gold)] text-[var(--color-bg)] font-bold text-base hover:from-[var(--color-gold)] hover:to-[var(--color-gold-light)] transition-all shadow-[0_0_20px_rgba(212,168,67,0.3)]"
            >
              投掷第 {completed + 1} 次
            </button>
          )}

          {/* 6次全部投完（idle 状态下的查看结果） */}
          {phase === "idle" && completed >= 6 && (
            <button
              onClick={handleConfirm}
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
              onClick={handleConfirm}
              className="px-8 py-3 rounded-xl bg-gradient-to-r from-[var(--color-gold-dark)] to-[var(--color-gold)] text-[var(--color-bg)] font-bold text-base hover:from-[var(--color-gold)] hover:to-[var(--color-gold-light)] transition-all shadow-[0_0_20px_rgba(212,168,67,0.3)]"
            >
              {completed >= 6 ? "🔮 查看结果" : `确认第 ${completed} 爻 →`}
            </button>
          )}

          {phase === "generating" && (
            <button
              onClick={triggerDivination}
              className="px-10 py-3 rounded-xl bg-gradient-to-r from-[var(--color-gold-dark)] to-[var(--color-gold)] text-[var(--color-bg)] font-bold text-lg hover:from-[var(--color-gold)] hover:to-[var(--color-gold-light)] transition-all shadow-[0_0_20px_rgba(212,168,67,0.3)]"
            >
              🌟 生成卦象
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
            {[...history].reverse().map((entry, i) => {
              if (!entry.face) return null;
              return (
                <div
                  key={history.length - 1 - i}
                  className="flex items-center justify-between text-sm py-1 border-b border-[var(--color-border)] last:border-0"
                >
                  <span className="text-[var(--color-text-muted)] w-16">第 {history.length - i} 爻</span>
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
