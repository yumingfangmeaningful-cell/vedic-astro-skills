#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
小六壬起卦脚本
用法:
  按公历日期时间起卦(自动转农历):
    python3 qigua.py date "2026-08-03 14:30"
  直接按农历起卦(月 日 时辰支):
    python3 qigua.py lunar 6 21 未
  按数字/骰子起卦(三个数, 连续起法: 第二数从天宫落点续数):
    python3 qigua.py numbers 3 5 2
  按数字独立起法(每个数都从大安起数):
    python3 qigua.py numbers 3 5 2 --independent
  可选: --gender 男/女  (用于转太极土宫取舍及取数参考)
  可选: --hour 未       (numbers 模式下补充时辰, 以便计算体用/墓库/旺衰等)
"""
import sys
import argparse

GONGS = ["大安", "留连", "速喜", "赤口", "小吉", "空亡"]
WUXING = {"大安": "木", "留连": "土", "速喜": "火", "赤口": "金", "小吉": "水", "空亡": "土"}
TU_TYPE = {"留连": "四方阴土", "空亡": "中央阳土"}
JIXIONG = {"大安": "大吉", "速喜": "中吉", "小吉": "小吉", "留连": "小凶", "赤口": "中凶", "空亡": "大凶"}
SISHEN = {"大安": "青龙", "留连": "腾蛇", "速喜": "朱雀", "赤口": "白虎", "小吉": "玄武", "空亡": "勾陈"}
GONGZHI = {"大安": "事业宫(暗藏命宫)", "留连": "田宅宫(暗藏奴仆宫)", "速喜": "感情宫(暗藏夫妻宫)",
           "赤口": "疾厄宫(暗藏兄弟宫)", "小吉": "驿马宫(暗藏子女宫)", "空亡": "福德宫(暗藏父母宫)"}
SHUZI = {"大安": "1、4、5(隐7)", "留连": "2、7、8(隐8)", "速喜": "3、6、9(隐9)",
         "赤口": "4、1、2(隐10)", "小吉": "5、3、8(隐11)", "空亡": "6、5、10(隐12)"}
CANGZHI = {"大安": "寅卯", "留连": "戌未", "速喜": "午巳", "赤口": "申酉", "小吉": "亥子", "空亡": "辰丑"}
BAGUA = {"大安": "震巽", "留连": "坤", "速喜": "离", "赤口": "乾兑", "小吉": "坎", "空亡": "艮"}
FANGWEI = {"大安": "东方", "留连": "四角(东南等偏方)", "速喜": "南方", "赤口": "西方", "小吉": "北方", "空亡": "中央"}
# 体用比助比劫用的宫阴阳(取象p2): 阳宫: 大安速喜赤口空亡; 阴宫: 小吉留连
GONG_YINYANG_TIYONG = {"大安": "阳", "速喜": "阳", "赤口": "阳", "空亡": "阳", "小吉": "阴", "留连": "阴"}
# 地支择法用的宫阴阳(取象p36): 吉宫为阳, 凶宫为阴
GONG_YINYANG_ZEFA = {"大安": "阳", "速喜": "阳", "小吉": "阳", "留连": "阴", "赤口": "阴", "空亡": "阴"}
# 择法各宫阴阳支(地支按标准序位阴阳: 子寅辰午申戌为阳, 丑卯巳未酉亥为阴)
ZEFA_ZHI = {"大安": {"阳": "寅", "阴": "卯"}, "留连": {"阳": "戌", "阴": "未"},
            "速喜": {"阳": "午", "阴": "巳"}, "赤口": {"阳": "申", "阴": "酉"},
            "小吉": {"阳": "子", "阴": "亥"}, "空亡": {"阳": "辰", "阴": "丑"}}

DIZHI = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]
ZHI_WUXING = {"子": "水", "丑": "土", "寅": "木", "卯": "木", "辰": "土", "巳": "火",
              "午": "火", "未": "土", "申": "金", "酉": "金", "戌": "土", "亥": "水"}
ZHI_YINYANG = {z: ("阳" if i % 2 == 0 else "阴") for i, z in enumerate(DIZHI)}
SHENG = {"木": "火", "火": "土", "土": "金", "金": "水", "水": "木"}  # key 生 value
KE = {"木": "土", "土": "水", "水": "火", "火": "金", "金": "木"}    # key 克 value
MU = {"木": "未", "火": "戌", "金": "丑", "水": "辰", "土": "辰"}     # 五行墓库(水土墓辰)
# 十二长生(五行寄生, 水土同宫): 起长生支
CHANGSHENG_START = {"木": "亥", "火": "寅", "金": "巳", "水": "申", "土": "申"}
CS_NAMES = ["长生", "沐浴", "冠带", "临官", "帝旺", "衰", "病", "死", "墓", "绝", "胎", "养"]
HUOSHEN_ORDER = ["青龙", "朱雀", "勾陈", "白虎", "玄武", "腾蛇"]  # 活神顺序(龙首蛇尾)


def wx_relation(a, b):
    """a 对 b 的五行关系描述"""
    if a == b:
        return "比和"
    if SHENG[a] == b:
        return "生"
    if SHENG[b] == a:
        return "被生"
    if KE[a] == b:
        return "克"
    if KE[b] == a:
        return "被克"
    return "?"


def changsheng(wx, zhi):
    start = DIZHI.index(CHANGSHENG_START[wx])
    idx = (DIZHI.index(zhi) - start) % 12
    return CS_NAMES[idx]


def wangshuai(gong_wx, shichen_wx):
    """宫五行相对时辰(令)的旺相休囚死"""
    if gong_wx == shichen_wx:
        return "旺"
    if SHENG[shichen_wx] == gong_wx:
        return "相"  # 令生我
    if SHENG[gong_wx] == shichen_wx:
        return "休"  # 我生令
    if KE[gong_wx] == shichen_wx:
        return "囚"  # 我克令
    return "死"      # 令克我


def hour_to_zhi(hh):
    """24小时制小时 -> 时辰支 (23-1子, 1-3丑, ...)"""
    return DIZHI[((hh + 1) // 2) % 12]


def zhi_ordinal(zhi):
    """子=1 ... 亥=12"""
    return DIZHI.index(zhi) + 1


def cast_from_counts(n1, n2, n3, independent=False):
    """连续起法(默认): 第一数从大安起(大安=1)得天宫; 第二数以天宫为1续数得地宫; 第三数以地宫为1续数得人宫。
       独立起法: 三个数均从大安起数。"""
    i1 = (n1 - 1) % 6
    if independent:
        i2 = (n2 - 1) % 6
        i3 = (n3 - 1) % 6
    else:
        i2 = (i1 + n2 - 1) % 6
        i3 = (i2 + n3 - 1) % 6
    return GONGS[i1], GONGS[i2], GONGS[i3]


def liuqin(luo_wx, other_gong, other_wx):
    """以落宫为我, 判断他宫六亲"""
    if other_wx == luo_wx:
        return "小人(同五行异宫)" if other_gong not in (None,) else "兄弟"
    if SHENG[other_wx] == luo_wx:
        return "父母(生我)"
    if SHENG[luo_wx] == other_wx:
        return "子孙(我生)"
    if KE[other_wx] == luo_wx:
        return "官鬼(克我)"
    if KE[luo_wx] == other_wx:
        return "妻财(我克)"
    return "?"


def zhuan_taiji(gua, shichen_zhi, gender):
    """六亲转太极: 对三宫逐宫变换。土宫取舍: 阳时男测/阴时女测取留连; 阳时女测/阴时男测取空亡。"""
    if not shichen_zhi or not gender:
        return None
    sy = ZHI_YINYANG[shichen_zhi]
    if (sy == "阳" and gender == "男") or (sy == "阴" and gender == "女"):
        tu_gong = "留连"
    else:
        tu_gong = "空亡"
    wx_to_gong = {"木": "大安", "火": "速喜", "金": "赤口", "水": "小吉", "土": tu_gong}
    rev_sheng = {v: k for k, v in SHENG.items()}   # 被谁生
    rev_ke = {v: k for k, v in KE.items()}         # 被谁克
    res = {}
    for name, func in [("父母卦(生我者)", lambda w: rev_sheng[w]),
                       ("子孙卦(我生者)", lambda w: SHENG[w]),
                       ("妻财卦(我克者)", lambda w: KE[w]),
                       ("官鬼卦(克我者)", lambda w: rev_ke[w])]:
        res[name] = [wx_to_gong[func(WUXING[g])] for g in gua]
    return res, tu_gong


def huoshen(shichen_zhi):
    """活六神: 从大安起子, 数至起卦时辰, 该宫为青龙, 依活神顺序(青龙朱雀勾陈白虎玄武腾蛇)按宫序排开"""
    qinglong_idx = (zhi_ordinal(shichen_zhi) - 1) % 6
    mapping = {}
    for k in range(6):
        mapping[GONGS[(qinglong_idx + k) % 6]] = HUOSHEN_ORDER[k]
    return mapping


def zefa(gua):
    """三宫地支择法: 位置天阳地阴人阳; 宫吉为阳凶为阴; 宫位阴阳相同取阴支, 不同取阳支"""
    pos_yy = ["阳", "阴", "阳"]
    out = []
    for g, py in zip(gua, pos_yy):
        gy = GONG_YINYANG_ZEFA[g]
        pick = "阴" if gy == py else "阳"
        out.append(ZEFA_ZHI[g][pick])
    return out


def render(gua, shichen_zhi=None, meta_lines=None, gender=None, day_ganzhi=None):
    tian, di, ren = gua
    L = []
    if meta_lines:
        L.extend(meta_lines)
    L.append("")
    L.append(f"【卦象】 {tian} {di} {ren}" + (f" {shichen_zhi}时" if shichen_zhi else ""))
    L.append("")
    L.append("── 三宫基本信息 ──")
    for pos, g in zip(["天宫(起因/过去/对方)", "地宫(经过/发展/关系)", "人宫·落宫(结果/当下/自身)"], gua):
        wx = WUXING[g] + (f"[{TU_TYPE[g]}]" if g in TU_TYPE else "")
        L.append(f"{pos}: {g} | 五行{wx} | {JIXIONG[g]} | {SISHEN[g]} | {GONGZHI[g]}")
        L.append(f"    主数{SHUZI[g]} | 藏支{CANGZHI[g]} | 八卦{BAGUA[g]} | {FANGWEI[g]}")
    L.append("")
    L.append("── 三宫生克(象义流向) ──")
    pairs = [("天", tian, "地", di), ("地", di, "人", ren), ("天", tian, "人", ren)]
    for pa, ga, pb, gb in pairs:
        rel = wx_relation(WUXING[ga], WUXING[gb])
        if rel == "比和":
            same = "(同宫)" if ga == gb else "(同五行异宫→小人/竞争之象)"
            L.append(f"{pa}宫{ga} 与 {pb}宫{gb}: 比和{same}")
        elif rel == "生":
            L.append(f"{pa}宫{ga}({WUXING[ga]}) 生 {pb}宫{gb}({WUXING[gb]})")
        elif rel == "被生":
            L.append(f"{pb}宫{gb}({WUXING[gb]}) 生 {pa}宫{ga}({WUXING[ga]})")
        elif rel == "克":
            L.append(f"{pa}宫{ga}({WUXING[ga]}) 克 {pb}宫{gb}({WUXING[gb]})")
        elif rel == "被克":
            L.append(f"{pb}宫{gb}({WUXING[gb]}) 克 {pa}宫{ga}({WUXING[ga]})")
    same_count = len(set(gua))
    if same_count == 1:
        L.append("※ 三宫相同: 直看落宫即可")
    elif same_count == 2:
        dup = [g for g in GONGS if gua.count(g) == 2][0]
        L.append(f"※ 两宫相同({dup}): 注意小人/朋友/第三者/竞争之象, 感情占尤要留意")
    L.append("")
    if shichen_zhi:
        swx = ZHI_WUXING[shichen_zhi]
        L.append(f"── 时辰参断 (时辰 {shichen_zhi}, 五行{swx}, {ZHI_YINYANG[shichen_zhi]}支) ──")
        # 体用
        luo_wx = WUXING[ren]
        rel = wx_relation(luo_wx, swx)
        if rel == "比和":
            gy = GONG_YINYANG_TIYONG[ren]
            zy = ZHI_YINYANG[shichen_zhi]
            if gy != zy:
                L.append(f"体用: 落宫{ren}({gy}{luo_wx}) 与 时辰{shichen_zhi}({zy}{swx}) 阴阳相异 → 比助(吉, 两相互助)")
            else:
                L.append(f"体用: 落宫{ren}({gy}{luo_wx}) 与 时辰{shichen_zhi}({zy}{swx}) 阴阳相同 → 比劫(凶, 竞争互损)")
        elif rel == "生":
            L.append(f"体用: 体生用({ren}{luo_wx}生时辰{swx}) → 小凶, 泄耗/付出/投资之象")
        elif rel == "被生":
            L.append(f"体用: 用生体(时辰{swx}生{ren}{luo_wx}) → 大吉, 外力相助, 发展趋势好")
        elif rel == "克":
            L.append(f"体用: 体克用({ren}{luo_wx}克时辰{swx}) → 小吉, 主动努力可得")
        elif rel == "被克":
            L.append(f"体用: 用克体(时辰{swx}克{ren}{luo_wx}) → 大凶, 受阻; 亦可解为考察/压力/克制")
        # 旺相休囚死 + 长生 + 墓
        L.append("各宫得令与长生状态:")
        for pos, g in zip(["天", "地", "人"], gua):
            gwx = WUXING[g]
            ws = wangshuai(gwx, swx)
            cs = changsheng(gwx, shichen_zhi)
            mu_flag = " ⚠入墓(困顿/收藏/闭塞/昏沉之象)" if MU[gwx] == shichen_zhi else ""
            L.append(f"  {pos}宫{g}({gwx}): {ws} | 十二长生临[{cs}]{mu_flag}")
        # 各宫与时辰生克
        L.append("各宫与时辰生克:")
        for pos, g in zip(["天", "地", "人"], gua):
            r = wx_relation(WUXING[g], swx)
            desc = {"生": f"{g}生时辰", "被生": f"时辰生{g}", "克": f"{g}克时辰", "被克": f"时辰克{g}", "比和": "与时辰比和"}[r]
            L.append(f"  {pos}宫{g}: {desc}")
        # 活六神
        hs = huoshen(shichen_zhi)
        L.append(f"活六神(以{shichen_zhi}时起): " + " ".join(f"{g}临{hs[g]}" for g in gua))
        L.append("(活神看内在: 性格/心情/实力/潜在想法; 与死六神合宫取象)")
        L.append("")
    # 地支择法
    zf = zefa(gua)
    L.append(f"── 三宫地支择法(主用于应期/路线, 忌在三宫内论刑冲破害合) ──")
    L.append(f"天{gua[0]}取{zf[0]} | 地{gua[1]}取{zf[1]} | 人{gua[2]}取{zf[2]}")
    L.append("")
    # 六亲(以落宫为我)
    L.append("── 六亲(以落宫为我) ──")
    for pos, g in zip(["天", "地"], [tian, di]):
        if g == ren:
            L.append(f"  {pos}宫{g}: 兄弟(同宫)")
        elif WUXING[g] == WUXING[ren]:
            L.append(f"  {pos}宫{g}: 小人(同五行异宫)")
        else:
            L.append(f"  {pos}宫{g}: {liuqin(WUXING[ren], g, WUXING[g])}")
    if day_ganzhi:
        L.append("")
        L.append(f"── 日干支: {day_ganzhi} (日支{day_ganzhi[1]}·{ZHI_WUXING[day_ganzhi[1]]}, 天气占/应期可用) ──")
    # 转太极
    if gender and shichen_zhi:
        zt = zhuan_taiji(gua, shichen_zhi, gender)
        if zt:
            res, tu_gong = zt
            L.append("")
            L.append(f"── 六亲转太极(土宫取{tu_gong}) ──")
            for name, arr in res.items():
                L.append(f"  {name}: {' '.join(arr)}")
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["date", "lunar", "numbers", "gua"])
    ap.add_argument("args", nargs="+")
    ap.add_argument("--independent", action="store_true", help="数字独立起法(每个数都从大安数)")
    ap.add_argument("--gender", choices=["男", "女"], default=None)
    ap.add_argument("--hour", default=None, help="numbers模式补充时辰支(如 未)")
    a = ap.parse_args()

    if a.mode == "date":
        import datetime
        try:
            import cnlunar
        except ImportError:
            print("请先安装: pip install cnlunar --break-system-packages", file=sys.stderr)
            sys.exit(1)
        dt = datetime.datetime.strptime(a.args[0], "%Y-%m-%d %H:%M")
        lun = cnlunar.Lunar(dt, godType="8char")
        lm, ld = lun.lunarMonth, lun.lunarDay
        leap = "(闰月, 按本月数)" if lun.isLunarLeapMonth else ""
        zhi = hour_to_zhi(dt.hour)
        # 三宫: 正月起大安 → 月上起日 → 日上起时
        i1 = (lm - 1) % 6
        i2 = (i1 + ld - 1) % 6
        i3 = (i2 + zhi_ordinal(zhi) - 1) % 6
        gua = (GONGS[i1], GONGS[i2], GONGS[i3])
        meta = [f"公历 {dt:%Y-%m-%d %H:%M} → 农历{lun.lunarYear}年{lm}月{ld}日{leap} {zhi}时",
                f"起法: 月上起日、日上起时(正月起大安)",
                f"四柱: {lun.year8Char} {lun.month8Char} {lun.day8Char} {lun.twohour8Char}"]
        print(render(gua, zhi, meta, a.gender, lun.day8Char))
    elif a.mode == "lunar":
        lm, ld, zhi = int(a.args[0]), int(a.args[1]), a.args[2]
        if zhi not in DIZHI:
            print("时辰支无效", file=sys.stderr); sys.exit(1)
        i1 = (lm - 1) % 6
        i2 = (i1 + ld - 1) % 6
        i3 = (i2 + zhi_ordinal(zhi) - 1) % 6
        gua = (GONGS[i1], GONGS[i2], GONGS[i3])
        meta = [f"农历{lm}月{ld}日 {zhi}时 (月上起日、日上起时)"]
        print(render(gua, zhi, meta, a.gender))
    elif a.mode == "gua":
        # 直接给三宫卦名: python3 qigua.py gua 大安 速喜 赤口 --hour 未
        alias = {"留恋": "留连", "流连": "留连", "榴莲": "留连"}
        gua = tuple(alias.get(g, g) for g in a.args[:3])
        for g in gua:
            if g not in GONGS:
                print(f"宫名无效: {g}", file=sys.stderr); sys.exit(1)
        zhi = a.hour if (a.hour in DIZHI) else None
        meta = ["直接输入卦象"]
        print(render(gua, zhi, meta, a.gender))
    else:  # numbers
        n1, n2, n3 = int(a.args[0]), int(a.args[1]), int(a.args[2])
        if min(n1, n2, n3) < 1:
            print("数字须为正整数", file=sys.stderr); sys.exit(1)
        gua = cast_from_counts(n1, n2, n3, a.independent)
        method = "独立起法(各数均从大安起)" if a.independent else "连续起法(次数从前一落宫续数)"
        meta = [f"数字起卦: {n1} {n2} {n3} | {method}"]
        zhi = a.hour if (a.hour in DIZHI) else None
        print(render(gua, zhi, meta, a.gender))


if __name__ == "__main__":
    main()
