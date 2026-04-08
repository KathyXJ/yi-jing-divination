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
    """构建 AI 解读提示词"""
    ben = divination_result["ben_gua"]
    zhi = divination_result["zhi_gua"]
    yaos = divination_result["yaos"]
    zhi_yaos = divination_result["zhi_yaos"]
    changed = divination_result["changed_indices"]
    changed_count = len(changed)
    hua_gua = divination_result.get("hua_gua")
    div_time = divination_result.get("divination_time", {})

    # 变爻详细信息
    changed_yao_info = ""
    if changed:
        changed_yaos = [yaos[i] for i in changed if i < len(yaos)]
        changed_yao_info = "本次占卜变爻：\n"
        for yao in changed_yaos:
            pos = (yao.get("position") or 1) - 1
            if 0 <= pos < len(zhi_yaos):
                zhi_yao_name = zhi_yaos[pos]["yao_name"]
            else:
                zhi_yao_name = "（信息不全）"
            changed_yao_info += f"- {yao['yao_name']}：{yao['sentence']} → 变后为 {zhi_yao_name}\n"
    else:
        changed_yao_info = "无（本卦无变爻，为静卦）"

    # 互卦信息（3爻动时展示）
    hua_gua_info = ""
    if changed_count == 3 and hua_gua:
        hua_gua_info = f"""
互卦（中爻，用于观察演变过程）：《{hua_gua['name']}》
  - 卦象：{hua_gua['lower_symbol']}下 + {hua_gua['upper_symbol']}上
  - 卦辞：{hua_gua.get('sentence', '（无）')}"""

    # 第二步：解读优先级
    priority_rule = _build_priority_rule(changed_count, ben["name"], zhi["name"], changed)

    # 第三步：体用生克
    tiyong_rule = _build_tiyong_rule(changed, ben, zhi, div_time, zhi_yaos, hua_gua)

    # 体用关系文字提取（用于综合判断）
    # 对于3爻动及以上：京房八宫卦的五行已直接在tiyong_rule中明确，
    # 提取时把整行带上，确保第五步不混淆
    try:
        if '体用生克：' in tiyong_rule:
            line = tiyong_rule.split('体用生克：')[1].split('\n')[0].strip()
            # 3爻动及以上时，用更明确的格式强制AI使用正确的五行
            if changed_count in (3, 4, 5, 6):
                # 从tiyong_rule中直接找到体卦五行和用卦五行
                lines = tiyong_rule.split('\n')
                ti_line = next((l for l in lines if '体卦五行' in l), '')
                yong_line = next((l for l in lines if '用卦五行' in l), '')
                tiyong_text = f"（{ti_line.strip()}，{yong_line.strip()}）→ {line}"
            else:
                tiyong_text = line
        elif '判断：' in tiyong_rule:
            tiyong_text = tiyong_rule.split('判断：')[1].split('\n')[0].strip()
        else:
            tiyong_text = '（见体用生克分析）'
    except:
        tiyong_text = '（见体用生克分析）'

    # 3爻动及以上时，加强约束：强制使用京房八宫卦查出的五行
    if changed_count in (3, 4, 5, 6):
        ben_gong, ben_gong_wx = _find_gua_gong_and_wuxing(ben["name"])
        zhi_gong, zhi_gong_wx = _find_gua_gong_and_wuxing(zhi["name"])
        tiyong_constraint = f"⚠️ 重要：本卦《{ben['name']}》属{ben_gong}，体卦五行={ben_gong_wx}；之卦《{zhi['name']}》属{zhi_gong or '未知'}，用卦五行={zhi_gong_wx or '未知'}。请在【定量】判断中严格使用上述数据，不得自行重新推算。"
    else:
        tiyong_constraint = ""

    # 第四步：三才定位（根据动爻位置）
    changed_positions = changed if isinstance(changed, list) else []
    sān_cái_rules, _ = _build_sancai_rule(changed_positions, changed_count, yaos)

    prompt = f"""你是一位精通《周易》的占卜师，请严格遵循以下五步解卦，为用户提供深入准确的解读。

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

动爻：{changed_yao_info}
{hua_gua_info}

═══════════════════════════════════════
【第二步 · 确定解读优先级】
核心铁律："爻为君，卦为臣"——变爻的爻辞优先级高于卦辞。
═══════════════════════════════════════

{priority_rule}

═══════════════════════════════════════
【第三步 · 体用生克（辅助定量分析）】
核心原则：爻辞/卦辞是"定性"主干，体用生克是"定量"辅助。两者结合，方得完整判断。
═══════════════════════════════════════

{tiyong_rule}

═══════════════════════════════════════
【第四步 · 三才定位】
将动爻的位置与现实处境结合，找到你可以发力的方向。
═══════════════════════════════════════

{sān_cái_rules}

═══════════════════════════════════════
【第五步 · 综合判断（必须全部包含四项）】
═══════════════════════════════════════

请按以下四个维度输出综合结论：

**① 定性**
根据爻辞的吉凶关键字（元吉、贞吉、无咎、悔亡、吝、凶等），为本次占卜定调。

**② 定位**
根据动爻位置（三才：初爻=地、二三爻=人、四五爻=人、上爻=天），指出问题出在哪个阶段。

**③ 定量**
{tiyong_constraint}
直接使用第三步给出的体用生克关系（{tiyong_text}），判断你与外部环境的能量对比。
绝对禁止：自行根据卦名重新推算体卦/用卦五行，或自行判断生克关系——必须严格采用第三步中已明确给出的结果。

**④ 定向**
根据之卦《{zhi['name']}》的整体象意，指出未来的大方向和行动出口。

═══════════════════════════════════════
【易经核心精神】
解卦的目的不是预知宿命，而是帮助你找到可以努力的"着力点"。遵循"无咎"之道——调整德行、能力和心态，避开凶的趋势，走向吉的结果。
═══════════════════════════════════════

请使用古典与当代结合的语言风格，既保持《周易》的智慧底蕴，又让现代人容易理解。回答要有深度，但不要过于晦涩。"""
    return prompt


class InterpretationRequest(BaseModel):
    divination_result: dict
    user_question: str = ""
    lang: str = "zh"  # 语言选项：zh=中文，en=英文


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

    def _call_api():
        if req.lang == "en":
            system_content = "You are a fortune-telling master with decades of experience in I Ching studies, speaking with wisdom and warmth."
        else:
            system_content = "你是一位精通《周易》的占卜师，拥有数十年易学研究经验，说话富有智慧且温暖。"
        resp = requests.post(
            "https://api.deepseek.com/chat/completions",
            json={
                "model": "deepseek-chat",
                "messages": [
                    {"role": "system", "content": system_content},
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
