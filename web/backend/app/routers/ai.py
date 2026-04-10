"""
AI 解读 API — 使用 DeepSeek DeepThink 模型
"""
import os
import json
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import asyncio
from dotenv import load_dotenv
from ..divination import _code_to_symbol

load_dotenv()

router = APIRouter(prefix="/api/ai", tags=["AI 解读"])

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = "https://api.deepseek.com"


# ─────────── 京房八宫卦表（64卦归属） ───────────
# 格式：宫 -> {五行, 纯卦, 一世, 二世, 三世, 四世, 五世, 游魂, 归魂}
JINGFANG_BAGUA = {
    "乾宫": {
        "五行": "金",
        "纯卦": "乾为天", "一世": "天风姤", "二世": "天山遁",
        "三世": "天地否", "四世": "风地观", "五世": "山地剥",
        "游魂": "火地晋", "归魂": "火天大有",
    },
    "兑宫": {
        "五行": "金",
        "纯卦": "兑为泽", "一世": "泽水困", "二世": "泽地萃",
        "三世": "泽山咸", "四世": "水山蹇", "五世": "地山谦",
        "游魂": "雷山小过", "归魂": "雷泽归妹",
    },
    "离宫": {
        "五行": "火",
        "纯卦": "离为火", "一世": "火山旅", "二世": "火风鼎",
        "三世": "火水未济", "四世": "山水蒙", "五世": "风水涣",
        "游魂": "天水讼", "归魂": "天火同人",
    },
    "震宫": {
        "五行": "木",
        "纯卦": "震为雷", "一世": "雷地豫", "二世": "雷水解",
        "三世": "雷风恒", "四世": "地风升", "五世": "水风井",
        "游魂": "泽风大过", "归魂": "泽雷随",
    },
    "巽宫": {
        "五行": "木",
        "纯卦": "巽为风", "一世": "风天小畜", "二世": "风火家人",
        "三世": "风雷益", "四世": "天雷无妄", "五世": "火雷噬嗑",
        "游魂": "山雷颐", "归魂": "山风蛊",
    },
    "坎宫": {
        "五行": "水",
        "纯卦": "坎为水", "一世": "水泽节", "二世": "水雷屯",
        "三世": "水火既济", "四世": "泽火革", "五世": "雷火丰",
        "游魂": "地火明夷", "归魂": "地水师",
    },
    "艮宫": {
        "五行": "土",
        "纯卦": "艮为山", "一世": "山火贲", "二世": "山天大畜",
        "三世": "山泽损", "四世": "火泽睽", "五世": "天泽履",
        "游魂": "风泽中孚", "归魂": "风山渐",
    },
    "坤宫": {
        "五行": "土",
        "纯卦": "坤为地", "一世": "地雷复", "二世": "地泽临",
        "三世": "地天泰", "四世": "雷天大壮", "五世": "泽天夬",
        "游魂": "水天需", "归魂": "水地比",
    },
}

# 反向查找：卦名 -> (宫名, 五行)
def _find_gua_gong_and_wuxing(gua_name: str):
    """根据卦名查找其所属的宫和五行，支持全称和简称匹配"""
    for gong_name, info in JINGFANG_BAGUA.items():
        for pos in ["纯卦", "一世", "二世", "三世", "四世", "五世", "游魂", "归魂"]:
            full_name = info[pos]
            # 精确匹配或简称匹配（卦名出现在全称末尾，如"履"匹配"天泽履"）
            if full_name == gua_name or full_name.endswith(gua_name) or gua_name.endswith(full_name):
                return gong_name, info["五行"]
            # 进一步处理：去掉"为"字后匹配（如"艮为山"匹配"艮"）
            if full_name.replace("为", "") in gua_name.replace("为", "") or gua_name.replace("为", "") in full_name.replace("为", ""):
                return gong_name, info["五行"]
    return None, None


