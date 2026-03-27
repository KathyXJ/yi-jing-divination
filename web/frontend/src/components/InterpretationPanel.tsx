"use client";

import type { DivinationResult } from "@/lib/api";

interface Props {
  result: DivinationResult;
  interpretation: string;
  question: string;
  onReset: () => void;
}

export default function InterpretationPanel({
  result,
  interpretation,
  question,
  onReset,
}: Props) {
  const { ben_gua, zhi_gua, changed_indices } = result;

  // 简单的分段解析，将 AI 解读按标题分割
  const sections = interpretation.split(/\n(?=\d+\.|#{1,3}\s)/g);

  return (
    <div className="animate-fade-in space-y-6">
      {/* 卦象摘要 */}
      <div className="glass rounded-2xl p-6">
        <div className="flex items-center justify-between">
          <div className="text-center">
            <p className="text-xs text-[var(--color-text-muted)] mb-1">本卦</p>
            <p className="text-2xl font-bold text-gold">{ben_gua.name}</p>
          </div>
          <div className="text-2xl text-[var(--color-gold-dark)] mx-4">→</div>
          <div className="text-center">
            <p className="text-xs text-[var(--color-text-muted)] mb-1">之卦</p>
            <p className="text-2xl font-bold text-gold">{zhi_gua.name}</p>
          </div>
        </div>
        {question && (
          <div className="mt-4 pt-4 border-t border-[var(--color-border)] text-center">
            <p className="text-xs text-[var(--color-text-muted)]">你所问</p>
            <p className="text-sm text-gold mt-1">{question}</p>
          </div>
        )}
        {changed_indices.length > 0 && (
          <div className="mt-3 text-center">
            <p className="text-xs text-[var(--color-text-muted)]">
              变爻：{changed_indices.map((i) => result.yaos[i].yao_name).join("、")}
            </p>
          </div>
        )}
      </div>

      {/* AI 解读 */}
      <div className="glass rounded-2xl p-6">
        <div className="flex items-center gap-2 mb-4">
          <span className="text-lg">🔮</span>
          <h2 className="text-lg font-semibold text-gold">AI 解卦</h2>
          <span className="text-xs text-[var(--color-text-muted)] ml-auto">DeepSeek</span>
        </div>

        <div className="text-sm text-[var(--color-text)] leading-7 space-y-3">
          {sections.map((section, i) => {
            const trimmed = section.trim();
            if (!trimmed) return null;
            // 检查是否是标题行
            const isHeading = /^\d+\.|\*{1,3}\s/.test(trimmed);
            if (isHeading && trimmed.length < 50) {
              return (
                <p key={i} className="text-gold font-semibold mt-4 first:mt-0">
                  {trimmed.replace(/^#{1,3}\s/, "")}
                </p>
              );
            }
            return (
              <p key={i} className="text-[var(--color-text)]">
                {trimmed}
              </p>
            );
          })}
        </div>
      </div>

      {/* 操作按钮 */}
      <div className="space-y-2">
        <button
          onClick={onReset}
          className="w-full py-3 rounded-xl bg-gradient-to-r from-[var(--color-gold-dark)] to-[var(--color-gold)] text-[var(--color-bg)] font-bold hover:from-[var(--color-gold)] hover:to-[var(--color-gold-light)] transition-all"
        >
          再次占卜
        </button>
        <p className="text-center text-xs text-[var(--color-text-muted)]">
          占卜结果由程序随机生成，AI 解读仅供参考
        </p>
      </div>
    </div>
  );
}
