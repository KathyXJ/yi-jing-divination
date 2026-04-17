"use client";

import type { DivinationResult } from "@/lib/api";
import { getGuaPinyin, getYaoNameEn } from "@/lib/pinyin";
import { HEXAGRAM_BY_NAME } from "@/lib/hexagrams";

interface Props {
  result: DivinationResult;
  interpretation: string;
  question: string;
  onReset: () => void;
  isLoading?: boolean;
  lang?: "zh" | "en";
}

// 八卦符号
const BAGUA_SYMBOLS: Record<string, string> = {
  "999": "☰", "996": "☱", "969": "☲", "966": "☳",
  "699": "☴", "696": "☵", "669": "☶", "666": "☷",
};
const BAGUA_NAMES: Record<string, string> = {
  "999": "乾", "996": "兑", "969": "离", "966": "震",
  "699": "巽", "696": "坎", "669": "艮", "666": "坤",
};

// 绘制单根爻线
function YaoLine({ value, isChange }: { value: number; isChange: boolean }) {
  const isYang = value === 9 || value === 7;
  return (
    <div className="relative w-full h-4 flex items-center">
      {isYang ? (
        <div
          className="w-full rounded-sm"
          style={{
            height: "3px",
            background: "linear-gradient(90deg, #8b6914, #d4a843, #8b6914)",
            boxShadow: "0 0 4px rgba(212,168,67,0.4)",
          }}
        />
      ) : (
        <div className="w-full flex items-center h-3">
          <div className="w-[48%] border-t-2 border-[#8a8070]" style={{ borderStyle: "solid" }} />
          <div className="w-[4%]" />
          <div className="w-[48%] border-t-2 border-[#8a8070]" style={{ borderStyle: "solid" }} />
        </div>
      )}
      {isChange && (
        <span className="absolute -right-5 text-xs" style={{ color: "#d4a843" }}>⚡</span>
      )}
    </div>
  );
}

// 爻行（用于对齐布局）
function YaoRow({
  yaoName,
  value,
  isChange,
  sentence,
  lang = "zh",
}: {
  yaoName: string;
  value: number;
  isChange: boolean;
  sentence: string;
  lang?: "zh" | "en";
}) {
  return (
    <div className="flex items-center gap-2 py-1 min-h-[24px]">
      <span className="text-xs text-[var(--color-text-muted)] w-8 shrink-0 flex items-center gap-0.5">
        {yaoName}
        {isChange && <span style={{ color: "#d4a843" }}>⚡</span>}
      </span>
      <div className="w-12 shrink-0">
        <YaoLine value={value} isChange={isChange} />
      </div>
      <span className="text-xs text-[var(--color-text)] leading-snug">
        {sentence}
      </span>
    </div>
  );
}