def _build_tiyong_rule(changed: list, ben: dict, zhi: dict, div_time: dict, zhi_yaos: list, hua_gua: dict = None) -> str:
    """
    根据动爻数量，构建第三步体用生克分析规则文本。
    ben/zhi 包含 wuxing（八卦五行），div_time 包含月令信息。

    规则（修改版）：
    - 0爻动：静卦，体用比和
    - 1爻动：上卦为体，下卦为用；上卦五行与下卦五行判断生克
    - 2爻动：以上爻卦为体，下爻卦为用
    - 3爻动 / 4爻动 / 5爻动 / 6爻全动：
        查京房八宫卦 → 本卦五行为体，之卦五行为用 → 体与用的生克关系
    """
    changed_count = len(changed)
    lunar = div_time.get("lunar_month", "")
    yue_wuxing = div_time.get("yueling_wuxing", "")
    yue_state = div_time.get("yueling_state", "")

    # 八卦符号 → 五行
    SYM_TO_WX = {"☰": "金", "☱": "金", "☲": "火", "☳": "木", "☴": "木", "☵": "水", "☶": "土", "☷": "土"}

    def shengke_text(ti_el: str, yong_el: str) -> str:
        """生克关系文字描述"""
        if ti_el == yong_el:
            return "体用比和（同性相安）"
        if (ti_el, yong_el) in [("木","火"),("火","土"),("土","金"),("金","水"),("水","木")]:
            return f"用生体（{yong_el}生{ti_el}，吉）"
        if (ti_el, yong_el) in [("木","土"),("土","水"),("水","火"),("火","金"),("金","木")]:
            return f"体克用（{ti_el}克{yong_el}，辛苦但能成）"
        if (ti_el, yong_el) in [("火","木"),("土","火"),("金","土"),("水","金"),("木","水")]:
            return f"体生用（{ti_el}生{yong_el}，泄气消耗）"
        if (ti_el, yong_el) in [("土","木"),("水","土"),("火","水"),("金","火"),("木","金")]:
            return f"用克体（{yong_el}克{ti_el}，凶）"
        return f"体{ti_el}，用{yong_el}"

    def yue_state_desc(state: str) -> str:
        if state in ("旺", "帝旺"):
            return "体气充沛，能驾驭变局"
        elif state == "相":
            return "体气有力，能把握机会"
        elif state == "休":
            return "体气偏弱，需要借助外部力量"
        elif state == "囚":
            return "体气受困，驾驭变局能力有限"
        elif state == "死":
            return "体气衰绝，难以抗拒外部压力"
        return "体气平常"

    if changed_count == 0:
        ti = ben.get("wuxing", "土")
        return f"""**【静卦 · 0个动爻】体用分析**
体用关系：本卦《{ben['name']}》整体为体，无对应之用卦（静卦无动爻）。
体卦五行：{ti}（本卦上卦 {ben['upper_symbol']} / 下卦 {ben['lower_symbol']}）
月令：{lunar}（{yue_wuxing}，{yue_state}）
判断：体用比和（静态平衡），事情无内在推动力，宜静观其变，以守为主。"""

    elif changed_count == 1:
        # 1爻动：无动爻的卦为体，有动爻的卦为用
        # 五行：乾兑金、震巽木、坎水、离火、坤艮土
        pos = changed[0] if changed else 0
        # 动爻在下卦(0/1/2) → 上卦(3/4/5)为体；动爻在上卦 → 下卦(0/1/2)为体
        ti_is_upper = pos >= 3
        ti_gua = "上卦" if ti_is_upper else "下卦"
        yong_gua = "下卦" if ti_is_upper else "上卦"
        ti_el = ben["upper_symbol"] if ti_is_upper else ben["lower_symbol"]
        yong_el = ben["lower_symbol"] if ti_is_upper else ben["upper_symbol"]
        # 五行转换：乾兑金、震巽木、坎水、离火、坤艮土
        GUA_WUXING = {
            "☰": "金", "☱": "金",   # 乾兑
            "☳": "木", "☴": "木",   # 震巽
            "☵": "水",              # 坎
            "☲": "火",              # 离
            "☷": "土", "☶": "土",   # 坤艮
        }
        ti = GUA_WUXING.get(ti_el, "土")
        yong = GUA_WUXING.get(yong_el, "火")
        return f"""**【一爻动】体用分析**
体用关系：动爻位于本卦「{yong_gua}」，该卦为用；无动爻的「{ti_gua}」为体。
体卦五行：{ti}（{ti_gua} {ti_el}）
用卦五行：{yong}（{yong_gua} {yong_el}）
月令：{lunar}（{yue_wuxing}，{yue_state}）
体用生克：{shengke_text(ti, yong)}
月令权重：{yue_state_desc(yue_state)}。"""

    elif changed_count == 2:
        # 2爻动：无动爻的卦为体，有动爻的卦为用（或以上位动爻所在的卦为用）
        # 五行：乾兑金、震巽木、坎水、离火、坤艮土
        all_positions = set(range(6))
        static_set = all_positions - set(changed)  # 无动爻的卦
        # 体：无动爻的那个卦（只有一种可能：两个动爻同在上卦或同在下卦）
        # 用：有动爻的卦
        GUA_WUXING = {
            "☰": "金", "☱": "金", "☳": "木", "☴": "木",
            "☵": "水", "☲": "火", "☷": "土", "☶": "土",
        }
        # 找静爻在哪一卦
        static_in_lower = sum(1 for p in static_set if p < 3)
        # 如果两个动爻都在同一卦（下卦0/1/2 或 上卦3/4/5），则体在另一卦
        lower_changed = sum(1 for p in changed if p < 3)
        upper_changed = len(changed) - lower_changed
        if lower_changed == 0:
            # 两个动爻都在上卦 → 下卦为体，上卦为用
            ti_gua, yong_gua = "下卦", "上卦"
            ti_el, yong_el = ben["lower_symbol"], ben["upper_symbol"]
        elif upper_changed == 0:
            # 两个动爻都在下卦 → 上卦为体，下卦为用
            ti_gua, yong_gua = "上卦", "下卦"
            ti_el, yong_el = ben["upper_symbol"], ben["lower_symbol"]
        else:
            # 两个动爻分别在上卦和下卦 → 以下卦为体，上卦为用（以上位动爻所在卦为用）
            ti_gua, yong_gua = "下卦", "上卦"
            ti_el, yong_el = ben["lower_symbol"], ben["upper_symbol"]

        ti = GUA_WUXING.get(ti_el, "土")
        yong = GUA_WUXING.get(yong_el, "火")
        pos_name = {0: "初爻", 1: "二爻", 2: "三爻", 3: "四爻", 4: "五爻", 5: "上爻"}
        ti_pos = "/".join(pos_name.get(p, "?") for p in sorted(static_set))
        yong_pos = "/".join(pos_name.get(p, "?") for p in sorted(changed))
        return f"""**【二爻动】体用分析**
体用关系：无动爻的卦「{ti_gua}」（{ti_pos}）为体，有动爻的卦「{yong_gua}」（{yong_pos}）为用。
体卦五行：{ti}（{ti_gua} {ti_el}）
用卦五行：{yong}（{yong_gua} {yong_el}）
月令：{lunar}（{yue_wuxing}，{yue_state}）
体用生克：{shengke_text(ti, yong)}
月令权重：{yue_state_desc(yue_state)}。"""

    elif changed_count in (3, 4, 5, 6):
        # 3爻动及以上：查京房八宫卦，本卦五行为体，之卦五行为用
        ben_gong, ben_gong_wx = _find_gua_gong_and_wuxing(ben["name"])
        zhi_gong, zhi_gong_wx = _find_gua_gong_and_wuxing(zhi["name"])
        ti = ben_gong_wx or ben.get("wuxing", "土")
        yong = zhi_gong_wx or zhi.get("wuxing", "火")

        if changed_count == 3:
            hua_name = hua_gua.get("name", "（互卦）") if hua_gua else "（无互卦数据）"
            return f"""**【三爻动】体用分析**
体用关系：查京房八宫卦，本卦「{ben['name']}」属{ben_gong}（{ti}），体；之卦「{zhi['name']}」属{zhi_gong or '未知'}（{yong}），用。
体卦五行：{ti}（{ben_gong}宫主）
用卦五行：{yong}（{zhi_gong or '未知'}宫之卦）
月令：{lunar}（{yue_wuxing}，{yue_state}）
体用生克：{shengke_text(ti, yong)}
月令权重：{yue_state_desc(yue_state)}。
重点：以本卦卦辞为"现状"，以之卦卦辞为"归宿"，互卦《{hua_name}》用于观察演变中间过程。"""

        elif changed_count in (4, 5):
            all_positions = set(range(6))
            changed_set = set(changed)
            static_positions = sorted(all_positions - changed_set)
            static_in_lower = sum(1 for p in static_positions if p < 3)
            static_in_upper = len(static_positions) - static_in_lower
            ti_gua = "下卦" if static_in_lower >= static_in_upper else "上卦"
            return f"""**【{changed_count}爻动】体用分析**
体用关系：查京房八宫卦，本卦「{ben['name']}」属{ben_gong}（{ti}），体；之卦「{zhi['name']}」属{zhi_gong or '未知'}（{yong}），用。
体卦五行：{ti}（{ben_gong}宫主）
用卦五行：{yong}（{zhi_gong or '未知'}宫之卦）
月令：{lunar}（{yue_wuxing}，{yue_state}）
体用生克：{shengke_text(ti, yong)}
月令权重：{yue_state_desc(yue_state)}。
静爻是变局中唯一可以把握的"定数"，{static_positions}位（共{len(static_positions)}个静爻），以下位（初爻方向）的静爻为根基。"""

        else:  # 6爻全动
            if ben["name"] == "乾":
                return f"""**【六爻全动 · 乾 · 用九】**
体用关系：查京房八宫卦，本卦「{ben['name']}」属{ben_gong}（{ti}），体；之卦「{zhi['name']}」属{zhi_gong or '未知'}（{yong}），用。
体卦五行：{ti}，用卦五行：{yong}，体用生克：{shengke_text(ti, yong)}。
操作：遵循"用九"——"见群龙无首，吉"。本卦六爻全动，旧格局完全瓦解，体用关系转化为阴阳终始的大循环。
解读：阳极转阴，事物进入全新阶段，应顺变而行，不强求主导，顺势而为则吉。"""
            elif ben["name"] == "坤":
                return f"""**【六爻全动 · 坤 · 用六】**
体用关系：查京房八宫卦，本卦「{ben['name']}」属{ben_gong}（{ti}），体；之卦「{zhi['name']}」属{zhi_gong or '未知'}（{yong}），用。
体卦五行：{ti}，用卦五行：{yong}，体用生克：{shengke_text(ti, yong)}。
操作：遵循"用六"——"利永贞"。本卦六爻全动，阴柔之道行到底，体用关系转化为终始循环。
解读：阴极转阳，事物进入全新阶段，宜守持正道，柔中带刚，永久守持则利。"""
            else:
                return f"""**【六爻全动】体用分析**
体用关系：查京房八宫卦，本卦「{ben['name']}」属{ben_gong}（{ti}），体；之卦「{zhi['name']}」属{zhi_gong or '未知'}（{yong}），用。
体卦五行：{ti}，用卦五行：{yong}，体用生克：{shengke_text(ti, yong)}。
月令：{lunar}（{yue_wuxing}，{yue_state}）
操作：直接看之卦《{zhi['name']}》的卦辞，本卦《{ben['name']}》的旧格局已完全瓦解。"""

    else:
        return f"**【{changed_count}个动爻】** 按一般原则解读。"


