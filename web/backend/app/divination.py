"""
周易占卜核心算法

硬币占卜法：
- 掷三枚硬币，每枚有正反两面
- 3正 → 老阳（☰）→ 变爻
- 2正1反 → 少阳（☰）
- 1正2反 → 少阴（☱）
- 3反 → 老阴（☱）→ 变爻

投掷6次得到6爻，从下往上依次为初爻、二爻、三爻、四爻、五爻、上爻。
老阳变阴，老阴变阳，得到之卦（变卦）。
"""
import random
from typing import List, Dict, Tuple
from .data_loader import (
    get_double_gua_table,
    get_remark_table,
    get_yao_sentence as _get_yao_sentence_table,
    get_single_gua_table,
)

# 爻的属性：9=老阳（变阴），6=少阴，7=少阳，8=老阴（变阳）
YAO_TYPES_BY_HEADS = {
    3: {"value": 9, "type": "lao_yang", "change": True},    # 3正 老阳（变阴）
    2: {"value": 7, "type": "shao_yang", "change": False},  # 2正1反 少阳
    1: {"value": 8, "type": "shao_yin", "change": False},   # 1正2反 少阴
    0: {"value": 6, "type": "lao_yin", "change": True},    # 3反 老阴（变阳）
}

# 6爻位置名称（从上爻到初爻）
YAO_NAMES = ["上九", "九五", "九四", "九三", "九二", "初九",
             "上六", "六五", "六四", "六三", "六二", "初六"]

# 8单卦代码
SINGLE_GUA_CODE = {
    "乾": "999", "兑": "996", "离": "969", "震": "966",
    "巽": "699", "坎": "696", "艮": "669", "坤": "666",
}


def throw_three_coins() -> Dict:
    """掷三枚硬币：统计正（head）数量，决定爻属性"""
    coins = [random.choice([True, False]) for _ in range(3)]  # True=正
    heads = sum(coins)  # 正面数量
    return {**YAO_TYPES_BY_HEADS[heads]}


def simulate_six_throws() -> List[Dict]:
    """模拟掷六次硬币（掷三枚硬币×6次）"""
    return [throw_three_coins() for _ in range(6)]


def yao_values_to_code(yao_list: List[Dict]) -> str:
    """
    将爻列表转换为卦象代码（从初爻到上爻）
    规则：7→9（少阳→阳），8→6（少阴→阴）
    所以最终代码只含 9（阳爻）或 6（阴爻）
    """
    def normalize(v: int) -> int:
        if v in (9, 7):  # 老阳或少阳 → 阳
            return 9
        else:            # 老阴或少阴 → 阴
            return 6
    return "".join(str(normalize(yao["value"])) for yao in yao_list)


def generate_zhi_gua(yao_list: List[Dict]) -> List[Dict]:
    """根据本卦生成之卦：老阳变阴，老阴变阳"""
    zhi_yao_list = []
    for yao in yao_list:
        if yao["value"] == 9:  # 老阳变阴
            zhi_yao_list.append({**yao, "value": 6, "type": "lao_yin_change", "change": False})
        elif yao["value"] == 6:  # 老阴变阳
            zhi_yao_list.append({**yao, "value": 9, "type": "lao_yang_change", "change": False})
        else:
            zhi_yao_list.append({**yao})
    return zhi_yao_list


def find_double_gua_by_code(code: str) -> Dict | None:
    """根据6位代码查找重卦"""
    for g in get_double_gua_table():
        if g["code"] == code:
            return g
    return None


def get_remark(gua_name: str, yao_index: int) -> Dict | None:
    """获取特定卦的特定爻的注释"""
    for r in get_remark_table():
        if r["currentGua"] == gua_name and int(r["yaoIndex"]) == yao_index:
            return r
    return None


def find_yao_sentence(gua_name: str, yao_index: int) -> Dict | None:
    """获取特定卦的特定爻的爻辞"""
    for y in _get_yao_sentence_table():
        if y["guaName"] == gua_name and y["index"] == yao_index:
            return y
    return None


def get_yao_name(yao: Dict) -> str:
    """获取爻的名称"""
    value = yao["value"]
    # 初爻和上爻根据阴阳不同
    yao_names_by_value = {
        9: ["初九", "九二", "九三", "九四", "九五", "上九"],
        7: ["初九", "九二", "九三", "九四", "九五", "上九"],
        8: ["初六", "六二", "六三", "六四", "六五", "上六"],
        6: ["初六", "六二", "六三", "六四", "六五", "上六"],
    }
    return yao_names_by_value.get(value, ["初爻"] * 6)[0]


