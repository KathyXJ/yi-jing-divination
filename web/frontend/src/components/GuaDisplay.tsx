"use client";

import type { YaoDetail } from "@/lib/api";

interface GuaDisplayProps {
  gua: {
    name: string;
    lower_code: string;
    upper_code: string;
    lower_symbol: string;
    upper_symbol: string;
  };
  yaos: YaoDetail[];
  isZhi: boolean;
}

// 八卦符号
const BAGUA_SYMBOLS: Record<string, string> = {
  "999": "☰", "996": "☱", "969": "☲", "966": "☳",
  "699": "☴", "696": "☵", "669": "☶", "666": "☷",
};

export default function GuaDisplay({ gua, yaos, isZhi }: GuaDisplayProps) {
  // 爻从下到上，yaos[0]=初爻, yaos[5]=上爻
  // reverse 后从上爻到初爻（上 → 下）绘制
  const displayYaos = isZhi
    ? yaos.map((y) => {
        let val = y.value;
        let isChange = false;
        if (y.value === 9) { val = 6; isChange = false; }
        else if (y.value === 6) { val = 9; isChange = false; }
        return { ...y, value: val, is_change: isChange };
      })
    : yaos;

  const reversed = [...displayYaos].reverse();

  return (
    <div className="flex flex-col gap-[2px] items-center">
      {reversed.map((yao, idx) => {
        const isYang = yao.value === 9 || yao.value === 7;
        const isChange = yao.is_change;

        return (
          <div
            key={idx}
            className="relative w-16 h-4 flex items-center justify-center"
            style={isChange ? { animation: "pulse-gold 2s ease-in-out infinite" } : {}}
          >
            {isYang ? (
              /* 阳爻 — 实线 */
              <div
                className="w-full rounded-sm"
                style={{
                  height: "3px",
                  background: "linear-gradient(90deg, #8b6914, #d4a843, #8b6914)",
                  boxShadow: "0 0 6px rgba(212,168,67,0.5)",
                }}
              />
            ) : (
              /* 阴爻 — 虚线（两段） */
              <div className="relative w-full h-3">
                <div
                  className="absolute left-0"
                  style={{
                    top: "50%",
                    transform: "translateY(-50%)",
                    width: "43%",
                    height: "2px",
                    borderTop: "2px solid #8a8070",
                  }}
                />
                <div
                  className="absolute right-0"
                  style={{
                    top: "50%",
                    transform: "translateY(-50%)",
                    width: "43%",
                    height: "2px",
                    borderTop: "2px solid #8a8070",
                  }}
                />
              </div>
            )}
            {isChange && (
              <span
                className="absolute -right-4 text-xs"
                style={{ color: "#d4a843" }}
              >
                ⚡
              </span>
            )}
          </div>
        );
      })}
    </div>
  );
}
