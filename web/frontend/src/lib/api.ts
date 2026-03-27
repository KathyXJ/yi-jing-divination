// API 调用封装

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || '';

export interface GuaInfo {
  name: string;
  code: string;
  lower_code: string;
  upper_code: string;
  lower_symbol: string;
  upper_symbol: string;
  sentence?: string;
}

export interface YaoDetail {
  position: number;
  yao_name: string;
  value: number;
  type: string;
  is_change: boolean;
  sentence: string;
  future_gua: string;
  symbol?: string;
}

export interface DivinationResult {
  ben_gua: GuaInfo;
  zhi_gua: GuaInfo;
  yaos: YaoDetail[];
  zhi_yaos: YaoDetail[];
  changed_indices: number[];
  total_throws: number;
}

export interface InterpretationRequest {
  divination_result: DivinationResult;
  user_question: string;
}

export async function castDivination(): Promise<DivinationResult> {
  const res = await fetch(`${BASE_URL}/api/divination/cast`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
  });
  if (!res.ok) throw new Error("占卜失败");
  return res.json();
}

export async function interpretWithAI(
  result: DivinationResult,
  question: string
): Promise<string> {
  const res = await fetch(`${BASE_URL}/api/ai/interpret`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      divination_result: result,
      user_question: question,
    }),
  });
  if (!res.ok) throw new Error("AI 解读失败");
  const data = await res.json();
  return data.interpretation;
}