def perform_divination() -> Dict:
    """
    执行完整占卜流程
    返回占卜结果，包含本卦、之卦、变爻等信息
    """
    # 1. 掷六次硬币
    yao_list = simulate_six_throws()

    # 2. 生成卦象代码
    ben_code = yao_values_to_code(yao_list)  # 本卦代码
    zhi_yao_list = generate_zhi_gua(yao_list)
    zhi_code = yao_values_to_code(zhi_yao_list)  # 之卦代码

    # 3. 查找卦名
    ben_gua = find_double_gua_by_code(ben_code)
    zhi_gua = find_double_gua_by_code(zhi_code)

    if not ben_gua or not zhi_gua:
        raise ValueError(f"卦象代码无效: 本卦={ben_code}, 之卦={zhi_code}")

    # 4. 找出变爻
    changed_yao_indices = [
        i for i, yao in enumerate(yao_list) if yao.get("change", False)
    ]

    # 5. 构建爻的详细信息
    def build_yao_detail(yao: Dict, index: int, is_zhi: bool = False) -> Dict:
        yao_names_map = {
            9: ["初九", "九二", "九三", "九四", "九五", "上九"],
            7: ["初九", "九二", "九三", "九四", "九五", "上九"],
            8: ["初六", "六二", "六三", "六四", "六五", "上六"],
            6: ["初六", "六二", "六三", "六四", "六五", "上六"],
        }
        names = yao_names_map.get(yao["value"], [])
        yao_name = names[index] if index < len(names) else f"第{index+1}爻"

        # 本卦爻的爻辞来自 yaoSentenceData
        src_gua = ben_gua["guaName"]
        yao_s = find_yao_sentence(src_gua, index)

        return {
            "position": index + 1,
            "yao_name": yao_name,
            "value": yao["value"],
            "type": yao["type"],
            "is_change": yao.get("change", False),
            "sentence": yao_s["sentence"] if yao_s else "",
            "future_gua": yao_s["futureGuaName"] if yao_s else "",
        }

    ben_yao_details = [build_yao_detail(yao, i, is_zhi=False) for i, yao in enumerate(yao_list)]
    zhi_yao_details = [build_yao_detail(yao, i, is_zhi=True) for i, yao in enumerate(zhi_yao_list)]

    # 6. 卦辞
    gua_remark = get_remark(ben_gua["guaName"], 0)
    gua_sentence = gua_remark["sentence"] if gua_remark else ""

    return {
        "ben_gua": {
            "name": ben_gua["guaName"],
            "code": ben_gua["code"],
            "lower_code": ben_gua["lowerCode"],
            "upper_code": ben_gua["upperCode"],
            "lower_symbol": _code_to_symbol(ben_gua["lowerCode"]),
            "upper_symbol": _code_to_symbol(ben_gua["upperCode"]),
            "sentence": gua_sentence,
        },
        "zhi_gua": {
            "name": zhi_gua["guaName"],
            "code": zhi_gua["code"],
            "lower_code": zhi_gua["lowerCode"],
            "upper_code": zhi_gua["upperCode"],
            "lower_symbol": _code_to_symbol(zhi_gua["lowerCode"]),
            "upper_symbol": _code_to_symbol(zhi_gua["upperCode"]),
        },
        "yaos": ben_yao_details,
        "zhi_yaos": zhi_yao_details,
        "changed_indices": changed_yao_indices,
        "total_throws": len(yao_list),
    }


def _code_to_symbol(code: str) -> str:
    """将3位代码转换为八卦符号"""
    symbol_map = {
        "999": "☰",  # 乾
        "996": "☱",  # 兑
        "969": "☲",  # 离
        "966": "☳",  # 震
        "699": "☴",  # 巽
        "696": "☵",  # 坎
        "669": "☶",  # 艮
        "666": "☷",  # 坤
    }
    return symbol_map.get(code, "?")


def yao_to_symbol(value: int) -> str:
    """将爻值转换为卦象符号（实线或虚线）"""
    # 老阳(9)=☰实线，少阳(7)=☰实线，少阴(8)=☱虚线，老阴(6)=☱虚线
    if value in (9, 7):
        return "——"  # 阳爻（实线）
    else:
        return "– –"  # 阴爻（虚线）
