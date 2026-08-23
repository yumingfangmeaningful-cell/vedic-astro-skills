#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
塔罗抽牌脚本
用法:
  单牌占 (抽1张):        python3 draw.py one
  三牌阵 (过去/现在/未来): python3 draw.py three
  十字牌阵 (Celtic Cross): python3 draw.py celtic
  自定义张数:             python3 draw.py custom 5
  指定牌(解牌用):         python3 draw.py interpret "The Fool" "reversed:The Tower" "Ten of Cups"
                          (加 reversed: 前缀表示逆位)
"""
import random
import argparse
import json

# ── 78张标准韦特塔罗 ──

MAJOR = [
    ("The Fool", "0", "愚者"),
    ("The Magician", "I", "魔术师"),
    ("The High Priestess", "II", "女祭司"),
    ("The Empress", "III", "女皇"),
    ("The Emperor", "IV", "皇帝"),
    ("The Hierophant", "V", "教皇"),
    ("The Lovers", "VI", "恋人"),
    ("The Chariot", "VII", "战车"),
    ("Strength", "VIII", "力量"),
    ("The Hermit", "IX", "隐士"),
    ("Wheel of Fortune", "X", "命运之轮"),
    ("Justice", "XI", "正义"),
    ("The Hanged Man", "XII", "倒吊人"),
    ("Death", "XIII", "死神"),
    ("Temperance", "XIV", "节制"),
    ("The Devil", "XV", "恶魔"),
    ("The Tower", "XVI", "塔"),
    ("The Star", "XVII", "星星"),
    ("The Moon", "XVIII", "月亮"),
    ("The Sun", "XIX", "太阳"),
    ("Judgement", "XX", "审判"),
    ("The World", "XXI", "世界"),
]

SUITS = {
    "Wands":     ("权杖", "Fire", "火", "行动/激情/创造力/意志"),
    "Cups":      ("圣杯", "Water", "水", "情感/关系/直觉/内心"),
    "Swords":    ("宝剑", "Air", "风", "思维/冲突/决断/沟通"),
    "Pentacles": ("星币", "Earth", "土", "物质/财务/工作/身体"),
}

RANKS = [
    ("Ace", "A", "王牌"),
    ("Two", "2", "二"),
    ("Three", "3", "三"),
    ("Four", "4", "四"),
    ("Five", "5", "五"),
    ("Six", "6", "六"),
    ("Seven", "7", "七"),
    ("Eight", "8", "八"),
    ("Nine", "9", "九"),
    ("Ten", "10", "十"),
    ("Page", "Pg", "侍从"),
    ("Knight", "Kn", "骑士"),
    ("Queen", "Qn", "王后"),
    ("King", "Kg", "国王"),
]

# 元素互动
ELEMENT_RELATIONS = {
    ("Fire", "Fire"): "同元素增强",
    ("Water", "Water"): "同元素增强",
    ("Air", "Air"): "同元素增强",
    ("Earth", "Earth"): "同元素增强",
    ("Fire", "Air"): "友好(火风相助)",
    ("Air", "Fire"): "友好(风火相助)",
    ("Water", "Earth"): "友好(水土相助)",
    ("Earth", "Water"): "友好(土水相助)",
    ("Fire", "Water"): "对立(火水相克)",
    ("Water", "Fire"): "对立(水火相克)",
    ("Air", "Earth"): "对立(风土相克)",
    ("Earth", "Air"): "对立(土风相克)",
    ("Fire", "Earth"): "中性",
    ("Earth", "Fire"): "中性",
    ("Air", "Water"): "中性",
    ("Water", "Air"): "中性",
}


def build_deck():
    deck = []
    for name, num, cn in MAJOR:
        deck.append({
            "name": name, "cn": cn, "number": num,
            "type": "Major", "suit": None, "element": None,
            "rank": None,
        })
    for suit, (suit_cn, elem, elem_cn, domain) in SUITS.items():
        for rank_en, rank_short, rank_cn in RANKS:
            card_name = f"{rank_en} of {suit}"
            deck.append({
                "name": card_name,
                "cn": f"{suit_cn}{rank_cn}",
                "number": rank_short,
                "type": "Minor",
                "suit": suit,
                "suit_cn": suit_cn,
                "element": elem,
                "element_cn": elem_cn,
                "domain": domain,
                "rank": rank_en,
                "rank_cn": rank_cn,
            })
    return deck


DECK = build_deck()
NAME_MAP = {c["name"].lower(): c for c in DECK}
# 中文名反查
CN_MAP = {c["cn"]: c for c in DECK}


def find_card(s):
    s_lower = s.strip().lower()
    if s_lower in NAME_MAP:
        return NAME_MAP[s_lower]
    # 中文名
    if s.strip() in CN_MAP:
        return CN_MAP[s.strip()]
    # 中文别名(tname-20260806: 高塔/女教皇/金币 等民间叫法)
    CN_ALIAS = {"高塔": "塔", "女教皇": "女祭司", "教宗": "教皇", "吊人": "倒吊人",
                "命运轮": "命运之轮", "星辰": "星星", "皇后": "女皇", "圣杯牌": "圣杯",
                "金币": "星币", "钱币": "星币", "五角星": "星币", "手杖": "权杖", "宝杖": "权杖"}
    t = s.strip()
    if t in CN_ALIAS and CN_ALIAS[t] in CN_MAP:
        return CN_MAP[CN_ALIAS[t]]
    for a0, b0 in CN_ALIAS.items():
        if a0 in t and t.replace(a0, b0) in CN_MAP:
            return CN_MAP[t.replace(a0, b0)]
    # 中文模糊(先长后短, 免得"星"抢在"星星"前头)
    if t:
        for k in sorted(CN_MAP, key=len, reverse=True):
            if t in k or k in t:
                return CN_MAP[k]
    # 英文模糊
    for k, v in NAME_MAP.items():
        if s_lower in k or k in s_lower:
            return v
    return None


def draw_cards(n):
    chosen = random.sample(DECK, n)
    result = []
    for c in chosen:
        orientation = random.choice(["正位", "逆位"])
        result.append((c, orientation))
    return result


# ── 牌阵定义 ──

SPREADS = {
    "one": {
        "name": "单牌占",
        "positions": ["当下的核心信息"],
    },
    "three": {
        "name": "三牌阵(时间线)",
        "positions": ["过去(根源/背景)", "现在(当下状态)", "未来(走向/建议)"],
    },
    "celtic": {
        "name": "凯尔特十字(Celtic Cross)",
        "positions": [
            "①现状(核心问题)",
            "②阻碍(挑战/交叉牌)",
            "③远因(深层根源)",
            "④近因(近期影响)",
            "⑤意识(目标/可能结果)",
            "⑥近未来(即将发生)",
            "⑦自我(内心态度/立场)",
            "⑧环境(外部影响/他人)",
            "⑨希望与恐惧",
            "⑩最终结果",
        ],
    },
}


def render_draw(cards_with_pos, spread_name, question=None):
    lines = []
    if question:
        lines.append(f"【问题】{question}")
    lines.append(f"【牌阵】{spread_name}")
    lines.append("")

    elements_in_reading = []

    for (card, orientation), position in cards_with_pos:
        tag = "★大阿卡纳" if card["type"] == "Major" else f"小阿卡纳·{card.get('suit_cn', '')}"
        lines.append(f"── {position} ──")
        lines.append(f"  {card['cn']}({card['name']}) [{orientation}]  {tag}")
        if card["element"]:
            lines.append(f"  元素: {card['element_cn']}({card['element']}) | 领域: {card.get('domain', '')}")
            elements_in_reading.append(card["element"])
        if card["type"] == "Major":
            lines.append(f"  编号: {card['number']} | 大阿卡纳代表重大主题/人生转折")
        lines.append("")

    # 元素分布统计
    if elements_in_reading:
        from collections import Counter
        ec = Counter(elements_in_reading)
        dist = ", ".join(f"{SUITS[s][2]}({SUITS[s][0]})×{c}" for s, (_, e, _, _) in SUITS.items()
                        for elem_name, c in ec.items() if e == elem_name)
        if dist:
            lines.append(f"── 元素分布: {dist} ──")

    # 多张牌时看元素互动
    if len(cards_with_pos) >= 2:
        lines.append("")
        lines.append("── 相邻牌元素互动 ──")
        for i in range(len(cards_with_pos) - 1):
            c1 = cards_with_pos[i][0][0]
            c2 = cards_with_pos[i + 1][0][0]
            e1, e2 = c1.get("element"), c2.get("element")
            if e1 and e2:
                rel = ELEMENT_RELATIONS.get((e1, e2), "—")
                lines.append(f"  {c1['cn']} ({e1}) → {c2['cn']} ({e2}): {rel}")
            elif c1["type"] == "Major" or c2["type"] == "Major":
                lines.append(f"  {c1['cn']} → {c2['cn']}: 含大阿卡纳(超越元素, 看主题共振)")

    # 大阿卡纳数量提示
    major_count = sum(1 for (c, _), _ in cards_with_pos if c["type"] == "Major")
    if major_count >= 3:
        lines.append(f"\n※ 大阿卡纳出现{major_count}张: 强烈的命运/转折信号, 非日常琐事")
    elif major_count == 0 and len(cards_with_pos) >= 3:
        lines.append("\n※ 全为小阿卡纳: 聚焦日常实际层面, 当事人有较大主动权")

    # 花色分布
    suit_counts = {}
    for (c, _), _ in cards_with_pos:
        if c["suit"]:
            suit_counts[c["suit"]] = suit_counts.get(c["suit"], 0) + 1
    dominant = [s for s, cnt in suit_counts.items() if cnt >= 2]
    if dominant:
        for s in dominant:
            lines.append(f"※ {SUITS[s][0]}({SUITS[s][3]})出现{suit_counts[s]}张, 此领域是焦点")

    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["one", "three", "celtic", "custom", "interpret"])
    ap.add_argument("args", nargs="*")
    ap.add_argument("--question", "-q", default=None, help="问题描述")
    a = ap.parse_args()

    if a.mode == "interpret":
        # 解牌模式: 给定牌名, 输出信息供解读
        cards_with_pos = []
        spread = SPREADS.get("custom", {"name": f"自由解牌({len(a.args)}张)", "positions": []})
        positions = [f"第{i+1}张" for i in range(len(a.args))]
        for i, s in enumerate(a.args):
            if s.startswith("reversed:"):
                orient = "逆位"
                s = s[len("reversed:"):]
            else:
                orient = "正位"
            card = find_card(s)
            if card is None:
                print(f"⚠ 未找到牌: {s}")
                continue
            cards_with_pos.append(((card, orient), positions[i]))
        print(render_draw(cards_with_pos, f"指定解牌({len(cards_with_pos)}张)", a.question))
    elif a.mode == "custom":
        n = int(a.args[0]) if a.args else 1
        drawn = draw_cards(n)
        positions = [f"第{i+1}张" for i in range(n)]
        cards_with_pos = list(zip(drawn, positions))
        print(render_draw(cards_with_pos, f"自由抽牌({n}张)", a.question))
    else:
        spread = SPREADS[a.mode]
        n = len(spread["positions"])
        drawn = draw_cards(n)
        cards_with_pos = list(zip(drawn, spread["positions"]))
        print(render_draw(cards_with_pos, spread["name"], a.question))


if __name__ == "__main__":
    main()
