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

export interface GuaTrigram {
  name: string;
  code?: string;
  lower_code: string;
  upper_code: string;
  lower_symbol: string;
  upper_symbol: string;
}

export interface DivinationResult {
  guaxiang: GuaTrigram;
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

const FETCH_TIMEOUT = 600000; // 600秒超时（DeepSeek AI 解读生成较长内容需要更多时间）

async function fetchWithTimeout(url: string, init?: RequestInit): Promise<Response> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), FETCH_TIMEOUT);
  try {
    const res = await fetch(url, { ...init, signal: controller.signal });
    return res;
  } finally {
    clearTimeout(timeout);
  }
}

/** 随机模拟投掷（保留给测试用） */
export async function castDivination(): Promise<DivinationResult> {
  const res = await fetchWithTimeout(`${BASE_URL}/api/divination/cast`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
  });
  if (!res.ok) throw new Error("占卜失败");
  return res.json();
}

/** 根据用户实际6次投掷结果计算卦象
 * @param throws - 6个投掷的faceIdx值（0-3），对应COIN_FACES数组索引
 *   faceIdx=0 → 三正(老阳,变爻)
 *   faceIdx=1 → 二正一反(少阴)
 *   faceIdx=2 → 一正二反(少阳)
 *   faceIdx=3 → 三反(老阴,变爻)
 */
export async function computeDivination(throws: number[]): Promise<DivinationResult> {
  const res = await fetchWithTimeout(`${BASE_URL}/api/divination/compute`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(throws),
  });
  if (!res.ok) throw new Error("占卜失败");
  return res.json();
}

export async function interpretWithAI(
  result: DivinationResult,
  question: string,
  lang: string = "zh"
): Promise<string> {
  const res = await fetchWithTimeout(`${BASE_URL}/api/ai/interpret`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      divination_result: result,
      user_question: question,
      lang,  // 添加这行
    }),
  });
  if (!res.ok) throw new Error("AI 解读失败，请稍后重试");
  const data = await res.json();
  return data.interpretation;
}
