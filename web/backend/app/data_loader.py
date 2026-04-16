"""
加载周易数据文件（从原始 JS 文件解析）
"""
import re
import os
from pathlib import Path
from typing import Dict, List, Any

DATA_DIR = Path(__file__).parent.parent / "data"


def extract_js_array(content: str, var_name: str) -> str:
    """
    从 JS 文件内容中提取指定变量的数组。
    支持 let/const/var 声明，处理换行和嵌套。
    """
    # 找到变量声明的起始位置
    pattern = rf"(?:let|const|var)\s+{var_name}\s*="
    match = re.search(pattern, content)
    if not match:
        raise ValueError(f"Cannot find variable '{var_name}'")
    start = match.end()

    # 从 = 之后开始，找第一个 '['
    i = start
    while i < len(content) and content[i] not in ('[', '{'):
        i += 1
    if i >= len(content):
        raise ValueError(f"Cannot find array/object for '{var_name}'")

    bracket = content[i]
    opener = content[i]
    closer = ']' if opener == '[' else '}'

    # 配对括号，找到对应的闭合括号
    depth = 1
    i += 1
    in_string = False
    string_char = None

    while i < len(content) and depth > 0:
        c = content[i]

        if in_string:
            if c == '\\' and i + 1 < len(content):
                i += 2  # 跳过转义符
                continue
            elif c == string_char:
                in_string = False
        else:
            if c in ('"', "'", '`'):
                in_string = True
                string_char = c
            elif c == opener:
                depth += 1
            elif c == closer:
                depth -= 1

        i += 1

    result = content[start:i]
    # result starts from "= " or "=" ... trim
    result = result.strip()
    if result.startswith('='):
        result = result[1:].strip()
    return result


def js_to_json(js_str: str) -> Any:
    """将简化的 JS 数组/对象转换为合法 JSON"""
    json_str = js_str
    # 1. 处理 JS 对象 key 不带引号的问题
    json_str = re.sub(
        r'([{,]\s*)([a-zA-Z_\u4e00-\u9fff][a-zA-Z0-9_\u4e00-\u9fff]*)\s*:',
        r'\1"\2":',
        json_str
    )
    # 2. 处理尾部多余逗号
    json_str = re.sub(r",\s*([\]}\]])", r"\1", json_str)
    # 3. 处理单引号：先保护双引号字符串，再转单引号
    quote_pattern = r'"[^"\\]*(?:\\.[^"\\]*)*"'
    matches = re.findall(quote_pattern, json_str)
    placeholders = {}
    for i, m in enumerate(matches):
        ph = f"__PH_{i}__"
        placeholders[ph] = m
        json_str = json_str.replace(m, ph, 1)
    json_str = json_str.replace("'", '"')
    for ph, orig in placeholders.items():
        json_str = json_str.replace(ph, orig)
    # 4. 中文引号
    json_str = json_str.replace('\u201c', '"').replace('\u201d', '"').replace('\u2018', "'").replace('\u2019', "'")

    import json as _json
    try:
        return _json.loads(json_str)
    except Exception as e:
        raise ValueError(f"JSON parse error: {e}\nRaw: {js_str[:200]}")


def load_js_data(var_name: str) -> Any:
    """从 data 目录下的同名 JS 文件加载数据"""
    filepath = DATA_DIR / f"{var_name}.js"
    if not filepath.exists():
        # 尝试从 data_loader 所在目录找
        filepath = Path(__file__).parent.parent / "data" / f"{var_name}.js"

    content = filepath.read_text(encoding="utf-8")
    arr_str = extract_js_array(content, var_name)
    return js_to_json(arr_str)


# ─────────── 全局数据缓存 ───────────
_cache: Dict[str, Any] = {}


def get_data() -> Dict[str, Any]:
    """获取所有数据（带缓存）"""
    if not _cache:
        _cache["single_gua"] = load_js_data("singleGuaTable")
        _cache["double_gua"] = load_js_data("doubleGuaTable")
        _cache["remark_table"] = load_js_data("remarkTable")
        _cache["yao_sentence"] = load_js_data("yaoSentenceData")
    return _cache