def _build_sancai_rule(changed_positions: list, changed_count: int, yaos: list) -> tuple[str, dict]:
    """
    根据动爻位置，构建第四步三才定位规则文本。
    返回 (规则文本, {涉及的三才: [位置列表]})
    初爻/二爻/三爻 = 地（底层/根基）
    四爻/五爻 = 人（中间层/阶段）
    上爻 = 天（顶层/终极）
    """
    involved = {"地": [], "人": [], "天": []}
    rules = []

    if changed_count == 0:
        return (
            """**【静卦 · 无动爻】三才定位**
事情处于静止状态，无明显着力点。三才皆平，宜静观其变，坚守本位，不宜轻举妄动。""",
            {"地": [], "人": [], "天": []}
        )

    for pos in changed_positions:
        if pos == 0:
            rules.append("**初爻动（地位）**：建议调整底层逻辑、起步策略或根基条件，从源头发力。")
            involved["地"].append("初爻")
        elif pos == 1:
            rules.append("**二爻动（地位）**：建议提升内在德行、辅佐他人或稳固内部基础。")
            involved["地"].append("二爻")
        elif pos == 2:
            rules.append("**三爻动（人位）**：警示行事需谨慎，进退艰难时切勿急躁，防中道之变。")
            involved["人"].append("三爻")
        elif pos == 3:
            rules.append("**四爻动（人位）**：已进入高层或新阶段，需审时度势，随机应变。")
            involved["人"].append("四爻")
        elif pos == 4:
            rules.append("**五爻动（天位）**：事情已到显赫位置，重在保持德行与中正，不可过亢。")
            involved["天"].append("五爻")
        elif pos == 5:
            rules.append("**上爻动（天位）**：物极必反，建议功成身退或考虑事物尽头的转变，戒极端。")
            involved["天"].append("上爻")

    # 构建涉及情况说明
    involved_desc = []
    not_involved = []
    if involved["地"]:
        involved_desc.append(f"地（{','.join(involved['地'])}动）")
    else:
        not_involved.append("地")
    if involved["人"]:
        involved_desc.append(f"人（{','.join(involved['人'])}动）")
    else:
        not_involved.append("人")
    if involved["天"]:
        involved_desc.append(f"天（{','.join(involved['天'])}动）")
    else:
        not_involved.append("天")

    base_text = "\n".join(rules)
    if changed_count == 1:
        base_text += f"\n\n本次唯一动爻位于「{['初爻','二爻','三爻','四爻','五爻','上爻'][changed_positions[0]]}」，请依上对应建议行事。"
    else:
        base_text += f"\n\n本次{changed_count}个动爻同时发力，建议分清主次，以最高位置（或最重要位置）的动爻为主要着力点，其他为辅。"

    note = f"\n\n⚠️ 本次动爻只涉及：{', '.join(involved_desc)}。三才中【{'/'.join(not_involved)}】无动爻，不在分析范围内，请勿添加这些未涉及的层级。"
    return base_text + note, involved


