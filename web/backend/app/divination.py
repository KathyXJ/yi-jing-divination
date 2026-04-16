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
from datetime import datetime
from typing import List, Dict, Tuple
from .data_loader import (
    get_double_gua_table,
    get_remark_table,
    get_yao_sentence as _get_yao_sentence_table,
    get_single_gua_table,
    get_bagua_wuxing,
    get_yueling_info,
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


# faceIdx (0-3) 到 value 的映射，对应 COIN_FACES
# faceIdx=0 → 三正 → 老阳(9, 变爻)
# faceIdx=1 → 二正一反 → 少阴(8, 不变)
# faceIdx=2 → 一正二反 → 少阳(7, 不变)
# faceIdx=3 → 三反 → 老阴(6, 变爻)
FACEIDX_TO_YAO = {
    0: {"value": 9, "type": "lao_yang", "change": True},
    1: {"value": 8, "type": "shao_yin", "change": False},
    2: {"value": 7, "type": "shao_yang", "change": False},
    3: {"value": 6, "type": "lao_yin", "change": True},
}


def compute_hexagram_from_throws(face_indices: List[int]) -> Dict:
    """
    根据6个投掷结果(faceIdx)计算卦象
    face_indices: 6个 COIN_FACES 索引(0-3)，从第1爻到第6爻(初爻到上爻)
    """
    # 转换为爻列表
    yao_list = [FACEIDX_TO_YAO[fi] for fi in face_indices]

    # 生成卦象代码
    ben_code = yao_values_to_code(yao_list)
    zhi_yao_list = generate_zhi_gua(yao_list)
    zhi_code = yao_values_to_code(zhi_yao_list)

    # 查找卦名
    ben_gua = find_double_gua_by_code(ben_code)
    zhi_gua = find_double_gua_by_code(zhi_code)

    if not ben_gua or not zhi_gua:
        raise ValueError(f"卦象代码无效: 本卦={ben_code}, 之卦={zhi_code}")

    # 找出变爻索引
    changed_yao_indices = [
        i for i, yao in enumerate(yao_list) if yao.get("change", False)
    ]

    # 构建爻详情
    def build_yao_detail(yao: Dict, index: int, src_gua_name: str) -> Dict:
        yao_names_map = {
            9: ["初九", "九二", "九三", "九四", "九五", "上九"],
            7: ["初九", "九二", "九三", "九四", "九五", "上九"],
            8: ["初六", "六二", "六三", "六四", "六五", "上六"],
            6: ["初六", "六二", "六三", "六四", "六五", "上六"],
        }
        names = yao_names_map.get(yao["value"], [])
        yao_name = names[index] if index < len(names) else f"第{index+1}爻"
        yao_s = find_yao_sentence(src_gua_name, index)
        return {
            "position": index + 1,
            "yao_name": yao_name,
            "value": yao["value"],
            "type": yao["type"],
            "is_change": yao.get("change", False),
            "sentence": yao_s["sentence"] if yao_s else "",
            "sentence_en": yao_s.get("sentence_en", "") if yao_s else "",
            "future_gua": yao_s["futureGuaName"] if yao_s else "",
        }

    ben_yao_details = [build_yao_detail(yao, i, ben_gua["guaName"]) for i, yao in enumerate(yao_list)]
    zhi_yao_details = [build_yao_detail(yao, i, zhi_gua["guaName"]) for i, yao in enumerate(zhi_yao_list)]

    # 卦辞
    ben_gua_remark = get_remark(ben_gua["guaName"], 0)
    zhi_gua_remark = get_remark(zhi_gua["guaName"], 0)
    ben_sentence = ben_gua_remark["sentence"] if ben_gua_remark else ""
    zhi_sentence = zhi_gua_remark["sentence"] if zhi_gua_remark else ""

    # 互卦 + 月令
    hua_gua = generate_hua_gua(yao_list)
    now = datetime.now()
    month = now.month
    yueling = get_yueling_info(month)

    # 卦象：保存原始本卦的 trigram（不受后续之卦计算影响）
    # 之卦用 zhi_gua，卦象用 guaxiang（原始 trigram）
    guaxiang = {
        "name": ben_gua["guaName"],
        "pinyin": ben_gua.get("pinyin", ""),
        "lower_code": ben_gua["lowerCode"],
        "upper_code": ben_gua["upperCode"],
        "lower_symbol": _code_to_symbol(ben_gua["lowerCode"]),
        "upper_symbol": _code_to_symbol(ben_gua["upperCode"]),
    }

    return {
        "guaxiang": guaxiang,
        "ben_gua": {
            "name": ben_gua["guaName"],
            "pinyin": ben_gua.get("pinyin", ""),
            "code": ben_gua["code"],
            "lower_code": ben_gua["lowerCode"],
            "upper_code": ben_gua["upperCode"],
            "lower_symbol": _code_to_symbol(ben_gua["lowerCode"]),
            "upper_symbol": _code_to_symbol(ben_gua["upperCode"]),
            "sentence": ben_sentence,
            "wuxing": get_bagua_wuxing(ben_gua["lowerCode"]),
        },
        "zhi_gua": {
            "name": zhi_gua["guaName"],
            "pinyin": zhi_gua.get("pinyin", ""),
            "code": zhi_gua["code"],
            "lower_code": zhi_gua["lowerCode"],
            "upper_code": zhi_gua["upperCode"],
            "lower_symbol": _code_to_symbol(zhi_gua["lowerCode"]),
            "upper_symbol": _code_to_symbol(zhi_gua["upperCode"]),
            "sentence": zhi_sentence,
            "wuxing": get_bagua_wuxing(zhi_gua["upperCode"]),
        },
        "yaos": ben_yao_details,
        "zhi_yaos": zhi_yao_details,
        "changed_indices": changed_yao_indices,
        "total_throws": 6,
        "hua_gua": hua_gua,
        "divination_time": {
            "month": month,
            "lunar_month": yueling["name"],
            "yueling_wuxing": yueling["wuxing"],
            "yueling_state": yueling["state"],
        },
    }


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
        try:
            if r["currentGua"] == gua_name and int(r["yaoIndex"]) == yao_index:
                return r
        except ValueError:
            # yaoIndex is "ALL" or other non-numeric value, skip
            continue
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
    def build_yao_detail(yao: Dict, index: int, src_gua_name: str) -> Dict:
        yao_names_map = {
            9: ["初九", "九二", "九三", "九四", "九五", "上九"],
            7: ["初九", "九二", "九三", "九四", "九五", "上九"],
            8: ["初六", "六二", "六三", "六四", "六五", "上六"],
            6: ["初六", "六二", "六三", "六四", "六五", "上六"],
        }
        names = yao_names_map.get(yao["value"], [])
        yao_name = names[index] if index < len(names) else f"第{index+1}爻"
        yao_s = find_yao_sentence(src_gua_name, index)
        return {
            "position": index + 1,
            "yao_name": yao_name,
            "value": yao["value"],
            "type": yao["type"],
            "is_change": yao.get("change", False),
            "sentence": yao_s["sentence"] if yao_s else "",
            "future_gua": yao_s["futureGuaName"] if yao_s else "",
        }

    ben_yao_details = [build_yao_detail(yao, i, ben_gua["guaName"]) for i, yao in enumerate(yao_list)]
    zhi_yao_details = [build_yao_detail(yao, i, zhi_gua["guaName"]) for i, yao in enumerate(zhi_yao_list)]

    # 6. 卦辞
    ben_gua_remark = get_remark(ben_gua["guaName"], 0)
    zhi_gua_remark = get_remark(zhi_gua["guaName"], 0)
    ben_sentence = ben_gua_remark["sentence"] if ben_gua_remark else ""
    ben_sentence_en = ben_gua_remark.get("sentence_en", "") if ben_gua_remark else ""
    zhi_sentence = zhi_gua_remark["sentence"] if zhi_gua_remark else ""
    zhi_sentence_en = zhi_gua_remark.get("sentence_en", "") if zhi_gua_remark else ""

    # 7. 互卦（仅3爻动时使用）
    hua_gua = generate_hua_gua(yao_list)

    # 8. 月令信息（服务器自动获取当前时间）
    now = datetime.now()
    month = now.month
    yueling = get_yueling_info(month)

    # 卦象：保存原始本卦的 trigram（不受后续之卦计算影响）
    # 之卦用 zhi_gua，卦象用 guaxiang（原始 trigram）
    guaxiang = {
        "name": ben_gua["guaName"],
        "lower_code": ben_gua["lowerCode"],
        "upper_code": ben_gua["upperCode"],
        "lower_symbol": _code_to_symbol(ben_gua["lowerCode"]),
        "upper_symbol": _code_to_symbol(ben_gua["upperCode"]),
    }

    return {
        "guaxiang": guaxiang,
        "ben_gua": {
            "name": ben_gua["guaName"],
            "code": ben_gua["code"],
            "lower_code": ben_gua["lowerCode"],
            "upper_code": ben_gua["upperCode"],
            "lower_symbol": _code_to_symbol(ben_gua["lowerCode"]),
            "upper_symbol": _code_to_symbol(ben_gua["upperCode"]),
            "sentence": ben_sentence,
            "wuxing": get_bagua_wuxing(ben_gua["lowerCode"]),  # 体卦五行
        },
        "zhi_gua": {
            "name": zhi_gua["guaName"],
            "code": zhi_gua["code"],
            "lower_code": zhi_gua["lowerCode"],
            "upper_code": zhi_gua["upperCode"],
            "lower_symbol": _code_to_symbol(zhi_gua["lowerCode"]),
            "upper_symbol": _code_to_symbol(zhi_gua["upperCode"]),
            "sentence": zhi_sentence,
            "wuxing": get_bagua_wuxing(zhi_gua["upperCode"]),  # 用卦五行
        },
        "yaos": ben_yao_details,
        "zhi_yaos": zhi_yao_details,
        "changed_indices": changed_yao_indices,
        "total_throws": len(yao_list),
        "hua_gua": hua_gua,
        "divination_time": {
            "month": month,
            "lunar_month": yueling["name"],
            "yueling_wuxing": yueling["wuxing"],
            "yueling_state": yueling["state"],
        },
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


def _yao_value_to_bagua_symbol(value: int) -> str:
    """将爻值转换为八卦符号（阳→☰，阴→☱）"""
    return "☰" if value in (9, 7) else "☱"


def _bagua_symbols_to_code(s1: str, s2: str, s3: str) -> str:
    """将三个八卦符号转为3位代码：☰=9，☱=6"""
    def sym_to_code(s: str) -> str:
        return "9" if s == "☰" else "6"
    return sym_to_code(s1) + sym_to_code(s2) + sym_to_code(s3)


def generate_hua_gua(yaos: List[Dict]) -> Dict | None:
    """
    生成互卦。
    规则（由用户提供并验证）：
      互卦上卦 = 三爻、四爻、五爻（索引 2、3、4）
      互卦下卦 = 二爻、三爻、四爻（索引 1、2、3）
      互卦代码 = 下卦 + 上卦（lower_code + upper_code）
    验证：鼎卦(699969) → 互卦=夬卦(999996) ✓
    """
    if len(yaos) < 6:
        return None

    upper_vals = [yaos[2]["value"], yaos[3]["value"], yaos[4]["value"]]
    lower_vals = [yaos[1]["value"], yaos[2]["value"], yaos[3]["value"]]

    def vals_to_code(vals):
        return "".join("9" if v in (9, 7) else "6" for v in vals)

    upper_code = vals_to_code(upper_vals)
    lower_code = vals_to_code(lower_vals)
    hugua_code = lower_code + upper_code

    hua_gua = find_double_gua_by_code(hugua_code)
    if not hua_gua:
        return None

    hua_gua_remark = get_remark(hua_gua["guaName"], 0)

    return {
        "name": hua_gua["guaName"],
        "upper_code": upper_code,
        "lower_code": lower_code,
        "upper_symbol": _code_to_symbol(upper_code),
        "lower_symbol": _code_to_symbol(lower_code),
        "sentence": hua_gua_remark["sentence"] if hua_gua_remark else "",
    }



# ─────────── 五行生克 ───────────
WUXING_SHENG = {
    "木": "火", "火": "土", "土": "金", "金": "水", "水": "木",
}
WUXING_KE = {
    "木": "土", "土": "水", "水": "火", "火": "金", "金": "木",
}


def wuxing_shengke(ti: str, yong: str) -> str:
    """判断体用生克关系"""
    if ti == yong:
        return "比和"
    if WUXING_SHENG.get(ti) == yong:
        return "用生体"  # 旺来助体，吉
    if WUXING_KE.get(ti) == yong:
        return "体克用"  # 体主动，能掌控但辛苦
    if WUXING_SHENG.get(yong) == ti:
        return "体生用"  # 泄气，过程消耗但可能成
    if WUXING_KE.get(yong) == ti:
        return "用克体"  # 外界不利，困难较大
    return "关系不明"


def _yueling_modifier(wuxing: str, state: str) -> str:
    """月令旺衰权重描述"""
    if state in ("旺", "帝旺"):
        return f"{wuxing}气充沛"
    elif state == "相":
        return f"{wuxing}气有力"
    elif state == "休":
        return f"{wuxing}气偏弱"
    elif state == "囚":
        return f"{wuxing}气受困"
    elif state == "死":
        return f"{wuxing}气衰绝"
    return wuxing


def yao_to_symbol(value: int) -> str:
    """将爻值转换为卦象符号（实线或虚线）"""
    # 老阳(9)=☰实线，少阳(7)=☰实线，少阴(8)=☱虚线，老阴(6)=☱虚线
    if value in (9, 7):
        return "——"  # 阳爻（实线）
    else:
        return "– –"  # 阴爻（虚线）