def get_single_gua_table() -> List[Dict]:
    return get_data()["single_gua"]


def get_double_gua_table() -> List[Dict]:
    return get_data()["double_gua"]


def get_remark_table() -> List[Dict]:
    return get_data()["remark_table"]


def get_yao_sentence() -> List[Dict]:
    return get_data()["yao_sentence"]


# ─────────── 八卦五行表 ───────────
BAGUA_WUXING = {
    "☰": "金",  # 乾
    "☱": "金",  # 兑
    "☲": "火",  # 离
    "☳": "木",  # 震
    "☴": "木",  # 巽
    "☵": "水",  # 坎
    "☶": "土",  # 艮
    "☷": "土",  # 坤
}

# 符号代码→五行
SYMBOL_WUXING = {
    "999": "金",  # 乾
    "996": "金",  # 兑
    "969": "火",  # 离
    "966": "木",  # 震
    "699": "木",  # 巽
    "696": "水",  # 坎
    "669": "土",  # 艮
    "666": "土",  # 坤
}


def get_bagua_wuxing(symbol_code: str) -> str:
    """根据3位单卦代码获取五行"""
    return SYMBOL_WUXING.get(symbol_code, "土")


# ─────────── 月令地支旺衰表（以月令地支为主键） ───────────
# 旺相休囚死：旺=最强，衰最弱
YUELING_WANGXIU = {
    "寅": {"name": "正月", "wuxing": "木", "state": "旺"},
    "卯": {"name": "二月", "wuxing": "木", "state": "帝旺"},
    "辰": {"name": "三月", "wuxing": "土", "state": "衰"},
    "巳": {"name": "四月", "wuxing": "火", "state": "病"},
    "午": {"name": "五月", "wuxing": "火", "state": "帝旺"},
    "未": {"name": "六月", "wuxing": "土", "state": "衰"},
    "申": {"name": "七月", "wuxing": "金", "state": "死"},
    "酉": {"name": "八月", "wuxing": "金", "state": "帝旺"},
    "戌": {"name": "九月", "wuxing": "土", "state": "衰"},
    "亥": {"name": "十月", "wuxing": "水", "state": "病"},
    "子": {"name": "冬月", "wuxing": "水", "state": "帝旺"},
    "丑": {"name": "腊月", "wuxing": "土", "state": "衰"},
}

# 月份(1-12) → 地支
MONTH_TO_ZHIHI = {
    1: "寅", 2: "卯", 3: "辰", 4: "巳",
    5: "午", 6: "未", 7: "申", 8: "酉",
    9: "戌", 10: "亥", 11: "子", 12: "丑",
}


def get_yueling_info(month: int) -> dict:
    """根据月份获取月令信息"""
    dizhi = MONTH_TO_ZHIHI.get(month, "寅")
    return YUELING_WANGXIU.get(dizhi, YUELING_WANGXIU["寅"])


# ─────────── 快速查询 ───────────

def find_gua_by_name(name: str, gua_list: List[Dict]) -> Dict | None:
    """根据卦名查找卦"""
    for g in gua_list:
        if g.get("guaName") == name or g.get("name") == name:
            return g
    return None


def get_gua_info(gua_name: str) -> Dict | None:
    """获取卦的完整信息（卦辞+爻辞）"""
    double_gua = get_double_gua_table()
    remark_table = get_remark_table()
    yao_sentence = get_yao_sentence()

    gua = find_gua_by_name(gua_name, double_gua)
    if not gua:
        return None

    gua_remarks = [r for r in remark_table if r["currentGua"] == gua_name]
    gua_yao_sentences = [y for y in yao_sentence if y["guaName"] == gua_name]

    return {
        "gua_name": gua_name,
        "code": gua["code"],
        "lower_code": gua["lowerCode"],
        "upper_code": gua["upperCode"],
        "remarks": gua_remarks,
        "yao_sentences": gua_yao_sentences,
    }