def _build_priority_rule(changed_count: int, ben_gua_name: str, zhi_gua_name: str, changed: list = None) -> str:
    """根据动爻数量，构建第二步的解读优先级规则文本"""
    if changed_count == 0:
        return f"""**【静卦 · 0个动爻】**
逻辑：事情处于静止、潜伏或僵持状态，没有内在推动力，短期内不会有大的变化。
操作：重点看本卦《{ben_gua_name}》的卦辞。结合卦象的"德性"判断当下处境，建议"以静制动"或坚守本位。"""
    elif changed_count == 1:
        return f"""**【一爻动 · 最常见】**
逻辑：矛盾集中体现在这一个爻位上，这是整件事情的关键节点。
操作：主要看本卦中动爻的爻辞。参考之卦《{zhi_gua_name}》对应爻的爻辞，作为"未来变化"的参考。"""
    elif changed_count == 2:
        # 以下爻为体、上爻为用，以下爻爻辞为主、上爻爻辞为辅
        lower_yao = min(changed or [0])
        upper_yao = max(changed_positions)
        pos_name = {0:"初爻",1:"二爻",2:"三爻",3:"四爻",4:"五爻",5:"上爻"}
        return f"""**【二爻动】**
逻辑：事情有两个内在驱动力在拉扯，或问题涉及两个层面的交织。
操作：以「{pos_name[lower_yao]}」动爻的爻辞为主，「{pos_name[upper_yao]}」动爻的爻辞为辅。{pos_name[upper_yao]}代表外部/未来/显性结果；{pos_name[lower_yao]}代表内部/根基/隐性原因。"""
    elif changed_count == 3:
        return f"""**【三爻动】**
逻辑：事情处于剧烈变动期，内卦或外卦整体结构发生根本动摇，单看某一爻已不足以概括全局。
操作：重点看本卦《{ben_gua_name}》和之卦《{zhi_gua_name}》的卦辞。本卦卦辞代表"现状"，之卦卦辞代表"归宿"。"""
    elif changed_count == 4:
        return f"""**【四爻动】**
逻辑：大多数爻都在变动，剩下的两个静爻反而是关键。在动荡的大环境中，守住"不变"的东西才是核心。
操作：看之卦《{zhi_gua_name}》中那两个不变（静）的爻，它们代表变局中唯一可以抓得住的"定数"，以下位（初爻）静爻为根基。"""
    elif changed_count == 5:
        return f"""**【五爻动】**
逻辑：物以稀为贵，唯一静止的地方是破局的关键。
操作：看之卦《{zhi_gua_name}》中唯一不变的静爻的爻辞。"""
    elif changed_count == 6:
        if ben_gua_name == "乾":
            return f"""**【六爻全动 · 极变之卦 · 乾】**
操作：遵循"用九"爻辞——"见群龙无首，吉"。代表由阳转阴的终极循环，本卦旧格局已完全瓦解。"""
        elif ben_gua_name == "坤":
            return f"""**【六爻全动 · 极变之卦 · 坤】**
操作：遵循"用六"爻辞——"利永贞"。代表由阴转阳的终极循环，本卦旧格局已完全瓦解。"""
        else:
            return f"""**【六爻全动 · 极变之卦】**
操作：直接看之卦《{zhi_gua_name}》的卦辞，因为本卦《{ben_gua_name}》的旧格局已完全瓦解，未来由全新的卦象主导。"""
    else:
        return f"**【{changed_count}个动爻】** 按一般原则解读。"


