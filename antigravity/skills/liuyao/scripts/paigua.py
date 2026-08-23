#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
六爻纳甲排盘脚本
用法:
  铜钱摇卦(随机):
    python3 paigua.py coin
  按公历时间起卦:
    python3 paigua.py date "2026-08-03 14:30"
  按数字起卦(报两个数+动爻数):
    python3 paigua.py numbers 5 3 2
  手动输入卦名(主卦名 [变卦名]):
    python3 paigua.py gua 天火同人
  手动输入爻象(从初爻到上爻, 7=少阳 8=少阴 9=老阳 6=老阴):
    python3 paigua.py yao 7 8 9 7 7 8
  可选参数:
    --datetime "2026-08-03 14:30"  指定占卦时间(用于排月建日辰六神)
    --dong 3                       指定动爻位(1-6)
"""
import sys, argparse, random, datetime

# ═══════════════════════════════════════════
# 基础常量
# ═══════════════════════════════════════════
TIANGAN = ["甲","乙","丙","丁","戊","己","庚","辛","壬","癸"]
DIZHI = ["子","丑","寅","卯","辰","巳","午","未","申","酉","戌","亥"]
WUXING_ZHI = {"子":"水","丑":"土","寅":"木","卯":"木","辰":"土","巳":"火",
              "午":"火","未":"土","申":"金","酉":"金","戌":"土","亥":"水"}
WUXING_GAN = {"甲":"木","乙":"木","丙":"火","丁":"火","戊":"土",
              "己":"土","庚":"金","辛":"金","壬":"水","癸":"水"}
SHENG = {"木":"火","火":"土","土":"金","金":"水","水":"木"}
KE   = {"木":"土","土":"水","水":"火","火":"金","金":"木"}

# 六亲: 以卦宫五行为"我"
def liu_qin(gong_wx, yao_wx):
    if gong_wx == yao_wx: return "兄弟"
    if SHENG[gong_wx] == yao_wx: return "子孙"
    if SHENG[yao_wx] == gong_wx: return "父母"
    if KE[gong_wx] == yao_wx: return "妻财"
    if KE[yao_wx] == gong_wx: return "官鬼"
    return "?"

# 六神(六兽): 按日干起, 甲乙起青龙
LIUSHEN = ["青龙","朱雀","勾陈","腾蛇","白虎","玄武"]
def get_liushen_start(ri_gan):
    mapping = {"甲":0,"乙":0,"丙":1,"丁":1,"戊":2,"己":3,"庚":4,"辛":4,"壬":5,"癸":5}
    return mapping.get(ri_gan, 0)

# ═══════════════════════════════════════════
# 八经卦 纳甲纳支
# ═══════════════════════════════════════════
# 每个经卦: (卦画[从下到上], 五行, 内卦天干, 外卦天干, 内卦地支[从下到上], 外卦地支[从下到上], 阴阳)
# 阳卦顺排: 乾甲子壬午, 震庚子庚午, 坎戊寅戊申, 艮丙辰丙戌
# 阴卦逆排: 坤乙未癸丑, 巽辛丑辛未, 离己卯己酉, 兑丁巳丁亥
JING_GUA = {
    "乾": {"hua":"111","wx":"金","nei_gan":"甲","wai_gan":"壬",
           "nei_zhi":["子","寅","辰"],"wai_zhi":["午","申","戌"],"yinyang":"阳"},
    "震": {"hua":"100","wx":"木","nei_gan":"庚","wai_gan":"庚",
           "nei_zhi":["子","寅","辰"],"wai_zhi":["午","申","戌"],"yinyang":"阳"},
    "坎": {"hua":"010","wx":"水","nei_gan":"戊","wai_gan":"戊",
           "nei_zhi":["寅","辰","午"],"wai_zhi":["申","戌","子"],"yinyang":"阳"},
    "艮": {"hua":"001","wx":"土","nei_gan":"丙","wai_gan":"丙",
           "nei_zhi":["辰","午","申"],"wai_zhi":["戌","子","寅"],"yinyang":"阳"},
    "坤": {"hua":"000","wx":"土","nei_gan":"乙","wai_gan":"癸",
           "nei_zhi":["未","巳","卯"],"wai_zhi":["丑","亥","酉"],"yinyang":"阴"},
    "巽": {"hua":"011","wx":"木","nei_gan":"辛","wai_gan":"辛",
           "nei_zhi":["丑","亥","酉"],"wai_zhi":["未","巳","卯"],"yinyang":"阴"},
    "离": {"hua":"101","wx":"火","nei_gan":"己","wai_gan":"己",
           "nei_zhi":["卯","丑","亥"],"wai_zhi":["酉","未","巳"],"yinyang":"阴"},
    "兑": {"hua":"110","wx":"金","nei_gan":"丁","wai_gan":"丁",
           "nei_zhi":["巳","卯","丑"],"wai_zhi":["亥","酉","未"],"yinyang":"阴"},
}

# 卦画到经卦名映射
HUA_TO_NAME = {v["hua"]:k for k,v in JING_GUA.items()}

# ═══════════════════════════════════════════
# 八宫六十四卦
# ═══════════════════════════════════════════
# 每宫8卦: 本宫(六世), 一世, 二世, 三世, 四世, 五世, 游魂, 归魂
# 存储格式: (卦名, 下卦经卦名, 上卦经卦名, 世爻位, 应爻位)
# 世应关系: 世在N, 应在N+3(mod 6), 本宫世在6应在3
BA_GONG = {}
GUA64_NAMES = {}  # 全名 -> (下卦名, 上卦名, 宫名, 世位, 应位)

def _init_bagong():
    """按卦变规则自动生成八宫六十四卦"""
    gong_order = ["乾","震","坎","艮","坤","巽","离","兑"]
    for gong in gong_order:
        base = list(JING_GUA[gong]["hua"] + JING_GUA[gong]["hua"])  # 6爻, 下3+上3
        gua_list = []
        # 本宫卦(八纯卦, 六世卦)
        cur = base[:]
        xia = HUA_TO_NAME["".join(cur[:3])]
        shang = HUA_TO_NAME["".join(cur[3:])]
        name = _gua_fullname(xia, shang)
        shi, ying = 6, 3
        gua_list.append((name, xia, shang, shi, ying))
        GUA64_NAMES[name] = (xia, shang, gong, shi, ying)
        # 一世到五世: 从初爻开始逐爻变
        prev = cur[:]
        for world in range(1, 6):
            idx = world - 1  # 变第几爻(0-indexed)
            prev[idx] = "0" if prev[idx] == "1" else "1"
            xia = HUA_TO_NAME["".join(prev[:3])]
            shang = HUA_TO_NAME["".join(prev[3:])]
            name = _gua_fullname(xia, shang)
            shi = world
            ying = (shi + 3 - 1) % 6 + 1
            gua_list.append((name, xia, shang, shi, ying))
            GUA64_NAMES[name] = (xia, shang, gong, shi, ying)
        # 游魂卦: 五世卦的第四爻再变回
        you = prev[:]
        you[3] = base[3]  # 第四爻变回本宫
        xia = HUA_TO_NAME["".join(you[:3])]
        shang = HUA_TO_NAME["".join(you[3:])]
        name = _gua_fullname(xia, shang)
        shi, ying = 4, 1
        gua_list.append((name, xia, shang, shi, ying))
        GUA64_NAMES[name] = (xia, shang, gong, shi, ying)
        # 归魂卦: 内卦三爻全部变回本宫
        gui = you[:]
        gui[0], gui[1], gui[2] = base[0], base[1], base[2]
        xia = HUA_TO_NAME["".join(gui[:3])]
        shang = HUA_TO_NAME["".join(gui[3:])]
        name = _gua_fullname(xia, shang)
        shi, ying = 3, 6
        gua_list.append((name, xia, shang, shi, ying))
        GUA64_NAMES[name] = (xia, shang, gong, shi, ying)
        BA_GONG[gong] = gua_list

# 卦全名: 用传统命名
_GUA_FULLNAME_TABLE = {
    ("乾","乾"):"乾为天",("坤","坤"):"坤为地",("坎","坎"):"坎为水",
    ("离","离"):"离为火",("震","震"):"震为雷",("巽","巽"):"巽为风",
    ("艮","艮"):"艮为山",("兑","兑"):"兑为泽",
    ("坤","乾"):"地天泰",("乾","坤"):"天地否",
    ("震","坎"):"雷水解",("坎","震"):"水雷屯",
    ("艮","坤"):"山地剥",("坤","艮"):"地山谦",
    ("巽","乾"):"风天小畜",("乾","巽"):"天风姤",
    ("离","坤"):"火地晋",("坤","离"):"地火明夷",
    ("兑","乾"):"泽天夬",("乾","兑"):"天泽履",
    ("震","乾"):"雷天大壮",("乾","震"):"天雷无妄",
    ("坎","坤"):"水地比",("坤","坎"):"地水师",
    ("艮","乾"):"山天大畜",("乾","艮"):"天山遁",
    ("巽","坤"):"风地观",("坤","巽"):"地风升",
    ("离","乾"):"火天大有",("乾","离"):"天火同人",
    ("兑","坤"):"泽地萃",("坤","兑"):"地泽临",
    ("震","坤"):"雷地豫",("坤","震"):"地雷复",
    ("巽","坎"):"风水涣",("坎","巽"):"水风井",
    ("离","艮"):"火山旅",("艮","离"):"山火贲",
    ("兑","震"):"泽雷随",("震","兑"):"雷泽归妹",
    ("艮","坎"):"山水蒙",("坎","艮"):"水山蹇",
    ("巽","艮"):"风山渐",("艮","巽"):"山风蛊",
    ("离","坎"):"火水未济",("坎","离"):"水火既济",
    ("兑","巽"):"泽风大过",("巽","兑"):"风泽中孚",
    ("震","艮"):"雷山小过",("艮","震"):"山雷颐",
    ("离","兑"):"火泽睽",("兑","离"):"泽火革",
    ("坎","乾"):"水天需",("乾","坎"):"天水讼",
    ("巽","离"):"风火家人",("离","巽"):"火风鼎",
    ("震","离"):"雷火丰",("离","震"):"火雷噬嗑",
    ("兑","坎"):"泽水困",("坎","兑"):"水泽节",
    ("艮","兑"):"山泽损",("兑","艮"):"泽山咸",
    ("巽","震"):"风雷益",("震","巽"):"雷风恒",
}

def _gua_fullname(xia, shang):
    key = (xia, shang)
    if key in _GUA_FULLNAME_TABLE:
        return _GUA_FULLNAME_TABLE[key]
    # fallback: 用经卦象名拼接
    xiang = {"乾":"天","坤":"地","坎":"水","离":"火","震":"雷","巽":"风","艮":"山","兑":"泽"}
    return xiang[xia] + xiang[shang] + "卦"

# ═══════════════════════════════════════════
# 干支历法
# ═══════════════════════════════════════════
def _gan_idx(g): return TIANGAN.index(g)
def _zhi_idx(z): return DIZHI.index(z)

def date_to_ganzhi(dt):
    """公历日期时间 -> (年干支, 月干支, 日干支, 时干支)  简化版本"""
    try:
        from cnlunar import Lunar
        ln = Lunar(dt)
        y_gz = ln.year8Char
        m_gz = ln.month8Char
        d_gz = ln.day8Char
        t_gz = ln.twohour8Char
        return y_gz, m_gz, d_gz, t_gz
    except ImportError:
        pass
    # fallback: 日干支查表法(以2000-01-01为甲子日)
    base = datetime.datetime(2000, 1, 1)
    delta = (dt.date() - base.date()).days
    ri_gz_idx = delta % 60
    ri_gan = TIANGAN[ri_gz_idx % 10]
    ri_zhi = DIZHI[ri_gz_idx % 12]
    # 时辰
    hour = dt.hour
    shi_zhi_idx = ((hour + 1) // 2) % 12
    shi_zhi = DIZHI[shi_zhi_idx]
    # 时干(日上起时): 甲己起甲子, 乙庚起丙子...
    ri_gan_group = _gan_idx(ri_gan) % 5
    shi_gan_start = (ri_gan_group * 2) % 10
    shi_gan = TIANGAN[(shi_gan_start + shi_zhi_idx) % 10]
    # 月干支(简化: 取农历月对应地支, 正月寅)
    month = dt.month
    # 简化处理: 以公历月近似
    yue_zhi_idx = (month + 1) % 12  # 近似: 正月=寅
    yue_zhi = DIZHI[yue_zhi_idx]
    # 年干支(简化)
    year = dt.year
    nian_gan = TIANGAN[(year - 4) % 10]
    nian_zhi = DIZHI[(year - 4) % 12]
    # 月干(年上起月)
    nian_gan_group = _gan_idx(nian_gan) % 5
    yue_gan_start = (nian_gan_group * 2 + 2) % 10
    yue_gan = TIANGAN[(yue_gan_start + yue_zhi_idx - 2) % 10]
    return nian_gan+nian_zhi, yue_gan+yue_zhi, ri_gan+ri_zhi, shi_gan+shi_zhi

def get_xunkong(ri_gz):
    """根据日干支算旬空(两个地支)"""
    gi = _gan_idx(ri_gz[0])
    zi = _zhi_idx(ri_gz[1])
    # 本旬起始地支序 = zi - gi (mod 12)
    start_zhi = (zi - gi) % 12
    # 旬空 = 本旬起始+10, +11
    k1 = DIZHI[(start_zhi + 10) % 12]
    k2 = DIZHI[(start_zhi + 11) % 12]
    return k1, k2

def get_yupo(yue_zhi):
    """月破: 与月建地支六冲的地支"""
    chong_map = {"子":"午","丑":"未","寅":"申","卯":"酉","辰":"戌","巳":"亥",
                 "午":"子","未":"丑","申":"寅","酉":"卯","戌":"辰","亥":"巳"}
    return chong_map.get(yue_zhi, "")

# ═══════════════════════════════════════════
# 伏神
# ═══════════════════════════════════════════
def find_fushen(gua_info, gong_name):
    """查找卦中缺少的六亲, 从本宫八纯卦中找伏神"""
    existing_qin = set()
    for yao in gua_info:
        existing_qin.add(yao["liuqin"])
    all_qin = {"父母","兄弟","子孙","妻财","官鬼"}
    missing = all_qin - existing_qin
    if not missing:
        return []
    # 本宫八纯卦
    gong_gua = JING_GUA[gong_name]
    gong_wx = gong_gua["wx"]
    # 本宫纯卦六爻
    nei_zhi = gong_gua["nei_zhi"]
    wai_zhi = gong_gua["wai_zhi"]
    nei_gan = gong_gua["nei_gan"]
    wai_gan = gong_gua["wai_gan"]
    ben_gong_yaos = []
    for i in range(3):
        zhi = nei_zhi[i]
        gan = nei_gan
        ben_gong_yaos.append({"pos":i+1,"gan":gan,"zhi":zhi,"wx":WUXING_ZHI[zhi],
                              "liuqin":liu_qin(gong_wx, WUXING_ZHI[zhi])})
    for i in range(3):
        zhi = wai_zhi[i]
        gan = wai_gan
        ben_gong_yaos.append({"pos":i+4,"gan":gan,"zhi":zhi,"wx":WUXING_ZHI[zhi],
                              "liuqin":liu_qin(gong_wx, WUXING_ZHI[zhi])})
    fushen_list = []
    for qin in missing:
        for byao in ben_gong_yaos:
            if byao["liuqin"] == qin:
                fushen_list.append({
                    "missing_qin": qin,
                    "fu_pos": byao["pos"],
                    "fu_gan": byao["gan"],
                    "fu_zhi": byao["zhi"],
                    "fu_wx": byao["wx"],
                })
                break
    return fushen_list

# ═══════════════════════════════════════════
# 装卦主函数
# ═══════════════════════════════════════════
def zhuang_gua(xia_name, shang_name, dong_yaos=None, dt=None):
    """
    装卦: 给定上下经卦名和动爻, 输出完整卦信息
    dong_yaos: list of int (1-6), 动爻位置
    dt: datetime, 占卦时间
    """
    if dong_yaos is None:
        dong_yaos = []

    fullname = _gua_fullname(xia_name, shang_name)
    if fullname not in GUA64_NAMES:
        # 尝试反查
        for fn, info in GUA64_NAMES.items():
            if info[0] == xia_name and info[1] == shang_name:
                fullname = fn
                break
    info = GUA64_NAMES.get(fullname)
    if not info:
        print(f"错误: 无法找到卦 {xia_name}/{shang_name}")
        return None
    _, _, gong_name, shi_pos, ying_pos = info
    gong_wx = JING_GUA[gong_name]["wx"]

    # 纳甲纳支
    xia_gua = JING_GUA[xia_name]
    shang_gua = JING_GUA[shang_name]
    yaos = []
    for i in range(3):
        zhi = xia_gua["nei_zhi"][i]
        gan = xia_gua["nei_gan"]
        wx = WUXING_ZHI[zhi]
        yin_yang = "—" if xia_gua["hua"][i] == "1" else "- -"
        yaos.append({
            "pos": i+1, "gan": gan, "zhi": zhi, "wx": wx,
            "yinyang_mark": yin_yang,
            "liuqin": liu_qin(gong_wx, wx),
            "is_shi": (i+1)==shi_pos, "is_ying": (i+1)==ying_pos,
            "is_dong": (i+1) in dong_yaos,
        })
    for i in range(3):
        zhi = shang_gua["wai_zhi"][i]
        gan = shang_gua["wai_gan"]
        wx = WUXING_ZHI[zhi]
        yin_yang = "—" if shang_gua["hua"][i] == "1" else "- -"
        yaos.append({
            "pos": i+4, "gan": gan, "zhi": zhi, "wx": wx,
            "yinyang_mark": yin_yang,
            "liuqin": liu_qin(gong_wx, wx),
            "is_shi": (i+4)==shi_pos, "is_ying": (i+4)==ying_pos,
            "is_dong": (i+4) in dong_yaos,
        })

    # 变卦(如有动爻)
    bian_gua = None
    bian_yaos = None
    if dong_yaos:
        hua = list(xia_gua["hua"] + shang_gua["hua"])
        for d in dong_yaos:
            idx = d - 1
            hua[idx] = "0" if hua[idx] == "1" else "1"
        bian_xia = HUA_TO_NAME.get("".join(hua[:3]))
        bian_shang = HUA_TO_NAME.get("".join(hua[3:]))
        if bian_xia and bian_shang:
            bian_fullname = _gua_fullname(bian_xia, bian_shang)
            bian_info = GUA64_NAMES.get(bian_fullname)
            bian_gong = bian_info[2] if bian_info else gong_name
            # 变卦的六亲仍以主卦卦宫五行为准
            bxg = JING_GUA[bian_xia]
            bsg = JING_GUA[bian_shang]
            bian_yaos = []
            for i in range(3):
                zhi = bxg["nei_zhi"][i]
                gan = bxg["nei_gan"]
                wx = WUXING_ZHI[zhi]
                bian_yaos.append({"pos":i+1,"gan":gan,"zhi":zhi,"wx":wx,
                                  "liuqin":liu_qin(gong_wx, wx)})
            for i in range(3):
                zhi = bsg["wai_zhi"][i]
                gan = bsg["wai_gan"]
                wx = WUXING_ZHI[zhi]
                bian_yaos.append({"pos":i+4,"gan":gan,"zhi":zhi,"wx":wx,
                                  "liuqin":liu_qin(gong_wx, wx)})
            bian_gua = {"name": bian_fullname, "xia": bian_xia, "shang": bian_shang}

    # 日期相关: 月建日辰六神旬空
    ri_gan, ri_zhi, yue_zhi = "甲", "子", "子"
    nian_gz, yue_gz, ri_gz, shi_gz = "", "", "", ""
    if dt:
        nian_gz, yue_gz, ri_gz, shi_gz = date_to_ganzhi(dt)
        ri_gan = ri_gz[0]
        ri_zhi = ri_gz[1]
        yue_zhi = yue_gz[1]

    xunkong = get_xunkong(ri_gan + ri_zhi) if dt else ("","")
    yupo = get_yupo(yue_zhi) if dt else ""

    # 六神
    ls_start = get_liushen_start(ri_gan)
    for yao in yaos:
        idx = yao["pos"] - 1
        yao["liushen"] = LIUSHEN[(ls_start + idx) % 6]
        yao["xunkong"] = yao["zhi"] in xunkong
        yao["yupo"] = yao["zhi"] == yupo

    # 伏神
    fushen = find_fushen(yaos, gong_name)

    # 标注动爻变爻关系
    for yao in yaos:
        if yao["is_dong"] and bian_yaos:
            by = bian_yaos[yao["pos"]-1]
            yao["bian_zhi"] = by["zhi"]
            yao["bian_wx"] = by["wx"]
            yao["bian_qin"] = by["liuqin"]
            # 回头生克
            if SHENG[by["wx"]] == yao["wx"] or by["wx"] == yao["wx"]:
                pass  # 变爻生本爻或比和
            y_wx, b_wx = yao["wx"], by["wx"]
            if SHENG.get(b_wx) == y_wx:
                yao["huishou"] = "回头生"
            elif KE.get(b_wx) == y_wx:
                yao["huishou"] = "回头克"
            # 进退神
            yi = _zhi_idx(yao["zhi"])
            bi = _zhi_idx(by["zhi"])
            if yao["wx"] == by["wx"]:
                # 同五行看地支序
                if (bi - yi) % 12 <= 6 and bi != yi:
                    yao["jintui"] = "化进神"
                elif bi != yi:
                    yao["jintui"] = "化退神"
            # 化墓化绝
            mu_map = {"木":"未","火":"戌","金":"丑","水":"辰","土":"辰"}
            if by["zhi"] == mu_map.get(yao["wx"]):
                yao["huamu"] = "化墓"

    # 月建旺衰
    yue_wx = WUXING_ZHI.get(yue_zhi, "")
    ri_wx = WUXING_ZHI.get(ri_zhi, "")
    for yao in yaos:
        states = []
        if yue_wx:
            if yao["wx"] == yue_wx: states.append("月旺")
            elif SHENG[yue_wx] == yao["wx"]: states.append("月相")
            elif SHENG[yao["wx"]] == yue_wx: states.append("月休")
            elif KE[yue_wx] == yao["wx"]: states.append("月囚")
            elif KE[yao["wx"]] == yue_wx: states.append("月死")
        if ri_wx:
            if yao["wx"] == ri_wx: states.append("日旺")
            elif SHENG[ri_wx] == yao["wx"]: states.append("日生")
            elif KE[ri_wx] == yao["wx"]: states.append("日克")
        yao["wangshuai"] = states

    return {
        "name": fullname,
        "gong": gong_name,
        "gong_wx": gong_wx,
        "xia": xia_name,
        "shang": shang_name,
        "shi": shi_pos,
        "ying": ying_pos,
        "yaos": yaos,
        "dong": dong_yaos,
        "bian": bian_gua,
        "bian_yaos": bian_yaos,
        "fushen": fushen,
        "nian_gz": nian_gz,
        "yue_gz": yue_gz,
        "ri_gz": ri_gz,
        "shi_gz": shi_gz,
        "xunkong": xunkong,
        "yupo": yupo,
    }

# ═══════════════════════════════════════════
# 起卦方法
# ═══════════════════════════════════════════
def coin_qigua():
    """铜钱摇卦: 模拟摇六次, 返回六爻(从初爻到上爻)"""
    results = []
    for _ in range(6):
        # 三枚铜钱: 正(字)=2, 反(花)=3
        coins = [random.choice([2,3]) for _ in range(3)]
        total = sum(coins)
        # 6=老阴(动), 7=少阳(静), 8=少阴(静), 9=老阳(动)
        results.append(total)
    return results

def yao_to_gua(yao_list):
    """
    六爻序列(6/7/8/9从初爻到上爻) -> (下卦名, 上卦名, 动爻列表)
    7=少阳(—), 8=少阴(- -), 9=老阳(—动), 6=老阴(- -动)
    """
    hua = []
    dong = []
    for i, y in enumerate(yao_list):
        if y in (7, 9):
            hua.append("1")  # 阳
        else:
            hua.append("0")  # 阴
        if y in (6, 9):
            dong.append(i + 1)
    xia = HUA_TO_NAME.get("".join(hua[:3]))
    shang = HUA_TO_NAME.get("".join(hua[3:]))
    return xia, shang, dong

def number_qigua(n1, n2, n3):
    """
    数字起卦: n1取下卦, n2取上卦, n3取动爻
    下卦 = (n1-1)%8+1 对应先天八卦序
    上卦 = (n2-1)%8+1
    动爻 = (n3-1)%6+1
    """
    xiantian = ["乾","兑","离","震","巽","坎","艮","坤"]
    xia_idx = (n1 - 1) % 8
    shang_idx = (n2 - 1) % 8
    dong_pos = (n3 - 1) % 6 + 1
    return xiantian[xia_idx], xiantian[shang_idx], [dong_pos]

def name_to_gua(name):
    """卦名查找"""
    if name in GUA64_NAMES:
        info = GUA64_NAMES[name]
        return info[0], info[1]
    # 模糊匹配
    for fn in GUA64_NAMES:
        if name in fn:
            info = GUA64_NAMES[fn]
            return info[0], info[1]
    return None, None

# ═══════════════════════════════════════════
# 输出格式化
# ═══════════════════════════════════════════
def format_output(gua):
    lines = []
    lines.append(f"{'═'*50}")
    lines.append(f"  {gua['gong']}宫: {gua['name']}")
    if gua['bian']:
        lines.append(f"  变卦: {gua['bian']['name']}")
    lines.append(f"  卦宫五行: {gua['gong_wx']}")
    if gua['ri_gz']:
        lines.append(f"  年:{gua['nian_gz']} 月:{gua['yue_gz']} 日:{gua['ri_gz']} 时:{gua['shi_gz']}")
        lines.append(f"  旬空: {gua['xunkong'][0]}{gua['xunkong'][1]}  月破: {gua['yupo']}")
    lines.append(f"{'═'*50}")

    # 从上爻到初爻显示(传统排列)
    header = f"{'六神':　<4}{'六亲':　<4}{'卦爻':　<8}{'世应':　<4}"
    if gua['bian']:
        header += f"  {'变爻':　<8}{'变亲':　<4}"
    lines.append(header)
    lines.append("─" * 50)

    for i in range(5, -1, -1):
        yao = gua['yaos'][i]
        pos_names = ["初","二","三","四","五","上"]
        # 爻画
        mark = yao['yinyang_mark']
        if yao['is_dong']:
            mark += " ○" if "—" in mark else " ×"

        sa = ""
        if yao['is_shi']: sa = "世"
        if yao['is_ying']: sa = "应"

        dong_mark = ""
        if yao.get('xunkong'): dong_mark += "空"
        if yao.get('yupo'): dong_mark += "破"
        ws = ",".join(yao.get('wangshuai', []))

        line = f"  {yao['liushen']:　<4}{yao['liuqin']:　<4}{yao['gan']}{yao['zhi']}{yao['wx']:　<3}{mark:　<6}{sa:　<3}"

        if yao['is_dong'] and gua.get('bian_yaos'):
            by = gua['bian_yaos'][i]
            huishou = yao.get('huishou', '')
            jintui = yao.get('jintui', '')
            huamu = yao.get('huamu', '')
            extra = " ".join(filter(None, [huishou, jintui, huamu]))
            line += f"  → {by['gan']}{by['zhi']}{by['wx']:　<3}{by['liuqin']:　<4}{extra}"

        if dong_mark or ws:
            line += f"  [{dong_mark} {ws}]".strip()

        lines.append(line)

    # 伏神
    if gua['fushen']:
        lines.append("─" * 50)
        lines.append("【伏神】")
        for fs in gua['fushen']:
            fly_yao = gua['yaos'][fs['fu_pos']-1]
            lines.append(f"  {fs['missing_qin']}: {fs['fu_gan']}{fs['fu_zhi']}{fs['fu_wx']} "
                         f"伏于{fly_yao['pos']}爻({fly_yao['liuqin']}{fly_yao['gan']}{fly_yao['zhi']})下")

    lines.append(f"{'═'*50}")
    # 技术标注
    lines.append("【技术标注·断卦底稿】")
    lines.append(f"主卦: {gua['name']}  宫: {gua['gong']}({gua['gong_wx']})")
    lines.append(f"世爻: {gua['shi']}爻  应爻: {gua['ying']}爻")
    if gua['dong']:
        lines.append(f"动爻: {gua['dong']}")
    if gua['bian']:
        lines.append(f"变卦: {gua['bian']['name']}")
    if gua['ri_gz']:
        yue_wx = WUXING_ZHI.get(gua['yue_gz'][1], '')
        ri_wx = WUXING_ZHI.get(gua['ri_gz'][1], '')
        lines.append(f"月建: {gua['yue_gz']}({yue_wx})  日辰: {gua['ri_gz']}({ri_wx})")

    # 用神提示
    shi_yao = gua['yaos'][gua['shi']-1]
    ying_yao = gua['yaos'][gua['ying']-1]
    lines.append(f"世爻: {shi_yao['liuqin']}{shi_yao['gan']}{shi_yao['zhi']}({shi_yao['wx']})")
    lines.append(f"应爻: {ying_yao['liuqin']}{ying_yao['gan']}{ying_yao['zhi']}({ying_yao['wx']})")

    # 各爻旺衰一览
    lines.append("─ 爻旺衰 ─")
    for yao in gua['yaos']:
        ws = ",".join(yao.get('wangshuai', [])) or "平"
        xk = " 旬空" if yao.get('xunkong') else ""
        yp = " 月破" if yao.get('yupo') else ""
        lines.append(f"  {yao['pos']}爻 {yao['liuqin']}{yao['gan']}{yao['zhi']}({yao['wx']}): {ws}{xk}{yp}")

    return "\n".join(lines)

# ═══════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════
def main():
    _init_bagong()

    parser = argparse.ArgumentParser(description="六爻纳甲排盘")
    sub = parser.add_subparsers(dest="mode")

    # coin
    p_coin = sub.add_parser("coin", help="铜钱摇卦(随机)")
    p_coin.add_argument("--datetime", type=str, help="占卦时间 YYYY-MM-DD HH:MM")

    # date
    p_date = sub.add_parser("date", help="时间起卦")
    p_date.add_argument("datetime_str", type=str, help="公历时间 YYYY-MM-DD HH:MM")

    # numbers
    p_num = sub.add_parser("numbers", help="数字起卦")
    p_num.add_argument("n1", type=int, help="第一个数(取下卦)")
    p_num.add_argument("n2", type=int, help="第二个数(取上卦)")
    p_num.add_argument("n3", type=int, help="第三个数(取动爻)")
    p_num.add_argument("--datetime", type=str, help="占卦时间")

    # gua
    p_gua = sub.add_parser("gua", help="输入卦名")
    p_gua.add_argument("name", type=str, help="主卦全名")
    p_gua.add_argument("--dong", type=int, nargs="*", help="动爻位(1-6)")
    p_gua.add_argument("--datetime", type=str, help="占卦时间")

    # yao
    p_yao = sub.add_parser("yao", help="输入六爻爻象")
    p_yao.add_argument("yaos", type=int, nargs=6, help="从初爻到上爻(6/7/8/9)")
    p_yao.add_argument("--datetime", type=str, help="占卦时间")

    args = parser.parse_args()
    if not args.mode:
        parser.print_help()
        return

    dt = None
    dt_str = getattr(args, 'datetime', None) or (args.datetime_str if args.mode == 'date' else None)
    if dt_str:
        for fmt in ["%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M"]:
            try:
                dt = datetime.datetime.strptime(dt_str, fmt)
                break
            except ValueError:
                continue
        if not dt:
            print(f"无法解析时间: {dt_str}")
            return
    else:
        dt = datetime.datetime.now()

    if args.mode == "coin":
        yao_list = coin_qigua()
        print(f"摇卦结果(初→上): {yao_list}")
        yao_names = {6:"老阴×",7:"少阳",8:"少阴",9:"老阳○"}
        for i, y in enumerate(yao_list):
            pos = ["初","二","三","四","五","上"][i]
            print(f"  {pos}爻: {y} ({yao_names[y]})")
        xia, shang, dong = yao_to_gua(yao_list)
        gua = zhuang_gua(xia, shang, dong, dt)

    elif args.mode == "date":
        # 时间起卦: 用年月日时数起卦
        nian_gz, yue_gz, ri_gz, shi_gz = date_to_ganzhi(dt)
        # 下卦 = (年支序+月支序+日支序) % 8
        # 上卦 = (年支序+月支序+日支序+时支序) % 8
        # 动爻 = 总数 % 6
        y = _zhi_idx(nian_gz[1]) + 1
        m = _zhi_idx(yue_gz[1]) + 1
        d = _zhi_idx(ri_gz[1]) + 1
        h = _zhi_idx(shi_gz[1]) + 1
        xiantian = ["乾","兑","离","震","巽","坎","艮","坤"]
        xia_idx = (y + m + d - 1) % 8
        shang_idx = (y + m + d + h - 1) % 8
        dong_pos = (y + m + d + h - 1) % 6 + 1
        xia = xiantian[xia_idx]
        shang = xiantian[shang_idx]
        print(f"时间起卦: {dt.strftime('%Y-%m-%d %H:%M')}")
        print(f"干支: {nian_gz} {yue_gz} {ri_gz} {shi_gz}")
        gua = zhuang_gua(xia, shang, [dong_pos], dt)

    elif args.mode == "numbers":
        xia, shang, dong = number_qigua(args.n1, args.n2, args.n3)
        print(f"数字起卦: {args.n1} {args.n2} {args.n3}")
        gua = zhuang_gua(xia, shang, dong, dt)

    elif args.mode == "gua":
        xia, shang = name_to_gua(args.name)
        if not xia:
            print(f"找不到卦: {args.name}")
            return
        dong = args.dong or []
        gua = zhuang_gua(xia, shang, dong, dt)

    elif args.mode == "yao":
        xia, shang, dong = yao_to_gua(args.yaos)
        if not xia:
            print("爻象有误，无法识别卦")
            return
        print(f"爻象起卦: {args.yaos}")
        gua = zhuang_gua(xia, shang, dong, dt)

    if gua:
        print(format_output(gua))

if __name__ == "__main__":
    main()
