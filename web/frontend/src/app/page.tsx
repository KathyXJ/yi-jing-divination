"use client";

import { useState } from "react";
import { castDivination, interpretWithAI, type DivinationResult } from "@/lib/api";
import GuaDisplay from "@/components/GuaDisplay";
import CoinCaster from "@/components/CoinCaster";
import InterpretationPanel from "@/components/InterpretationPanel";

type Phase = "intro" | "casting" | "result" | "interpreting";

export default function HomePage() {
  const [phase, setPhase] = useState<Phase>("intro");
  const [result, setResult] = useState<DivinationResult | null>(null);
  const [question, setQuestion] = useState("");
  const [interpretation, setInterpretation] = useState<string>("");
  const [error, setError] = useState("");
  const [isLoadingAI, setIsLoadingAI] = useState(false);

  async function handleCastingComplete(castResult: DivinationResult) {
    setResult(castResult);
    setPhase("result");
  }

  async function handleInterpret() {
    if (!result) return;
    setPhase("interpreting");
    setError("");
    setIsLoadingAI(true);
    try {
      const text = await interpretWithAI(result, question);
      setInterpretation(text);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "AI 解读失败，请检查后端服务");
    } finally {
      setIsLoadingAI(false);
    }
  }

  function handleReset() {
    setPhase("intro");
    setResult(null);
    setInterpretation("");
    setQuestion("");
    setError("");
    setIsLoadingAI(false);
  }

  return (
    <main className="min-h-screen flex flex-col items-center">
      {/* Header */}
      <header className="w-full max-w-2xl pt-12 pb-8 text-center">
        <h1 className="text-4xl font-bold text-gold-gradient tracking-widest mb-2">
          周易占卜
        </h1>
        <p className="text-[var(--color-text-muted)] text-sm tracking-wide">
          融合千年智慧 · AI 智能解卦
        </p>
      </header>

      {/* Content */}
      <div className="w-full max-w-2xl px-4 pb-16">
        {phase === "intro" && (
          <IntroPanel onStart={() => setPhase("casting")} />
        )}

        {phase === "casting" && (
          <CoinCaster onComplete={handleCastingComplete} />
        )}

        {phase === "result" && result && (
          <ResultPanel
            result={result}
            question={question}
            onQuestionChange={setQuestion}
            onInterpret={handleInterpret}
            onReset={handleReset}
            error={error}
          />
        )}

        {phase === "interpreting" && result && (
          <InterpretationPanel
            result={result}
            interpretation={interpretation}
            question={question}
            onReset={handleReset}
            isLoading={isLoadingAI}
          />
        )}
      </div>

      {/* Footer */}
      <footer className="fixed bottom-0 w-full text-center py-3 text-xs text-[var(--color-text-muted)] border-t border-[var(--color-border)]">
        周易占卜 · 仅供娱乐参考
      </footer>
    </main>
  );
}

function IntroPanel({ onStart }: { onStart: () => void }) {
  return (
    <div className="animate-fade-in space-y-6">
      <div className="glass rounded-2xl p-6 space-y-4">
        <h2 className="text-xl font-semibold text-gold text-center">
          金钱卦占卜法
        </h2>
        <div className="space-y-3 text-sm text-[var(--color-text)] leading-relaxed">
          <p>
            <span className="text-gold font-semibold">第一步：占卦。</span>
            每次投掷三枚硬币，根据正反面获取爻的属性：
          </p>
          <ul className="list-none pl-4 space-y-1 text-[var(--color-text-muted)]">
            <li>🟡 三正为 <span className="text-gold">老阳</span> → 变爻</li>
            <li>🔴 二正一反为 <span className="text-[var(--color-text)]">少阴</span></li>
            <li>🔵 一正二反为 <span className="text-[var(--color-text)]">少阳</span></li>
            <li>⚫ 三反为 <span className="text-gold">老阴</span> → 变爻</li>
          </ul>
          <p>
            投掷六次获得六爻，即可得
            <span className="text-gold"> 本卦</span>
            （描述当前形势）。老阳变阴、老阴变阳，得到
            <span className="text-gold"> 之卦</span>
            （描述未来趋势）。
          </p>
          <p>
            <span className="text-gold font-semibold">第二步：解卦。</span>
            结合卦辞和变爻爻辞，便可解释疑难、预测未来。
          </p>
        </div>
      </div>

      <button
        onClick={onStart}
        className="w-full py-4 rounded-xl bg-gradient-to-r from-[var(--color-gold-dark)] to-[var(--color-gold)] text-[var(--color-bg)] font-bold text-lg tracking-wider hover:from-[var(--color-gold)] hover:to-[var(--color-gold-light)] transition-all duration-300 hover:shadow-lg hover:shadow-[var(--color-gold)]/30 animate-pulse-gold"
      >
        开始占卜
      </button>
    </div>
  );
}