def build_interpretation_prompt(divination_result: dict, user_question: str = "", lang: str = "zh") -> str:
    """构建 AI 解读提示词（支持中/英）"""
    ben = divination_result["ben_gua"]
    zhi = divination_result["zhi_gua"]
    yaos = divination_result["yaos"]
    zhi_yaos = divination_result["zhi_yaos"]
    changed = divination_result["changed_indices"]
    changed_count = len(changed)
    hua_gua = divination_result.get("hua_gua")
    div_time = divination_result.get("divination_time", {})

    # ── 变爻信息 ──
    changed_yao_info_en = []
    changed_yao_info_zh = []
    if changed:
        for i in changed:
            if i < len(yaos):
                yao = yaos[i]
                pos = yao.get("position", i + 1) - 1
                zhi_yao_name = zhi_yaos[pos]["yao_name"] if 0 <= pos < len(zhi_yaos) else "(data unavailable)"
                changed_yao_info_en.append(f"- {yao['yao_name']}: {yao['sentence']} → changes to {zhi_yao_name}")
                changed_yao_info_zh.append(f"- {yao['yao_name']}：{yao['sentence']} → 变后为 {zhi_yao_name}")
    else:
        changed_yao_info_en.append("(None — this is a静卦, a still hexagram with no changing lines)")
        changed_yao_info_zh.append("无（本卦无变爻，为静卦）")

    # ── 互卦信息 ──
    hua_gua_en = ""
    hua_gua_zh = ""
    if changed_count == 3 and hua_gua:
        hua_gua_en = f"""\nInterchangeable hexagram (Hùa Guà — for observing the transitional process): {hua_gua['name']}
  - Structure: {hua_gua['lower_symbol']} (lower) / {hua_gua['upper_symbol']} (upper)
  - Hexagram meaning: {hua_gua.get('sentence', '(none)')}"""
        hua_gua_zh = f"""\n互卦（中爻，用于观察演变过程）：《{hua_gua['name']}》
  - 卦象：{hua_gua['lower_symbol']}下 + {hua_gua['upper_symbol']}上
  - 卦辞：{hua_gua.get('sentence', '（无）')}"""

    # ── 第二步到第四步（与语言无关，使用数字和符号保持一致性）──
    # 体用规则构建（中文，用于注入）
    tiyong_zh = _build_tiyong_rule(changed, ben, zhi, div_time, zhi_yaos, hua_gua)
    sancai_zh, _ = _build_sancai_rule(changed if isinstance(changed, list) else [], changed_count, yaos)
    priority_zh = _build_priority_rule(changed_count, ben["name"], zhi["name"], changed)

    def extract_tiyong_text(tiyong_rule: str) -> str:
        if "体用生克：" in tiyong_rule:
            seg = tiyong_rule.split("体用生克：")[1].split("\n")[0].strip()
        elif "判断：" in tiyong_rule:
            seg = tiyong_rule.split("判断：")[1].split("\n")[0].strip()
        else:
            seg = "(see body/weight analysis above)"
        if changed_count in (3, 4, 5, 6) and "体卦五行" in tiyong_rule:
            lines = tiyong_rule.split("\n")
            ti_l = next((l for l in lines if "体卦五行" in l), "")
            yong_l = next((l for l in lines if "用卦五行" in l), "")
            seg = f"（{ti_l.strip()}，{yong_l.strip()}）→ {seg}"
        return seg

    tiyong_text = extract_tiyong_text(tiyong_zh)

    # ── 五行约束（用于3爻动及以上）──
    if changed_count in (3, 4, 5, 6):
        ben_gong, ben_gong_wx = _find_gua_gong_and_wuxing(ben["name"])
        zhi_gong, zhi_gong_wx = _find_gua_gong_and_wuxing(zhi["name"])
        tiyong_constraint_zh = f"⚠️ 重要：本卦《{ben['name']}》属{ben_gong}，体卦五行={ben_gong_wx}；之卦《{zhi['name']}》属{zhi_gong or '未知'}，用卦五行={zhi_gong_wx or '未知'}。请在【定量】判断中严格使用上述数据，不得自行重新推算。"
        tiyong_constraint_en = f"IMPORTANT: Original hexagram {ben['name']} belongs to the {ben_gong} palace (body element: {ben_gong_wx}); Changed hexagram {zhi['name']} belongs to {zhi_gong or 'unknown'} palace (use element: {zhi_gong_wx or 'unknown'}). You MUST use these exact element assignments in your【Quantitative】analysis — do NOT recalculate them from hexagram names."
    else:
        tiyong_constraint_zh = ""
        tiyong_constraint_en = ""

    # ── 五行名称映射（用于英文）──
    WX_NAMES_EN = {"金": "Metal", "木": "Wood", "水": "Water", "火": "Fire", "土": "Earth"}

    # ── 构建中文版 prompt ──
    prompt_zh = f"""你是一位精通《周易》的占卜师，请严格遵循以下五步解卦，为用户提供深入准确的解读。

{'用户的问题：' + user_question if user_question else '（用户未提供具体问题，请从卦象本身出发进行解读）'}

═══════════════════════════════════════
【第一步 · 确认三要素】
═══════════════════════════════════════

本卦：《{ben['name']}》
  - 卦象：{ben['lower_symbol']}下 + {ben['upper_symbol']}上
  - 卦辞：{ben['sentence']}

之卦（变卦）：《{zhi['name']}》
  - 卦象：{zhi['lower_symbol']}下 + {zhi['upper_symbol']}上
  - 卦辞：{zhi['sentence']}

动爻：{''.join(changed_yao_info_zh)}
{hua_gua_zh}

═══════════════════════════════════════
【第二步 · 确定解读优先级】
核心铁律："爻为君，卦为臣"——变爻的爻辞优先级高于卦辞。
═══════════════════════════════════════

{priority_zh}

═══════════════════════════════════════
【第三步 · 体用生克（辅助定量分析）】
核心原则：爻辞/卦辞是"定性"主干，体用生克是"定量"辅助。两者结合，方得完整判断。
═══════════════════════════════════════

{tiyong_zh}

═══════════════════════════════════════
【第四步 · 三才定位】
将动爻的位置与现实处境结合，找到你可以发力的方向。
═══════════════════════════════════════

{sancai_zh}

═══════════════════════════════════════
【第五步 · 综合判断（必须全部包含四项）】
═══════════════════════════════════════

请按以下四个维度输出综合结论：

**① 定性**
根据爻辞的吉凶关键字（元吉、贞吉、无咎、悔亡、吝、凶等），为本次占卜定调。

**② 定位**
根据动爻位置（三才：初爻=地、二三爻=人、四五爻=人、上爻=天），指出问题出在哪个阶段。

**③ 定量**
{tiyong_constraint_zh}
直接使用第三步给出的体用生克关系（{tiyong_text}），判断你与外部环境的能量对比。
绝对禁止：自行根据卦名重新推算体卦/用卦五行，或自行判断生克关系——必须严格采用第三步中已明确给出的结果。

**④ 定向**
根据之卦《{zhi['name']}》的整体象意，指出未来的大方向和行动出口。

═══════════════════════════════════════
【易经核心精神】
解卦的目的不是预知宿命，而是帮助你找到可以努力的"着力点"。遵循"无咎"之道——调整德行、能力和心态，避开凶的趋势，走向吉的结果。
═══════════════════════════════════════

请使用古典与当代结合的语言风格，既保持《周易》的智慧底蕴，又让现代人容易理解。回答要有深度，但不要过于晦涩。"""

    # ── 构建英文版 prompt ──
    changed_names_en = ", ".join(yaos[i]["yao_name"] for i in changed) if changed else "none"
    position_meaning_en = {
        0: "Ground/Foot (the foundation — where you stand)",
        1: "Ground/Foot (inner strength, inner resources)",
        2: "Person/Middle (cautious action, middle road)",
        3: "Person/Middle (position of transition, adapt to circumstances)",
        4: "Heaven/High (high position, guard against arrogance)",
        5: "Heaven/Top (extreme, retreat or transform)",
    }
    changed_positions_en = [position_meaning_en.get(i, f"position {i+1}") for i in (changed if isinstance(changed, list) else [])]

    def get_priority_en(count):
        if count == 0:
            return "This is a静卦 (Still Hexagram) — no lines are changing. The situation is at rest. Focus entirely on the hexagram judgment (卦辞) and its 'virtue' — the energy it represents. No internal driving force. Advise the user to stay steady and wait."
        elif count == 1:
            return f"One line is changing (line(s): {changed_names_en}). This is the KEY node of the entire situation. Focus primarily on the changing line's爻辞 (line text). Use the changed hexagram's corresponding line text as a glimpse of the future direction."
        elif count == 2:
            pos = changed[:]
            lower = min(pos); upper = max(pos)
            return f"Two lines are changing (lines {', '.join(changed_names_en.split(', '))}). Focus mainly on the爻辞 of line {lower+1} (the lower position), and use line {upper+1} (the higher position) as secondary context — the higher line represents the external/visible outcome, the lower represents internal/root cause."
        elif count == 3:
            return f"Three lines are changing — a MAJOR transformation affecting both inner and outer structures. The entire hexagram is in flux. Look at BOTH hexagram judgments (卦辞 of original and changed) for the full picture. Original = current reality; Changed = future destination."
        elif count == 4:
            return f"Four lines are changing — most of the hexagram is transforming. The TWO STILL lines are the only constants you can rely on. Focus on those still lines, especially the one in the lower position (near the root). These represent what remains steady in a changing situation."
        elif count == 5:
            return f"Five lines are changing — only one line remains still. That single still line is the key to the entire situation. Everything else is in motion; hold fast to what is unmoving."
        elif count == 6:
            return f"All six lines are changing — total transformation. The entire structure collapses and rebuilds. For 乾 (all yang), follow '用九' — '群龙无首，吉' (no single leader, harmony). For 坤 (all yin), follow '用六' — '利永贞' (lasting perseverance). Otherwise, interpret through the changed hexagram's meaning."
        return f"{count} lines changing."

    def get_tiyong_en(count, ben, zhi, hua_gua, div_time):
        SYM_TO_WX = {"☰": "金", "☱": "金", "☲": "火", "☳": "木", "☴": "木", "☵": "水", "☷": "土", "☶": "土"}
        GUA_WUXING = {s: SYM_TO_WX.get(s, "土") for s in ["☰", "☱", "☳", "☴", "☵", "☲", "☷", "☶"]}

        if count == 0:
            ti_el = GUA_WUXING.get(ben["upper_symbol"], "土")
            return f"Body-Use: Static balance (静卦). The entire hexagram is the Body, with no separate Use. Element: {WX_NAMES_EN.get(ti_el, ti_el)}."

        ti_elements = []
        yong_elements = []
        ti_gua_str = ""; yong_gua_str = ""
        ti_pos_str = ""; yong_pos_str = ""

        if count == 1:
            pos = changed[0] if changed else 0
            ti_is_upper = pos >= 3
            ti_gua = "upper" if ti_is_upper else "lower"
            yong_gua = "lower" if ti_is_upper else "upper"
            ti_el = GUA_WUXING.get(ben["upper_symbol"] if ti_is_upper else ben["lower_symbol"], "土")
            yong_el = GUA_WUXING.get(ben["lower_symbol"] if ti_is_upper else ben["upper_symbol"], "火")
            ti_elements = [ti_el]; yong_elements = [yong_el]
            ti_gua_str = ti_gua; yong_gua_str = yong_gua
            ti_pos_str = f"{'upper' if ti_is_upper else 'lower'} trigram ({ben['upper_symbol'] if ti_is_upper else ben['lower_symbol']})"; yong_pos_str = f"{'lower' if ti_is_upper else 'upper'} trigram ({ben['lower_symbol'] if ti_is_upper else ben['upper_symbol']})"
        elif count == 2:
            all_pos = set(range(6))
            static = all_pos - set(changed)
            lower_changed = sum(1 for p in changed if p < 3)
            upper_changed = len(changed) - lower_changed
            if lower_changed == 0:
                ti_gua_str, yong_gua_str = "lower", "upper"
                ti_el = GUA_WUXING.get(ben["lower_symbol"], "土"); yong_el = GUA_WUXING.get(ben["upper_symbol"], "火")
                ti_pos_str = f"lower trigram ({ben['lower_symbol']})"; yong_pos_str = f"upper trigram ({ben['upper_symbol']})"
            elif upper_changed == 0:
                ti_gua_str, yong_gua_str = "upper", "lower"
                ti_el = GUA_WUXING.get(ben["upper_symbol"], "土"); yong_el = GUA_WUXING.get(ben["lower_symbol"], "火")
                ti_pos_str = f"upper trigram ({ben['upper_symbol']})"; yong_pos_str = f"lower trigram ({ben['lower_symbol']})"
            else:
                ti_gua_str, yong_gua_str = "lower", "upper"
                ti_el = GUA_WUXING.get(ben["lower_symbol"], "土"); yong_el = GUA_WUXING.get(ben["upper_symbol"], "火")
                ti_pos_str = f"lower trigram ({ben['lower_symbol']})"; yong_pos_str = f"upper trigram ({ben['upper_symbol']})"
            ti_elements = [ti_el]; yong_elements = [yong_el]
        elif count in (3, 4, 5, 6):
            ben_gong, bwx = _find_gua_gong_and_wuxing(ben["name"])
            zhi_gong, zwx = _find_gua_gong_and_wuxing(zhi["name"])
            ti_el = bwx or "土"; yong_el = zwx or "火"
            ti_elements = [WX_NAMES_EN.get(ti_el, ti_el)]; yong_elements = [WX_NAMES_EN.get(yong_el, yong_el)]
            ti_pos_str = f"{ben_gong} palace main element ({WX_NAMES_EN.get(ti_el, ti_el)})"; yong_pos_str = f"{zhi_gong or 'unknown'} palace element ({WX_NAMES_EN.get(yong_el, yong_el)})"

        def shengke_en(ti, yong):
            pairs = [("Wood","Fire"),("Fire","Earth"),("Earth","Metal"),("Metal","Water"),("Water","Wood")]
            if ti == yong:
                return "Body and Use are in harmony (比和) — stable and balanced."
            if (ti, yong) in pairs:
                return f"Use nourishes Body ({yong} → {ti}) — FAVORABLE. External energy supports you."
            rev = [("Wood","Earth"),("Earth","Water"),("Water","Fire"),("Fire","Metal"),("Metal","Wood")]
            if (ti, yong) in rev:
                return f"Body controls Use ({ti} → {yong}) — productive but requires effort."
            if (yong, ti) in pairs:
                return f"Body generates Use ({ti} → {yong}) — draining, energy leaks away."
            if (yong, ti) in rev:
                return f"Use controls Body ({yong} → {ti}) — DANGEROUS. External force overwhelms you."
            return f"Body {ti}, Use {yong}"

        sk = shengke_en(ti_elements[0], yong_elements[0])
        ti_pos_str = ti_pos_str.replace("土","Earth").replace("火","Fire").replace("水","Water").replace("金","Metal").replace("木","Wood")
        yong_pos_str = yong_pos_str.replace("土","Earth").replace("火","Fire").replace("水","Water").replace("金","Metal").replace("木","Wood")

        if count in (0, 1, 2):
            return f"Body-Use analysis ({count} changing line{'s' if count != 1 else ''}): Body element = {ti_elements[0]} (in the {ti_pos_str}), Use element = {yong_elements[0]} (in the {yong_pos_str}). Relationship: {sk}"
        else:
            return f"Jingfang Gong analysis ({count} changing lines): Body element = {ti_elements[0]} (from {ben['name']}'s {ti_pos_str}), Use element = {yong_elements[0]} (from {zhi['name']}'s {yong_pos_str}). Relationship: {sk}"

    def get_sancai_en(changed_list, count, yaos):
        if count == 0:
            return "Three Powers (三才) — Still Hexagram: All three levels (Ground/Person/Heaven) are at rest. No active force anywhere. Advise calm observation, maintain current position, do not act."
        involved = []
        not_inv = ["Ground (lower)", "Person (middle)", "Heaven (upper)"]
        rules = []
        for i, pos in enumerate(changed_list):
            desc = [
                "Ground/Fundament — Adjust your foundation, root strategy, or underlying conditions. Act from the source.",
                "Ground/Fundament — Build inner strength, support others, or stabilize the inner foundation.",
                "Person/Middle — Proceed with caution. This is a difficult in-between position — do not rush.",
                "Person/Middle — You have entered a higher level. Assess the situation and adapt flexibly.",
                "Heaven/High — You have reached a prominent position. Maintain virtue and balance — do not become arrogant.",
                "Heaven/Top — Extreme position. Consider retreat or transformation. Avoid extremism.",
            ]
            rules.append(f"  Line {pos+1} ({yaos[pos]['yao_name']}): {desc[pos]}")
            involved.append(desc[pos].split("—")[0].strip())
            if "Ground" in involved[-1]: not_inv = [n for n in not_inv if "Ground" not in n]
            if "Person" in involved[-1]: not_inv = [n for n in not_inv if "Person" not in n]
            if "Heaven" in involved[-1]: not_inv = [n for n in not_inv if "Heaven" not in n]
        note = f"\n\n⚠️ Only the following Three Powers levels have changing lines: {', '.join(involved)}. Levels {', '.join(not_inv)} have NO changing lines — do NOT analyze or mention these levels."
        if count == 1:
            note += f"\n\nThe sole changing line is at {changed_list[0]+1}: {position_meaning_en.get(changed_list[0], '')}."
        return "Three Powers (三才) positioning — match changing line positions to real-world areas:\n" + "\n".join(rules) + note

    lunar = div_time.get("lunar_month", "")
    yue_wx = div_time.get("yueling_wuxing", "")
    yue_state = div_time.get("yueling_state", "")

    priority_en = get_priority_en(changed_count)
    tiyong_en = get_tiyong_en(changed_count, ben, zhi, hua_gua, div_time)
    sancai_en = get_sancai_en(changed if isinstance(changed, list) else [], changed_count, yaos)

    if yue_state:
        state_map = {"旺": "at its peak (strongest)", "帝旺": "at imperial peak", "相": "in a growing phase",
                     "休": "resting/recovering", "囚": "imprisoned/constrained", "死": "exhausted/declining"}
        yue_desc = state_map.get(yue_state, yue_state)
    else:
        yue_desc = "moderate"

    prompt_en = f"""You are a wise I Ching master. Give a clear, practical reading in simple modern English.

## THE HEXAGRAM
- Current: **{ben['name']}** → Future: **{zhi['name']}**
- Changing line(s): {changed_names_en if changed_names_en else 'none'}

{tiyong_en}

## COMPREHENSIVE ANALYSIS

**① Overall Energy & Mood**
(tone: favorable or unfavorable? auspicious or risky?)

**② Situation Positioning**
(where is this happening — foundation, relationships, or bigger context?)

**③ Energy Balance**
(your energy vs external conditions — supportive or challenging?)

**④ Development Direction**
(where is this heading? what should you prepare for?)

## FINAL GUIDANCE
(give 1-2 short paragraphs of practical advice — what to do next, what to avoid, mindset to adopt)

Keep it short, warm, and actionable. Like advice from a wise friend. No ancient theory needed."""

    if lang == "en":
        return prompt_en
    else:
        return prompt_zh



