"use client";

import { useState, useEffect } from "react";
import { castDivination, type DivinationResult } from "@/lib/api";

const COIN_FACES = [
  { label: "三正", sub: "老阳 ☰", color: "#d4a843" },
  { label: "二正一反", sub: "少阳 ☰", color: "#e8c060" },
  { label: "一正二反", sub: "少阴 ☱", color: "#8a8070" },
  { label: "三反", sub: "老阴 ☱", color: "#5a5040" },
];

function sleep(ms: number) {
  return new Promise<void>((resolve) => setTimeout(resolve, ms));
}

interface Props {
  onComplete: (result: DivinationResult) => void;
}

export default function CoinCaster({ onComplete }: Props) {
  const [round, setRound] = useState(0);
  const [coins, setCoins] = useState<boolean[]>([]);
  const [isFlipping, setIsFlipping] = useState(false);
  const [result, setResult] = useState<DivinationResult | null>(null);
  const [roundResults, setRoundResults] = useState<number[]>([]);
  const [isComplete, setIsComplete] = useState(false);

  // 启动第一次投掷
  useEffect(() => {
    if (round === 0 && !isFlipping && roundResults.length === 0) {
      const timer = setTimeout(() => setRound(1), 600);
      return () => clearTimeout(timer);
    }
  }, [round, isFlipping, roundResults.length]);

  // 主逻辑
  useEffect(() => {
    if (isComplete) return;

    let cancelled = false;

    async function run() {
      if (cancelled) return;
      if (round === 0) return;

      if (round <= 6 && !isFlipping) {
        setIsFlipping(true);
        if (cancelled) return;

        // 随机硬币结果
        const heads = Math.floor(Math.random() * 4);
        const needed: boolean[] =
          heads === 3
            ? [true, true, true]
            : heads === 2
            ? [true, true, false]
            : heads === 1
            ? [true, false, false]
            : [false, false, false];

        const shuffled = [...needed].sort(() => Math.random() - 0.5);
        setCoins(shuffled);

        await sleep(900);
        if (cancelled) return;

        setIsFlipping(false);
        const faceIndex = shuffled.filter(Boolean).length;
        setRoundResults((prev) => [...prev, faceIndex]);
        setRound((r) => r + 1);
      } else if (round === 7 && !result) {
        try {
          const data = await castDivination();
          if (cancelled) return;
          setResult(data);
          setIsComplete(true);
        } catch (e) {
          console.error("占卜失败:", e);
        }
      }
    }

    run();
    return () => {
      cancelled = true;
    };
  }, [round, isFlipping, result, isComplete]);

  // 完成后跳转
  useEffect(() => {
    if (isComplete && result) {
      const timer = setTimeout(() => onComplete(result), 1200);
      return () => clearTimeout(timer);
    }
  }, [isComplete, result, onComplete]);

  const displayRound = Math.min(round, 6);

  return (
    <div className="animate-fade-in space-y-6">
      <div className="glass rounded-2xl p-8">
        <div className="text-center mb-8">
          <h2 className="text-xl font-semibold text-gold mb-1">
            {round <= 6 ? `第 ${displayRound} / 6 次投掷` : "占卜完成"}
          </h2>
          <p className="text-xs text-[var(--color-text-muted)]">
            每次投掷三枚硬币
          </p>
        </div>

        {/* 硬币 */}
        <div className="flex justify-center gap-6 mb-8">
          {[0, 1, 2].map((i) => {
            const coinState = coins[i];
            return (
              <div key={i} className="flex flex-col items-center gap-1">
                <div
                  className={`
                    w-14 h-14 rounded-full flex items-center justify-center text-xl font-bold
                    border-2 transition-all duration-300
                    ${isFlipping ? "animate-coin border-[var(--color-gold)]/50 bg-[var(--color-surface)]" : ""}
                    ${!isFlipping && coinState === true ? "border-[var(--color-gold)] bg-gradient-to-br from-[var(--color-gold)]/20 to-[var(--color-gold-dark)]/20 shadow-[0_0_15px_rgba(212,168,67,0.3)]" : ""}
                    ${!isFlipping && coinState === false ? "border-[var(--color-text-muted)] bg-[var(--color-surface)]" : ""}
                  `}
                >
                  {isFlipping ? (
                    <span className="text-[var(--color-text-muted)]">?</span>
                  ) : coinState === true ? (
                    "☰"
                  ) : coinState === false ? (
                    "☱"
                  ) : null}
                </div>
              </div>
            );
          })}
        </div>

        {/* 当前结果 */}
        {round > 0 && round <= 6 && roundResults[round - 1] !== undefined && !isFlipping && (
          <div className="text-center mb-6 animate-fade-in">
            <div
              className="inline-block px-4 py-2 rounded-lg text-sm"
              style={{
                backgroundColor: `${COIN_FACES[roundResults[round - 1]].color}15`,
                border: `1px solid ${COIN_FACES[roundResults[round - 1]].color}40`,
              }}
            >
              <span style={{ color: COIN_FACES[roundResults[round - 1]].color }}>
                {COIN_FACES[roundResults[round - 1]].label}
              </span>
              {" "}
              <span className="text-[var(--color-text-muted)]">
                {COIN_FACES[roundResults[round - 1]].sub}
              </span>
            </div>
          </div>
        )}

        {/* 进度条 */}
        <div className="flex gap-2 justify-center">
          {Array.from({ length: 6 }).map((_, i) => (
            <div
              key={i}
              className={`
                h-1.5 rounded-full transition-all duration-500
                ${i < roundResults.length
                  ? "bg-[var(--color-gold)] w-6"
                  : i === roundResults.length && isFlipping
                  ? "bg-[var(--color-gold)]/50 w-3"
                  : "bg-[var(--color-border)] w-6"
                }
              `}
            />
          ))}
        </div>
      </div>

      {/* 历史记录 */}
      {roundResults.length > 0 && (
        <div className="glass rounded-2xl p-4">
          <p className="text-xs text-[var(--color-text-muted)] mb-3 text-center">已得爻象</p>
          <div className="space-y-1">
            {roundResults.map((faceIdx, i) => (
              <div key={i} className="flex items-center justify-between text-sm">
                <span className="text-[var(--color-text-muted)]">第 {i + 1} 爻</span>
                <span
                  className="px-3 py-0.5 rounded text-xs"
                  style={{
                    backgroundColor: `${COIN_FACES[faceIdx].color}10`,
                    color: COIN_FACES[faceIdx].color,
                    border: `1px solid ${COIN_FACES[faceIdx].color}30`,
                  }}
                >
                  {COIN_FACES[faceIdx].label} · {COIN_FACES[faceIdx].sub}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
