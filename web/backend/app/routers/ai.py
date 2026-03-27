"""
AI 解读 API — 使用 DeepSeek DeepThink 模型
"""
import os
import json
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

router = APIRouter(prefix="/api/ai", tags=["AI 解读"])

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = "https://api.deepseek.com"


def build_interpretation_prompt(divination_result: dict, user_question: str = "") -> str:
    """构建 AI 解读提示词"""
    ben = divination_result["ben_gua"]
    zhi = divination_result["zhi_gua"]
    yaos = divination_result["yaos"]
    zhi_yaos = divination_result["zhi_yaos"]
    changed = divination_result["changed_indices"]

    # 变爻信息
    changed_yao_info = ""
    if changed:
        changed_yaos = [yaos[i] for i in changed]
        changed_yao_info = "本次占卜变爻：\n"
        for yao in changed_yaos:
            changed_yao_info += f"- {yao['yao_name']}：{yao['sentence']} → 未来将变为【{zhi['name']}】之象\n"

    prompt = f"""你是一位精通《周易》的占卜师，请根据以下占卜结果，为用户提供深入浅出的解读。

{'用户的问题：' + user_question if user_question else ''}

【占卜结果】
本卦：《{ben['name']}》
  - 卦象：{'☰' * ben['code'].count('9') if '9' in ben['code'] else '☷' * ben['code'].count('6')}{ben['lower_symbol']}下 + {ben['upper_symbol']}上
  - 卦辞：{ben['sentence']}

之卦（未来之象）：《{zhi['name']}》
  - 象征着事物发展的趋势和结果

变爻（共{len(changed)}个）：
{changed_yao_info if changed_yao_info else '本次占卜无变爻，主卦象不变，应静观其变。'}

请从以下几个维度进行解读：
1. **卦象象征**：本卦《{ben['name']}》的象征意义
2. **当前形势**：结合变爻，分析当前所处的发展阶段
3. **未来趋势**：之卦《{zhi['name']}》预示着什么变化
4. **行动建议**：针对用户的问题，给予具体可行的建议
5. **注意事项**：特别需要留意的风险或警示

请使用古典与当代结合的语言风格，既保持《周易》的智慧底蕴，又让现代人容易理解和运用。回答要有深度，但不要过于晦涩。
"""
    return prompt


class InterpretationRequest(BaseModel):
    divination_result: dict
    user_question: str = ""


class InterpretationResponse(BaseModel):
    interpretation: str
    model: str


@router.post("/interpret", response_model=InterpretationResponse)
async def interpret_divination(req: InterpretationRequest):
    """使用 DeepSeek 对占卜结果进行 AI 解读"""
    if not DEEPSEEK_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="DeepSeek API Key 未配置，请设置 DEEPSEEK_API_KEY 环境变量"
        )

    prompt = build_interpretation_prompt(req.divination_result, req.user_question)

    try:
        client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)

        response = client.chat.completions.create(
            model="deepseek-reasoner",  # DeepSeek 深度思考模型
            messages=[
                {
                    "role": "system",
                    "content": "你是一位精通《周易》的占卜师，拥有数十年易学研究经验，说话富有智慧且温暖。"
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            max_tokens=2048,
            temperature=0.7,
        )

        interpretation = response.choices[0].message.content

        return InterpretationResponse(
            interpretation=interpretation,
            model="deepseek-reasoner"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI 解读失败：{str(e)}")


@router.get("/health")
async def ai_health():
    """检查 AI 服务状态"""
    if not DEEPSEEK_API_KEY:
        return {"status": "unconfigured", "message": "DEEPSEEK_API_KEY 未设置"}
    return {"status": "ready", "model": "deepseek-reasoner"}