class InterpretationRequest(BaseModel):
    divination_result: dict
    user_question: str = ""
    lang: str = "zh"


class InterpretationResponse(BaseModel):
    interpretation: str
    model: str


@router.post("/interpret", response_model=InterpretationResponse)
async def interpret_divination(req: InterpretationRequest):
    """使用 DeepSeek 对占卜结果进行 AI 解读（async版本，避免阻塞事件循环）"""
    import requests
    import json as json_lib

    if not DEEPSEEK_API_KEY:
        raise HTTPException(status_code=500, detail="DeepSeek API Key 未配置")

    # DEBUG: 打印收到的 ben_gua 类型
    ben_gua_val = req.divination_result.get("ben_gua")
    print(f"[DEBUG] ben_gua type: {type(ben_gua_val)}, value: {str(ben_gua_val)[:100]}")

    # 防御性修复：如果 ben_gua 是字符串（旧的卦名格式），转换为完整的 dict 对象
    divination_result = req.divination_result
    if isinstance(divination_result.get("ben_gua"), str):
        # 把字符串卦名转换为完整的卦对象（从 data_loader 获取完整数据）
        from ..data_loader import get_gua_info
        ben_name = divination_result["ben_gua"]
        zhi_name = divination_result.get("zhi_gua", ben_name)
        ben_info = get_gua_info(ben_name) or {}
        zhi_info = get_gua_info(zhi_name) if zhi_name != ben_name else ben_info
        divination_result = {
            **divination_result,
            "ben_gua": {
                "name": ben_info.get("guaName", ben_name),
                "code": ben_info.get("code", ""),
                "lower_code": ben_info.get("lowerCode", ""),
                "upper_code": ben_info.get("upperCode", ""),
                "lower_symbol": _code_to_symbol(ben_info.get("lowerCode", "")),
                "upper_symbol": _code_to_symbol(ben_info.get("upperCode", "")),
                "sentence": "",
                "wuxing": "",
            },
            "zhi_gua": {
                "name": zhi_info.get("guaName", zhi_name),
                "code": zhi_info.get("code", ""),
                "lower_code": zhi_info.get("lowerCode", ""),
                "upper_code": zhi_info.get("upperCode", ""),
                "lower_symbol": _code_to_symbol(zhi_info.get("lowerCode", "")),
                "upper_symbol": _code_to_symbol(zhi_info.get("upperCode", "")),
                "sentence": "",
                "wuxing": "",
            } if zhi_name != ben_name else {
                "name": ben_info.get("guaName", ben_name),
                "code": ben_info.get("code", ""),
                "lower_code": ben_info.get("lowerCode", ""),
                "upper_code": ben_info.get("upperCode", ""),
                "lower_symbol": _code_to_symbol(ben_info.get("lowerCode", "")),
                "upper_symbol": _code_to_symbol(ben_info.get("upperCode", "")),
                "sentence": "",
                "wuxing": "",
            },
        }
        print(f"[DEBUG] Converted string ben_gua to dict: {ben_name}")

    prompt = build_interpretation_prompt(divination_result, req.user_question, req.lang)

    system_msg = (
        "You are a master of the I Ching (Zhou Yi /周易), with decades of experience in Yi Jing studies. You speak with wisdom and warmth, blending classical insight with modern understanding. Always respond in English."
        if req.lang == "en"
        else "你是一位精通《周易》的占卜师，拥有数十年易学研究经验，说话富有智慧且温暖。"
    )

    def _call_api():
        resp = requests.post(
            "https://api.deepseek.com/chat/completions",
            json={
                "model": "deepseek-chat",
                "messages": [
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 2048,
                "temperature": 0.7,
            },
            headers={"Authorization": f"Bearer {DEEPSEEK_API_KEY}"},
            timeout=180,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]

    try:
        interpretation = await asyncio.to_thread(_call_api)
        return InterpretationResponse(interpretation=interpretation, model="deepseek-chat")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI 解读失败：{str(e)}")


@router.get("/health")
async def ai_health():
    """检查 AI 服务状态"""
    if not DEEPSEEK_API_KEY:
        return {"status": "unconfigured", "message": "DEEPSEEK_API_KEY 未设置"}
    return {"status": "ready", "model": "deepseek-chat"}
