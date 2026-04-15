"use client";

import { createContext, useContext, useState, useEffect, ReactNode } from "react";

export type Lang = "zh" | "en";

interface LangContextValue {
  lang: Lang;
  toggleLang: () => void;
}

const LANG_STORAGE_KEY = "ichoose_lang";

const LangContext = createContext<LangContextValue>({
  lang: "en",
  toggleLang: () => {},
});

export function LangProvider({ children }: { children: ReactNode }) {
  const [lang, setLang] = useState<Lang>("en");

  // 初始化时从 localStorage 恢复语言偏好
  useEffect(() => {
    const saved = localStorage.getItem(LANG_STORAGE_KEY);
    if (saved === "zh" || saved === "en") {
      setLang(saved);
    }
  }, []);

  function toggleLang() {
    setLang((prev) => {
      const next = prev === "zh" ? "en" : "zh";
      localStorage.setItem(LANG_STORAGE_KEY, next);
      return next;
    });
  }

  return (
    <LangContext.Provider value={{ lang, toggleLang }}>
      {children}
    </LangContext.Provider>
  );
}

export function useLang() {
  return useContext(LangContext);
}

// ============ 中英文文案 ============

export const TXT = {
  zh: {
    // 通用
    siteName: "周易占卜",
    siteSubtitle: "融合千年智慧 · AI 智能解卦",
    footer: "周易占卜 · 仅供娱乐参考",

    // 首页介绍
    introTitle: "金钱卦占卜法",
    introStep1: "第一步：占卦。",
    introDesc1: "每次投掷三枚硬币，根据正反面获取爻的属性：",
    outcome3positive: "三正为",
    oldYang: "老阳",
    changeYao: "变爻",
    outcome2positive1neg: "二正一反为",
    youngYin: "少阴",
    outcome1positive2neg: "一正二反为",
    youngYang: "少阳",
    outcome3neg: "三反为",
    oldYin: "老阴",
    introDesc2: "投掷六次获得六爻，即可得本卦（描述当前形势）。老阳变阴、老阴变阳，得到之卦（描述未来趋势）。",
    benGua: "本卦",
    descCurrentSituation: "描述当前形势",
    zhiGua: "之卦",
    descFutureTrend: "描述未来趋势",
    introStep2: "第二步：解卦。",
    introDesc3: "结合卦辞和变爻爻辞，便可解释疑难、预测未来。",
    startCasting: "开始占卜",

    // 投掷页
    readyToStart: "准备开始",
    sixYaoSet: "六爻已定",
    tossHint: "每次投掷三枚硬币，得一爻",
    startThrow: "🎲 开始投掷",
    tossing: "投掷中...",
    tossHistory: "已得爻象",
    coinHeads: "正面",
    coinTails: "反面",
    coinHeadsShort: "正",
    coinTailsShort: "反",
    throwN: (n: number) => `第 ${n} 次投掷`,
    tossResultRecord: "投掷结果记录",
    castingImage: "投掷的图像",
    // 硬币面
    face3heads: "三正",
    face2heads1tail: "二正一反",
    face1head2tails: "一正二反",
    face0heads: "三反",
    faceOldYang: "老阳（变爻）",
    faceYoungYin: "少阴",
    faceYoungYang: "少阳",
    faceOldYin: "老阴（变爻）",
    faceOldYangShrt: "老阳",
    faceOldYinShrt: "老阴",
    faceYoungYinShrt: "少阴",
    faceYoungYangShrt: "少阳",
    generating: "解读中...",
    generatingHex: "正在生成卦象...",
    btnGenerate: "🌟 生成卦象",
    btnView: "🔮 查看结果",

    // 结果页
    benGuaLabel: "本卦",
    zhiGuaLabel: "之卦",
    guaCi: "卦辞：",
    noGuaCi: "（无卦辞）",
    changedYaoInterpret: "变爻解读",
    noChanged: "无变爻，主卦象不变，应静观其变",
    questionPlaceholder: "例如：我的事业运如何？",
    questionLabel: "你想问什么？（可选）",
    aiInterpret: "🔮 AI 智能解卦",
    castAgain: "重新占卜",
    aiDecoding: "AI 解卦",
    deepseek: "DeepSeek",
    aiThinking: "AI 正在解读，请稍候…",
    aiThinkHint: "DeepSeek 推理需要数十秒，请耐心等待",
    disclaimer: "占卜结果由程序随机生成，AI 解读仅供参考",
    divSummary: (benLower: string, benUpper: string, benName: string, zhiLower: string, zhiUpper: string, zhiName: string, changed: string) =>
      `此次占卜结果：本卦${benLower}${benUpper}《${benName}》，之卦${zhiLower}${zhiUpper}《${zhiName}》，变爻为${changed}。`,
    askedLabel: "所问：",
    willChangeTo: "将变为",

    // 错误
    divinationFailed: "占卜失败，请重试",
    aiFailed: "AI 解读失败，请检查后端服务",
  },

  en: {
    // 通用
    siteName: "I Ching Divination",
    siteSubtitle: "Ancient Wisdom · AI-Powered Insights",
    footer: "I Ching · For entertainment purposes only",

    // 首页介绍
    introTitle: "Coin Divination Method",
    introStep1: "Step 1: Cast the hexagram.",
    introDesc1: "Toss three coins each time to determine a yao (line):",
    outcome3positive: "3 heads =",
    oldYang: "Old Yang",
    changeYao: "(changing)",
    outcome2positive1neg: "2 heads 1 tail =",
    youngYin: "Young Yin",
    outcome1positive2neg: "1 head 2 tails =",
    youngYang: "Young Yang",
    outcome3neg: "3 tails =",
    oldYin: "Old Yin",
    introDesc2: "Six tosses give you six yao, forming the Original Hexagram (describes your current situation). Old Yang becomes Yin, Old Yin becomes Yang, giving the Changed Hexagram (shows future trends).",
    benGua: "Original Hexagram",
    descCurrentSituation: "(describes your current situation)",
    zhiGua: "Changed Hexagram",
    descFutureTrend: "(shows future trends)",
    introStep2: "Step 2: Interpret.",
    introDesc3: "Combine the hexagram text and changing line readings to gain insight.",
    startCasting: "Begin Divination",

    // 投掷页
    readyToStart: "Ready to Begin",
    sixYaoSet: "Six Lines Complete",
    tossHint: "Toss three coins each time to obtain one yao",
    startThrow: "🎲 Begin Tossing",
    tossing: "Tossing...",
    tossHistory: "Recorded Lines",
    coinHeads: "Heads",
    coinTails: "Tails",
    coinHeadsShort: "H",
    coinTailsShort: "T",
    throwN: (n: number) => `Throw ${n}`,
    tossResultRecord: "Toss Result Record",
    castingImage: "Casting Image",
    // 硬币面
    face3heads: "3 Heads",
    face2heads1tail: "2 Heads 1 Tail",
    face1head2tails: "1 Head 2 Tails",
    face0heads: "3 Tails",
    faceOldYang: "Old Yang (changing)",
    faceYoungYin: "Young Yin",
    faceYoungYang: "Young Yang",
    faceOldYin: "Old Yin (changing)",
    faceOldYangShrt: "Old Yang",
    faceOldYinShrt: "Old Yin",
    faceYoungYinShrt: "Young Yin",
    faceYoungYangShrt: "Young Yang",
    generating: "Interpreting...",
    generatingHex: "Generating hexagram...",
    btnGenerate: "🌟 Generate Hexagram",
    btnView: "🔮 View Results",

    // 结果页
    benGuaLabel: "Original",
    zhiGuaLabel: "Changed",
    guaCi: "Hexagram text: ",
    noGuaCi: "(no text)",
    changedYaoInterpret: "Changing Lines",
    noChanged: "No changing lines — the hexagram remains stable. Observe quietly.",
    questionPlaceholder: "e.g. What about my career?",
    questionLabel: "What would you like to ask? (optional)",
    aiInterpret: "🔮 AI Interpretation",
    castAgain: "Divine Again",
    aiDecoding: "AI Interpretation",
    deepseek: "DeepSeek",
    aiThinking: "AI is interpreting, please wait…",
    aiThinkHint: "DeepSeek reasoning takes ~30 seconds",
    disclaimer: "Divination results are randomly generated; AI interpretation is for reference only.",
    divSummary: (benLower: string, benUpper: string, benName: string, zhiLower: string, zhiUpper: string, zhiName: string, changed: string) =>
      `Divination result: Original ${benLower}${benUpper}《${benName}》, Changed ${zhiLower}${zhiUpper}《${zhiName}》, changing lines: ${changed}.`,
    askedLabel: "Question: ",
    willChangeTo: "Will change to",

    // 错误
    divinationFailed: "Divination failed, please try again",
    aiFailed: "AI interpretation failed, please check backend service",
  },
};

export type TXT = typeof TXT.zh;
