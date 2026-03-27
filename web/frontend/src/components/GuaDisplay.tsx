"use client";

import type { GuaInfo, YaoDetail } from "@/lib/api";

interface GuaDisplayProps {
  gua: GuaInfo;
  yaos: YaoDetail[];
  isZhi: boolean;
}

export default function GuaDisplay({ gua, yaos, isZhi }: GuaDisplayProps) {
  // 爻从下到上排列，yaos[0]=初爻，yaos[5]=上爻
  const displayYaos = isZhi
    ? yaos.map((y, i) => {
        // 之卦的爻：老阳变阴，老阴变阳
        let val = y.value;
        let type = y.type;
        let isChange = false;
        if (y.value === 9) { val = 6; type = "lao_yin_change"; isChange = false; }
        else if (y.value === 6) { val = 9; type = "lao_yang_change"; isChange = false; }
        else { val = y.value; }
        return { ...y, value: val, type, is_change: isChange };
      })
    : yaos;

  return (
    <div className="flex flex-col gap-1 items-center">
      {displayYaos.slice().reverse().map((yao, idx) => {
        const isYang = yao.value === 9 || yao.value === 7;
        const isChange = yao.is_change;
        return (
          <div
            key={idx}
            className={`
              relative w-16 h-4 flex items-center justify-center
              ${isChange ? "animate-pulse-gold rounded" : ""}
            `}
          >
            {isYang ? (
              <div className="line-yang w-full" />
            ) : (
              <div className="relative w-full">
                <div className="line-yin w-[45%] absolute left-0 top-1/2 -translate-y-1/2" />
                <div className="line-yin w-[45%] absolute right-0 top-1/2 -translate-y-1/2" />
              </div>
            )}
            {isChange && (
              <span className="absolute -right-4 text-[var(--color-gold)] text-xs">⚡</span>
            )}
          </div>
        );
      })}
    </div>
  );
}