function ResultPanel({
  result,
  question,
  onQuestionChange,
  onInterpret,
  onReset,
  error,
}: {
  result: DivinationResult;
  question: string;
  onQuestionChange: (q: string) => void;
  onInterpret: () => void;
  onReset: () => void;
  error: string;
}) {
  const { guaxiang, ben_gua, zhi_gua, yaos } = result;

  return (
    <div className="animate-fade-in space-y-6">
      {/* 卦象展示 */}
      <div className="glass rounded-2xl p-6">
        <div className="text-center mb-6">
          <div className="flex justify-center gap-8 items-start">
            <div>
              <p className="text-xs text-[var(--color-text-muted)] mb-2">本卦</p>
              <GuaDisplay gua={guaxiang} yaos={yaos} isZhi={false} />
              <p className="text-2xl font-bold text-gold mt-2">{guaxiang.name}</p>
              <p className="text-xs text-[var(--color-text-muted)] mt-1">
                {guaxiang.lower_symbol}下 + {guaxiang.upper_symbol}上
              </p>
            </div>
            <div className="flex items-center pt-8 text-2xl text-[var(--color-gold-dark)]">→</div>
            <div>
              <p className="text-xs text-[var(--color-text-muted)] mb-2">之卦</p>
              <GuaDisplay gua={zhi_gua} yaos={yaos} isZhi={true} />
              <p className="text-2xl font-bold text-gold mt-2">{zhi_gua.name}</p>
              <p className="text-xs text-[var(--color-text-muted)] mt-1">
                {zhi_gua.lower_symbol}下 + {zhi_gua.upper_symbol}上
              </p>
            </div>
          </div>
        </div>

        {/* 卦辞 */}
        <div className="border-t border-[var(--color-border)] pt-4 mb-4">
          <p className="text-center text-sm text-[var(--color-text)] leading-relaxed">
            <span className="text-[var(--color-text-muted)]">卦辞：</span>
            {ben_gua.sentence || "（无卦辞）"}
          </p>
        </div>

        {/* 变爻 */}
        {result.changed_indices.length > 0 ? (
          <div className="border-t border-[var(--color-border)] pt-4">
            <p className="text-xs text-[var(--color-text-muted)] mb-2">变爻解读</p>
            {result.changed_indices.map((idx) => {
              const yao = yaos[idx];
              return (
                <div key={idx} className="mb-2 p-3 rounded-lg bg-[rgba(212,168,67,0.05)] border border-[var(--color-gold-dark)]/20">
                  <p className="text-gold text-sm font-semibold">{yao.yao_name}</p>
                  <p className="text-sm text-[var(--color-text)] mt-1">{yao.sentence}</p>
                  <p className="text-xs text-[var(--color-text-muted)] mt-1">
                    → 将变为 {yao.future_gua} 之象
                  </p>
                </div>
              );
            })}
          </div>
        ) : (
          <div className="border-t border-[var(--color-border)] pt-4 text-center text-sm text-[var(--color-text-muted)]">
            无变爻，主卦象不变，应静观其变
          </div>
        )}
      </div>

      {/* 问题输入 */}
      <div className="glass rounded-2xl p-6 space-y-4">
        <label className="block">
          <p className="text-sm text-gold mb-2">你想问什么？（可选）</p>
          <textarea
            value={question}
            onChange={(e) => onQuestionChange(e.target.value)}
            placeholder="例如：我的事业运如何？"
            className="w-full bg-[var(--color-bg)] border border-[var(--color-border)] rounded-lg px-4 py-3 text-sm text-[var(--color-text)] placeholder:text-[var(--color-text-muted)] focus:border-[var(--color-gold-dark)] focus:outline-none resize-none"
            rows={2}
          />
        </label>

        {error && (
          <p className="text-red-400 text-sm">{error}</p>
        )}

        <button
          onClick={onInterpret}
          className="w-full py-3 rounded-xl bg-gradient-to-r from-[var(--color-gold-dark)] to-[var(--color-gold)] text-[var(--color-bg)] font-bold hover:from-[var(--color-gold)] hover:to-[var(--color-gold-light)] transition-all"
        >
          🔮 AI 智能解卦
        </button>

        <button
          onClick={onReset}
          className="w-full py-2 text-sm text-[var(--color-text-muted)] hover:text-[var(--color-text)] transition-colors"
        >
          重新占卜
        </button>
      </div>
    </div>
  );
}
