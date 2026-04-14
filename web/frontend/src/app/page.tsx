"use client";

import { useState } from "react";
import { castDivination, interpretWithAI, type DivinationResult } from "@/lib/api";
import GuaDisplay from "@/components/GuaDisplay";
import CoinCaster from "@/components/CoinCaster";
import InterpretationPanel from "@/components/InterpretationPanel";
import { useLang, TXT } from "@/lib/i18n";
import { useAuth } from "@/lib/auth";

type Phase = "intro" | "casting" | "result" | "interpreting";

export default function HomePage() {
  const [phase, setPhase] = useState<Phase>("intro");
  const [result, setResult] = useState<DivinationResult | null>(null);
  const [question, setQuestion] = useState("");
  const [interpretation, setInterpretation] = useState<string>("");
  const [error, setError] = useState("");
  const [isLoadingAI, setIsLoadingAI] = useState(false);
  const { lang, toggleLang } = useLang();
  const { user, isLoading, login, logout } = useAuth();
  const t = TXT[lang];

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
      const text = await interpretWithAI(result, question, lang);
      setInterpretation(text);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : t.aiFailed;
      // AI失败时提示积分未扣除，可重新尝试
      if (msg.includes("AI 解读失败") || msg.includes("AI interpretation failed")) {
        setError(lang === "zh"
          ? "AI 解读失败，积分未扣除。您可以重新尝试。"
          : "AI interpretation failed, no credits deducted. Please try again.");
      } else {
        setError(msg);
      }
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
        <div className="flex items-center justify-center gap-4 mb-2">
          <h1 className="text-4xl font-bold text-gold-gradient tracking-widest">
            {t.siteName}
          </h1>
          {/* Language Toggle */}
          <button
            onClick={toggleLang}
            className="text-xs font-bold rounded-full px-4 py-1.5 bg-gradient-to-r from-[var(--color-gold-dark)] to-[var(--color-gold)] text-[var(--color-bg)] hover:from-[var(--color-gold)] hover:to-[var(--color-gold-light)] transition-all shadow-[0_0_10px_rgba(212,168,67,0.3)] hover:shadow-[0_0_16px_rgba(212,168,67,0.5)]"
          >
            {lang === "zh" ? "EN 中" : "中 EN"}
          </button>
          {/* Login / User */}
          {!isLoading && (
            user ? (
              <button
                onClick={logout}
                className="text-xs font-bold rounded-full px-4 py-1.5 bg-[var(--color-bg)] border border-[var(--color-gold-dark)] text-[var(--color-gold)] hover:bg-[var(--color-gold-dark)] hover:text-[var(--color-bg)] transition-all flex items-center gap-2"
                title={user.email}
              >
                {user.avatar_url && (
                  <img src={user.avatar_url} alt={user.name || ""} className="w-5 h-5 rounded-full" />
                )}
                {user.name || user.email}
              </button>
            ) : (
              <button
                onClick={login}
                className="text-xs font-bold rounded-full px-4 py-1.5 bg-gradient-to-r from-[var(--color-gold-dark)] to-[var(--color-gold)] text-[var(--color-bg)] hover:from-[var(--color-gold)] hover:to-[var(--color-gold-light)] transition-all shadow-[0_0_8px_rgba(212,168,67,0.3)] hover:shadow-[0_0_12px_rgba(212,168,67,0.5)] flex items-center gap-1"
              >
                <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/>
                </svg>
                {lang === "zh" ? "登录" : "Login"}
              </button>
            )
          )}
        </div>
        <p className="text-[var(--color-text-muted)] text-sm tracking-wide">
          {t.siteSubtitle}
        </p>
      </header>

      {/* Content */}
      <div className="w-full max-w-2xl px-4 pb-16">
        {phase === "intro" && (
          <IntroPanel onStart={() => setPhase("casting")} lang={lang} />
        )}

        {phase === "casting" && (
          <CoinCaster onComplete={handleCastingComplete} lang={lang} />
        )}

        {phase === "result" && result && (
          <ResultPanel
            result={result}
            question={question}
            onQuestionChange={setQuestion}
            onInterpret={handleInterpret}
            onReset={handleReset}
            error={error}
            lang={lang}
          />
        )}

        {phase === "interpreting" && result && (
          <InterpretationPanel
            result={result}
            interpretation={interpretation}
            question={question}
            onReset={handleReset}
            isLoading={isLoadingAI}
            lang={lang}
          />
        )}
      </div>

      {/* Footer */}
      <footer className="fixed bottom-0 w-full text-center py-3 text-xs text-[var(--color-text-muted)] border-t border-[var(--color-border)]">
        {t.footer}
      </footer>
    </main>
  );
}

