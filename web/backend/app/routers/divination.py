"""
占卜相关 API 路由
"""
from fastapi import APIRouter
from pydantic import BaseModel
from ..divination import perform_divination, yao_to_symbol, compute_hexagram_from_throws
from ..data_loader import get_gua_info, get_single_gua_table, get_double_gua_table

router = APIRouter(prefix="/api/divination", tags=["占卜"])


class DivinationResponse(BaseModel):
    guaxiang: dict
    ben_gua: dict
    zhi_gua: dict
    yaos: list
    zhi_yaos: list
    changed_indices: list
    total_throws: int
    hua_gua: dict | None = None
    divination_time: dict | None = None


class GuaQuery(BaseModel):
    gua_name: str


class ThrowResult(BaseModel):
    """单次投掷结果：faceIdx 对应 COIN_FACES 的索引
    faceIdx=0 → 三正(老阳,变爻), value=9
    faceIdx=1 → 二正一反(少阴), value=8
    faceIdx=2 → 一正二反(少阳), value=7
    faceIdx=3 → 三反(老阴,变爻), value=6
    """
    faceIdx: int


@router.post("/cast", response_model=DivinationResponse)
async def cast_divination():
    """自动占卜：模拟掷六次硬币，返回本卦和之卦"""
    result = perform_divination()
    # 添加爻的符号表示
    for yao in result["yaos"]:
        yao["symbol"] = yao_to_symbol(yao["value"])
    for yao in result["zhi_yaos"]:
        yao["symbol"] = yao_to_symbol(yao["value"])
    return result


@router.post("/compute", response_model=DivinationResponse)
async def compute_divination(throws: list[int]):
    """根据用户实际投掷的6次结果计算卦象"""
    if len(throws) != 6:
        return {"error": "需要 exactly 6 次投掷结果"}
    result = compute_hexagram_from_throws(throws)
    # 添加爻的符号表示
    for yao in result["yaos"]:
        yao["symbol"] = yao_to_symbol(yao["value"])
    for yao in result["zhi_yaos"]:
        yao["symbol"] = yao_to_symbol(yao["value"])
    return result


@router.get("/hexagrams")
async def list_hexagrams():
    """获取全部64卦列表"""
    return get_double_gua_table()


@router.get("/hexagram/{name}")
async def get_hexagram(name: str):
    """获取指定卦的详细信息（含卦辞和爻辞）"""
    info = get_gua_info(name)
    if not info:
        return {"error": f"未找到卦名：{name}"}
    return info


@router.get("/ba-gua")
async def list_ba_gua():
    """获取八卦（单卦）列表"""
    return get_single_gua_table()