export default function InterpretationPanel({
  result,
  interpretation,
  question,
  onReset,
  isLoading = false,
  lang = "zh",
}: Props) {
  const { ben_gua, zhi_gua, yaos, zhi_yaos, changed_indices } = result;

  const t = {
    zh: {
      benGua: "本卦",
      zhiGua: "之卦",
      resultSummary: (benLower: string, benUpper: string, benName: string, zhiLower: string, zhiUpper: string, zhiName: string, changed: string) =>
        `此次占卜结果：本卦《${benName}》，之卦《${zhiName}》，变爻为${changed}。`,
      askedLabel: "所问：",
      aiTitle: "AI 解卦",
      aiThinking: "AI 正在解读，请稍候…",
      aiThinkHint: "DeepSeek 推理需要数十秒，请耐心等待",
      castAgain: "再次占卜",
      disclaimer: "占卜结果由程序随机生成，AI 解读仅供参考",
      noChanged: "无",
    },
    en: {
      benGua: "Original",
      zhiGua: "Changed",
      resultSummary: (benLower: string, benUpper: string, benName: string, zhiLower: string, zhiUpper: string, zhiName: string, changed: string) =>
        `Divination Result: Original Hexagram《${getGuaPinyin(benName)}》, Changed Hexagram《${getGuaPinyin(zhiName)}》, changing lines: ${changed}.`,
      askedLabel: "Question: ",
      aiTitle: "AI Interpretation",
      aiThinking: "AI is interpreting, please wait…",
      aiThinkHint: "DeepSeek reasoning takes ~30 seconds",
      castAgain: "Divine Again",
      disclaimer: "Divination results are randomly generated; AI interpretation is for reference only.",
      noChanged: "none",
    },
  }[lang];

  const changedNames = changed_indices.length > 0
    ? changed_indices
        .slice()
        .sort((a, b) => b - a)
        .map((i) => lang === "en" ? getYaoNameEn(yaos[i].yao_name) : yaos[i].yao_name)
        .join(lang === "en" ? ", " : "、")
    : t.noChanged;

  const benUpperName = BAGUA_NAMES[ben_gua.upper_code] || "";
  const benLowerName = BAGUA_NAMES[ben_gua.lower_code] || "";
  const zhiUpperName = BAGUA_NAMES[zhi_gua.upper_code] || "";
  const zhiLowerName = BAGUA_NAMES[zhi_gua.lower_code] || "";

  // 按双换行分段（段落分隔），单换行在段内作为换行展示
  const rawParagraphs = interpretation.split(/\n{2,}/);
  // 每个段落再按单换行拆成多行
  const paragraphs = rawParagraphs
    .map((p) => p.split(/\n/).filter((l) => l.trim()))
    .filter((lines) => lines.length > 0);

  return (
    <div className="animate-fade-in space-y-5">

      {/* ===== 左右对称卦象面板 ===== */}
      <div className="glass rounded-2xl p-6">
        <div className="flex items-stretch justify-center gap-4">
          {/* 本卦 */}
          <div className="flex flex-col items-center w-[200px]">
            {/* 标签 */}
            <p className="text-xs text-[var(--color-text-muted)] mb-1">{t.benGua}</p>
            {/* 卦名大字 */}
            <p className="text-2xl font-bold text-gold">
              {ben_gua.name}
              {ben_gua.pinyin && <span className="text-lg text-gold/70 ml-1">{ben_gua.pinyin}</span>}
            </p>
            {/* 卦象符号 + 爻线示意图（变爻标注⚡） */}
            <div className="flex items-center gap-2 mt-1">
              {/* Unicode卦符（大） */}
              <span className="text-5xl font-serif leading-none">
                {HEXAGRAM_BY_NAME[ben_gua.name] || ben_gua.name}
              </span>
              {/* 爻线示意图（从上爻到初爻） */}
              <div className="flex flex-col gap-[1px]">
                {[...yaos].reverse().map((yao, revIdx) => {
                  const actualIdx = 5 - revIdx;
                  const isYang = yao.value === 9 || yao.value === 7;
                  const isChange = changed_indices.includes(actualIdx);
                  return (
                    <div key={revIdx} className="relative w-10 h-3 flex items-center">
                      {isYang ? (
                        <div
                          className="w-full rounded-sm"
                          style={{
                            height: "2px",
                            background: isChange
                              ? "linear-gradient(90deg, #8b6914, #d4a843, #8b6914)"
                              : "#8b6914",
                            boxShadow: isChange ? "0 0 3px rgba(212,168,67,0.5)" : "none",
                          }}
                        />
                      ) : (
                        <div className="relative w-full h-2">
                          <div
                            className="absolute left-0"
                            style={{
                              top: "50%",
                              transform: "translateY(-50%)",
                              width: "44%",
                              borderTop: "2px solid #8a8070",
                            }}
                          />
                          <div
                            className="absolute right-0"
                            style={{
                              top: "50%",
                              transform: "translateY(-50%)",
                              width: "44%",
                              borderTop: "2px solid #8a8070",
                            }}
                          />
                        </div>
                      )}
                      {isChange && (
                        <span
                          className="absolute -right-4 text-amber-400 text-xs"
                          style={{ animation: "pulse-gold 2s ease-in-out infinite" }}
                        >
                          ⚡
                        </span>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
            {/* 卦辞 */}
            {(lang === "en" ? ben_gua.sentence_en : ben_gua.sentence) && (
              <p className="text-xs text-[var(--color-text)] text-center leading-relaxed max-w-36 mt-1">
                《{ben_gua.name}》：{lang === "en" ? ben_gua.sentence_en : ben_gua.sentence}
              </p>
            )}
            {/* 爻辞（从下到上） */}
            <div className="w-full mt-2 space-y-1">
              {[...yaos].map((yao, idx) => {
                const isYang = yao.value === 9 || yao.value === 7;
                const isChange = changed_indices.includes(idx);
                return (
                  <div key={yao.yao_name} className="text-xs text-left flex items-start gap-1">
                    <span className={isYang ? "text-amber-400" : "text-slate-400"}>{yao.yao_name}</span>
                    {isChange && <span className="text-amber-400">⚡</span>}
                    <span className={isYang ? "text-amber-200/80" : "text-slate-300/80"}>
                      {lang === "en" && yao.sentence_en ? yao.sentence_en : yao.sentence}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>

          {/* 箭头 */}
          <div className="flex items-center">
            <span className="text-2xl text-[var(--color-gold-dark)]">→</span>
          </div>

          {/* 之卦 */}
          <div className="flex flex-col items-center w-[200px]">
            {/* 标签 */}
            <p className="text-xs text-[var(--color-text-muted)] mb-1">{t.zhiGua}</p>
            {/* 卦名大字 */}
            <p className="text-2xl font-bold text-gold">
              {zhi_gua.name}
              {zhi_gua.pinyin && <span className="text-lg text-gold/70 ml-1">{zhi_gua.pinyin}</span>}
            </p>
            {/* 卦象符号 */}
            <div className="flex items-center gap-2 mt-1">
              {/* Unicode卦符（大） */}
              <span className="text-5xl font-serif leading-none">
                {HEXAGRAM_BY_NAME[zhi_gua.name] || zhi_gua.name}
              </span>
              {/* 爻线示意图（之卦无变爻，不标注⚡） */}
              <div className="flex flex-col gap-[1px]">
                {[...zhi_yaos].reverse().map((yao, revIdx) => {
                  const isYang = yao.value === 9 || yao.value === 7;
                  return (
                    <div key={revIdx} className="relative w-10 h-3 flex items-center">
                      {isYang ? (
                        <div
                          className="w-full rounded-sm"
                          style={{
                            height: "2px",
                            background: "#8b6914",
                          }}
                        />
                      ) : (
                        <div className="relative w-full h-2">
                          <div
                            className="absolute left-0"
                            style={{
                              top: "50%",
                              transform: "translateY(-50%)",
                              width: "44%",
                              borderTop: "2px solid #8a8070",
                            }}
                          />
                          <div
                            className="absolute right-0"
                            style={{
                              top: "50%",
                              transform: "translateY(-50%)",
                              width: "44%",
                              borderTop: "2px solid #8a8070",
                            }}
                          />
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
            {/* 卦辞 */}
            {(lang === "en" ? zhi_gua.sentence_en : zhi_gua.sentence) && (
              <p className="text-xs text-[var(--color-text)] text-center leading-relaxed max-w-36 mt-1">
                《{zhi_gua.name}》：{lang === "en" ? zhi_gua.sentence_en : zhi_gua.sentence}
              </p>
            )}
            {/* 爻辞（从下到上） */}
            <div className="w-full mt-2 space-y-1">
              {[...zhi_yaos].map((yao, idx) => {
                const isYang = yao.value === 9 || yao.value === 7;
                const isChange = changed_indices.includes(idx);
                return (
                  <div key={yao.yao_name} className="text-xs text-left flex items-start gap-1">
                    <span className={isYang ? "text-amber-400" : "text-slate-400"}>{yao.yao_name}</span>
                    {isChange && <span className="text-amber-400">⚡</span>}
                    <span className={isYang ? "text-amber-200/80" : "text-slate-300/80"}>
                      {lang === "en" && yao.sentence_en ? yao.sentence_en : yao.sentence}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>

      {/* ===== 占卜结果摘要 ===== */}
      <div className="glass rounded-2xl p-5 text-center">
        <p className="text-sm text-[var(--color-text)] leading-relaxed">
          {t.resultSummary(benLowerName, benUpperName, ben_gua.name, zhiLowerName, zhiUpperName, zhi_gua.name, changedNames)}
        </p>
        {question && (
          <p className="text-sm text-[var(--color-text-muted)] mt-2">
            {t.askedLabel}{question}
          </p>
        )}
      </div>

      {/* ===== AI 解读 ===== */}
      <div className="glass rounded-2xl p-6">
        <div className="flex items-center gap-2 mb-4">
          <span className="text-lg">🔮</span>
          <h2 className="text-lg font-semibold text-gold">{t.aiTitle}</h2>
          <span className="text-xs text-[var(--color-text-muted)] ml-auto">DeepSeek</span>
        </div>

        {isLoading ? (
          <div className="flex flex-col items-center justify-center py-12 gap-4">
            <div className="animate-spin text-4xl">☰</div>
            <p className="text-[var(--color-text-muted)] text-sm">{t.aiThinking}</p>
            <p className="text-[var(--color-text-muted)] text-xs">{t.aiThinkHint}</p>
          </div>
        ) : (
          <div className="text-sm text-[var(--color-text)] leading-7 space-y-4">
            {paragraphs.map((paraLines, i) => {
              if (!paraLines || paraLines.length === 0) return null;
              const firstLine = paraLines[0].trim().replace(/\*\*/g, "");
              const isHeading = /^#{1,3}\s*[一二三四五六]、/.test(firstLine)
                || /^[一二三四五六]、/.test(firstLine)
                || /^[①②③④⑤⑥⑦⑧⑨⑩][闪烁智慧古今君子之道]/.test(firstLine);

              if (isHeading) {
                return (
                  <div key={i} className="mt-5 first:mt-0">
                    <p className="text-gold font-semibold text-base leading-relaxed">
                      {firstLine.replace(/^#+\s*/, "")}
                    </p>
                    {paraLines.slice(1).map((line, j) => {
                      const clean = line.trim().replace(/\*\*/g, "");
                      if (!clean) return null;
                      if (/^[①②③④⑤⑥⑦⑧⑨⑩][闪烁智慧古今君子之道]/.test(clean)) {
                        return <p key={j} className="text-gold/80 font-medium mt-2">{clean}</p>;
                      }
                      return <p key={j} className="text-[var(--color-text)] leading-relaxed mt-1">{clean}</p>;
                    })}
                  </div>
                );
              }

              return (
                <div key={i} className="space-y-0.5">
                  {paraLines.map((line, j) => {
                    const clean = line.trim().replace(/\*\*/g, "").replace(/^[-*]\s*/, "");
                    if (!clean) return null;
                    return (
                      <p key={j} className="text-[var(--color-text)] leading-relaxed">
                        {clean}
                      </p>
                    );
                  })}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* ===== 操作按钮 ===== */}
      <div className="space-y-2">
        <button
          onClick={onReset}
          className="w-full py-3 rounded-xl bg-gradient-to-r from-[var(--color-gold-dark)] to-[var(--color-gold)] text-[var(--color-bg)] font-bold hover:from-[var(--color-gold)] hover:to-[var(--color-gold-light)] transition-all"
        >
          {t.castAgain}
        </button>
        <p className="text-center text-xs text-[var(--color-text-muted)]">
          {t.disclaimer}
        </p>
      </div>
    </div>
  );
}