function IntroPanel({ onStart, lang }: { onStart: () => void; lang: "zh" | "en" }) {
  const t = TXT[lang];

  return (
    <div className="animate-fade-in space-y-6">
      <div className="glass rounded-2xl p-6 space-y-4">
        <h2 className="text-xl font-semibold text-gold text-center">
          {t.introTitle}
        </h2>
        <div className="space-y-3 text-sm text-[var(--color-text)] leading-relaxed">
          <p>
            <span className="text-gold font-semibold">{t.introStep1}</span>
            {" "}{t.introDesc1}
          </p>
          <ul className="list-none pl-4 space-y-1 text-[var(--color-text-muted)]">
            <li>
              {t.outcome3positive} <span className="text-gold">{t.oldYang}</span> {t.changeYao}
            </li>
            <li>
              {t.outcome2positive1neg} <span className="text-[var(--color-text)]">{t.youngYin}</span>
            </li>
            <li>
              {t.outcome1positive2neg} <span className="text-[var(--color-text)]">{t.youngYang}</span>
            </li>
            <li>
              {t.outcome3neg} <span className="text-gold">{t.oldYin}</span> {t.changeYao}
            </li>
          </ul>
          <p className="leading-relaxed">
            {t.introDesc2}
          </p>
          <p>
            <span className="text-gold font-semibold">{t.introStep2}</span>
            {" "}{t.introDesc3}
          </p>
        </div>
      </div>

      <button
        onClick={onStart}
        className="w-full py-4 rounded-xl bg-gradient-to-r from-[var(--color-gold-dark)] to-[var(--color-gold)] text-[var(--color-bg)] font-bold text-lg tracking-wider hover:from-[var(--color-gold)] hover:to-[var(--color-gold-light)] transition-all duration-300 hover:shadow-lg hover:shadow-[var(--color-gold)]/30 animate-pulse-gold"
      >
        {t.startCasting}
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
  lang,
}: {
  result: DivinationResult;
  question: string;
  onQuestionChange: (q: string) => void;
  onInterpret: () => void;
  onReset: () => void;
  error: string;
  lang: "zh" | "en";
}) {
  const t = TXT[lang];
  const { guaxiang, ben_gua, zhi_gua, yaos } = result;

  return (
    <div className="animate-fade-in space-y-6">
      {/* 卦象展示 */}
      <div className="glass rounded-2xl p-6">
        <div className="text-center mb-6">
          <div className="flex justify-center gap-8 items-start">
            <div>
              <p className="text-xs text-[var(--color-text-muted)] mb-2">{t.benGuaLabel}</p>
              <GuaDisplay gua={guaxiang} yaos={yaos} isZhi={false} />
              <p className="text-2xl font-bold text-gold mt-2">{guaxiang.name}</p>
              <p className="text-xs text-[var(--color-text-muted)] mt-1">
                {guaxiang.upper_symbol}上 + {guaxiang.lower_symbol}下
              </p>
            </div>
            <div className="flex items-center pt-8 text-2xl text-[var(--color-gold-dark)]">→</div>
            <div>
              <p className="text-xs text-[var(--color-text-muted)] mb-2">{t.zhiGuaLabel}</p>
              <GuaDisplay gua={zhi_gua} yaos={yaos} isZhi={true} />
              <p className="text-2xl font-bold text-gold mt-2">{zhi_gua.name}</p>
              <p className="text-xs text-[var(--color-text-muted)] mt-1">
                {zhi_gua.upper_symbol}上 + {zhi_gua.lower_symbol}下
              </p>
            </div>
          </div>
        </div>

        {/* 卦辞 */}
        <div className="border-t border-[var(--color-border)] pt-4 mb-4">
          <p className="text-center text-sm text-[var(--color-text)] leading-relaxed">
            <span className="text-[var(--color-text-muted)]">{t.guaCi}</span>
            {ben_gua.sentence || t.noGuaCi}
          </p>
        </div>

        {/* 变爻 */}
        {result.changed_indices.length > 0 ? (
          <div className="border-t border-[var(--color-border)] pt-4">
            <p className="text-xs text-[var(--color-text-muted)] mb-2">{t.changedYaoInterpret}</p>
            {result.changed_indices
              .slice()
              .sort((a, b) => b - a)
              .map((idx) => {
                const yao = yaos[idx];
                return (
                  <div key={idx} className="mb-2 p-3 rounded-lg bg-[rgba(212,168,67,0.05)] border border-[var(--color-gold-dark)]/20">
                    <p className="text-gold text-sm font-semibold">{yao.yao_name}</p>
                    <p className="text-sm text-[var(--color-text)] mt-1">{yao.sentence}</p>
                    <p className="text-xs text-[var(--color-text-muted)] mt-1">
                      → {lang === "en" ? "Will change to" : "将变为"} {yao.future_gua}
                    </p>
                  </div>
                );
              })}
          </div>
        ) : (
          <div className="border-t border-[var(--color-border)] pt-4 text-center text-sm text-[var(--color-text-muted)]">
            {t.noChanged}
          </div>
        )}
      </div>

      {/* 问题输入 */}
      <div className="glass rounded-2xl p-6 space-y-4">
        <label className="block">
          <p className="text-sm text-gold mb-2">{t.questionLabel}</p>
          <textarea
            value={question}
            onChange={(e) => onQuestionChange(e.target.value)}
            placeholder={t.questionPlaceholder}
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
          {t.aiInterpret}
        </button>

        <button
          onClick={onReset}
          className="w-full py-2 text-sm text-[var(--color-text-muted)] hover:text-[var(--color-text)] transition-colors"
        >
          {t.castAgain}
        </button>
      </div>
    </div>
  );
}
