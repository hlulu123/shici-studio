"""Build shici-studio/assets from downloaded third-party data.

Usage:
    PYTHONPATH=<dir with pypinyin> python3 -I tools/build_data.py <download_dir> <skill_dir>

<download_dir> layout:
    pingshui/pingshui.json          rbnyng/pingshui_rhyme organized_ping_ze_rhyme_dict.json (MIT)
    cwr/Cilin_Rhyme.json            charlesix59/chinese_word_rhyme (MIT)
    opencc/TSCharacters.txt         BYVoid/OpenCC (Apache-2.0)
    cp/tangshisanbaishou.json       chinese-poetry (MIT)
    cp/qianjiashi.json
    cp/songci300.json
    cp/ci.db                        full Song ci, used for the extended corpus
    cp/tang/poet.tang.*.json        full Tang poetry, used for character frequency and the extended corpus
"""
import collections
import glob
import json
import os
import re
import sys

import pypinyin
from pypinyin import Style

DL, SKILL = sys.argv[1], sys.argv[2]
ASSETS = os.path.join(SKILL, "assets")
os.makedirs(os.path.join(ASSETS, "rhyme"), exist_ok=True)
os.makedirs(os.path.join(ASSETS, "corpus"), exist_ok=True)


def load_t2s():
    m = {}
    with open(os.path.join(DL, "opencc", "TSCharacters.txt"), encoding="utf-8") as f:
        for line in f:
            if line.startswith("#") or "\t" not in line:
                continue
            k, v = line.rstrip("\n").split("\t", 1)
            m[k] = v.split(" ")[0]
    return m


T2S = load_t2s()


def s(text):
    return "".join(T2S.get(c, c) for c in text)


# ---------------------------------------------------------------- pinyin helpers
def readings(ch):
    """[(initial, final, tone)] for every Mandarin reading pypinyin knows."""
    out = []
    finals = pypinyin.pinyin(ch, style=Style.FINALS_TONE3, heteronym=True, strict=True,
                             neutral_tone_with_five=True)[0]
    initials = pypinyin.pinyin(ch, style=Style.INITIALS, heteronym=True, strict=True)[0]
    if finals == [ch]:
        return out
    for i, fin in enumerate(finals):
        ini = initials[i] if i < len(initials) else initials[0]
        m = re.match(r"([a-zü]+)([1-5])$", fin.replace("ü", "v"))
        if m:
            out.append((ini, m.group(1), int(m.group(2))))
    return out


XINYUN_NAMES = ["", "麻", "波", "皆", "开", "微", "豪", "尤", "寒", "文", "唐", "庚", "齐", "支", "姑"]
XINYUN_FINALS = {
    1: {"a", "ia", "ua"}, 2: {"o", "uo", "e", "io"}, 3: {"ie", "ve"}, 4: {"ai", "uai"},
    5: {"ei", "uei"}, 6: {"ao", "iao"}, 7: {"ou", "iou"}, 8: {"an", "ian", "uan", "van"},
    9: {"en", "in", "uen", "vn"}, 10: {"ang", "iang", "uang"},
    11: {"eng", "ing", "ong", "iong", "ueng"}, 12: {"i", "er", "v"}, 14: {"u"},
}
ZCS = {"zh", "ch", "sh", "r", "z", "c", "s"}


def xinyun_bu(ini, fin):
    if fin == "i" and ini in ZCS:
        return 13
    for bu, fs in XINYUN_FINALS.items():
        if fin in fs:
            return bu
    return 0


# ---------------------------------------------------------------- 平水韵
SHENG_NAMES = {"上平聲部": "上平", "下平聲部": "下平", "上聲部": "上声", "去聲部": "去声", "入聲部": "入声"}
TONE_OF = {"上平": "平", "下平": "平", "上声": "上", "去声": "去", "入声": "入"}

# 词林正韵: 平水韵目代表字 -> 部 ; tuple means the 韵 is split ("半") and decided by modern final
CILIN = {}
for bu, names in {
    1: "东冬董肿送宋", 2: "江阳讲养绛漾", 3: "支微齐纸尾荠寘未霁", 4: "鱼虞语麌御遇",
    6: "真文轸吻震问", 7: "寒删先旱潸铣翰谏霰", 8: "萧肴豪筱巧皓啸效号", 9: "歌哿个",
    10: "麻马祃", 11: "庚青蒸梗迥敬径", 12: "尤有宥", 13: "侵寝沁", 14: "覃盐咸感琰豏勘艳陷",
    15: "屋沃", 16: "觉药", 17: "质陌锡职缉", 18: "物月曷黠屑叶", 19: "合洽", 5: "蟹",
}.items():
    for n in names:
        CILIN[n] = bu
# 常用而源数据漏收的字，韵目有把握的直接指定（其余按今音推定）
MANUAL_YUN = {"啼": "上平八齐", "堤": "上平八齐", "迹": "入声十一陌", "涩": "入声十四缉", "抄": "下平三肴",
              "遍": "去声十七霰", "懒": "上声十四旱", "灶": "去声二十号", "坞": "上声七麌", "盏": "上声十五潸",
              "碗": "上声十四旱", "惭": "下平十三覃", "炉": "上平七虞", "葱": "上平一东", "粗": "上平七虞",
              "昂": "下平七阳", "扫": "上声十九皓", "燃": "下平一先"}
VARIANTS = {"樽": "尊", "罇": "尊", "徭": "傜", "盃": "杯", "牕": "窗", "鉏": "锄", "缐": "线",
            "沉": "沈", "锺": "钟", "徧": "遍", "覷": "觑", "跡": "迹", "蹟": "迹"}

# OpenCC gives variant forms for a few 韵目 names; use the conventional ones
YUN_NAME_FIX = {"筿": "筱", "箇": "个", "禡": "祃", "豔": "艳"}
SPLIT = {"灰": (3, 5), "贿": (3, 5), "队": (3, 5), "泰": (3, 5),
         "佳": (5, 10), "卦": (5, 10), "元": (6, 7), "阮": (6, 7), "愿": (6, 7)}


def split_bu(yun_char, ch):
    lo, hi = SPLIT[yun_char]
    finals = {f for _, f, _ in readings(ch)}
    res = set()
    for f in finals:
        if (lo, hi) == (3, 5):
            res.add(5 if f in ("ai", "a") else 3)   # 合口（外、块）归第三部
        elif (lo, hi) == (5, 10):
            res.add(10 if f in ("a", "ia", "ua") else 5)
        else:
            res.add(7 if f.endswith("an") else 6)
    return sorted(res) or [lo, hi]


def fill_from_cilin(yunmu, chars, cilin_chars):
    """平水韵源数据漏收了一些常用字（啼、迹、遍、惭……）。用词林正韵补：平仄可靠；
    具体韵目在同部同声的候选里按今音声韵相近推定，并记入 inferred，押韵检查对它们只给提示。"""
    cl = json.load(open(os.path.join(DL, "cwr", "Cilin_Rhyme.json"), encoding="utf-8"))
    bu_num = {"第%s部" % n: i for i, n in enumerate("一二三四五六七八九十", 1)}
    bu_num.update({"第十%s部" % n: 10 + i for i, n in enumerate("一二三四五六七八九", 1)})
    # 每个韵目成员的今音分布，用来给缺字挑最像的韵目
    profile = [collections.Counter() for _ in yunmu]
    for c, ids in chars.items():
        for ini, fin, _ in readings(c)[:1]:
            for i in ids:
                profile[i][(ini, fin)] += 3
                profile[i][fin] += 1
    inferred = set()
    for bu_name, secs in cl.items():
        bu = bu_num[bu_name]
        for sheng, members in secs.items():
            pz = "平" if sheng == "平声" else "仄"
            want_tone = {"平声": ("平",), "入声": ("入",)}.get(sheng, ("上", "去"))
            cands = [i for i, y in enumerate(yunmu) if y["tone"] in want_tone and
                     (y.get("cilin") == bu or bu in y.get("cilin_split", []))]
            for c in members:
                if c in chars or not cands or not re.match("[\u3400-\u9fff\U00020000-\U0003134f]$", c):
                    continue
                rd = readings(c)[:1]
                key = rd[0][:2] if rd else None
                if c in MANUAL_YUN:
                    best = next(i for i, y in enumerate(yunmu) if y["id"] == MANUAL_YUN[c])
                else:
                    # 按占比而不是个数打分，免得支韵这类大韵吞掉一切
                    best = max(cands, key=lambda i: (3.0 * profile[i][key] + profile[i][key[1]]) /
                               (sum(profile[i].values()) or 1) if key else 0)
                chars[c].append(best)
                if "cilin_split" in yunmu[best]:
                    cilin_chars[c].add(bu)
                inferred.add(c)
                assert yunmu[best]["pz"] == pz
    return inferred


def build_pingshui():
    raw = json.load(open(os.path.join(DL, "pingshui", "pingshui.json"), encoding="utf-8"))
    yunmu, chars = [], collections.defaultdict(list)
    cilin_chars = collections.defaultdict(set)
    for pz in ("ping", "ze"):
        for part, yuns in raw[pz].items():
            sheng = SHENG_NAMES[part]
            for name, (members,) in yuns.items():
                num_yun = s(name.replace(part.replace("部", ""), ""))   # e.g. 七阳
                num_yun = num_yun[:-1] + YUN_NAME_FIX.get(num_yun[-1], num_yun[-1])
                yun_char = num_yun[-1]
                idx = len(yunmu)
                entry = {"id": sheng + num_yun, "sheng": sheng, "tone": TONE_OF[sheng],
                         "pz": "平" if pz == "ping" else "仄", "yun": yun_char}
                if yun_char in CILIN:
                    entry["cilin"] = CILIN[yun_char]
                else:
                    entry["cilin_split"] = list(SPLIT[yun_char])
                yunmu.append(entry)
                for c in members:
                    for key in {c, s(c)}:
                        if idx not in chars[key]:
                            chars[key].append(idx)
                        if yun_char in SPLIT:
                            cilin_chars[key].update(split_bu(yun_char, c))
    # 源数据把韵目代表字当标题漏掉了（先、筱），补回本韵
    for idx, y in enumerate(yunmu):
        if idx not in chars[y["yun"]]:
            chars[y["yun"]].append(idx)
    inferred = fill_from_cilin(yunmu, chars, cilin_chars)
    # 源数据未收的常见异体字，按正字归韵
    for variant, canon in VARIANTS.items():
        if variant not in chars and canon in chars:
            chars[variant] = list(chars[canon])
            if canon in cilin_chars:
                cilin_chars[variant] = set(cilin_chars[canon])
    assert len(yunmu) == 106, len(yunmu)
    assert len({y["yun"] for y in yunmu}) == 106, "韵目代表字应唯一"
    out = {
        "_source": "平水韵 via rbnyng/pingshui_rhyme (MIT), simplified keys added via OpenCC; "
                   "chars missing there filled from charlesix59/chinese_word_rhyme 词林正韵 (MIT), 韵目 inferred",
        "yunmu": yunmu,
        "chars": {k: v for k, v in sorted(chars.items())},
        "cilin_split_chars": {k: sorted(v) for k, v in sorted(cilin_chars.items())},
        "inferred": "".join(sorted(inferred)),
    }
    dump(out, "rhyme/pingshui.json")
    return chars


def build_xinyun(extra_chars):
    table = {}
    cands = set(extra_chars)
    cands.update(chr(cp) for cp in range(0x4E00, 0x9FA6))
    for ch in sorted(cands):
        vals = []
        for ini, fin, tone in readings(ch):
            bu = xinyun_bu(ini, fin)
            if not bu or tone == 5:
                continue
            v = "%d%s" % (bu, "平" if tone in (1, 2) else "仄")
            if v not in vals:
                vals.append(v)
        if vals:
            table[ch] = ",".join(vals)
    dump({"_source": "中华新韵十四部, derived from pypinyin (MIT)", "names": XINYUN_NAMES,
          "chars": table}, "rhyme/xinyun.json")


# ---------------------------------------------------------------- corpus
def clean_author(a):
    return re.sub(r"^（.*?）", "", a or "").strip()


def strip_notes(text):
    """Drop 夹注 such as (青山外 一作：青山下)."""
    return re.sub(r"[（(][^（）()]*[）)]", "", text)


def build_corpus():
    poems = []
    for fname, book in (("tangshisanbaishou.json", "唐诗三百首"), ("qianjiashi.json", "千家诗")):
        d = json.load(open(os.path.join(DL, "cp", fname), encoding="utf-8"))
        for group in d["content"]:
            for p in group["content"]:
                # a few entries group several poems (其一/其二) under one chapter
                parts = [(p.get("subchapter"), p["paragraphs"])]
                if p["paragraphs"] and isinstance(p["paragraphs"][0], dict):
                    parts = [(p["chapter"] + "·" + sub["subchapter"], sub["paragraphs"]) for sub in p["paragraphs"]]
                for sub, paras in parts:
                    poems.append({"book": book, "type": s(group["type"]), "title": s(sub or p["chapter"]),
                                  "author": s(clean_author(p["author"])), "text": strip_notes(s("".join(paras)))})
    for p in json.load(open(os.path.join(DL, "cp", "songci300.json"), encoding="utf-8")):
        poems.append({"book": "宋词三百首", "type": "词", "title": p["rhythmic"], "author": p["author"],
                      "text": strip_notes("".join(p["paragraphs"]))})
    dump({"_source": "chinese-poetry (MIT), converted to simplified via OpenCC", "poems": poems},
         "corpus/poems.json", indent=None)
    return poems


TANG_POETS = set("""李白 杜甫 王维 白居易 李商隐 杜牧 孟浩然 王昌龄 刘禹锡 韩愈 柳宗元 岑参 高适 孟郊 贾岛 李贺
温庭筠 韦应物 王勃 骆宾王 卢照邻 杨炯 陈子昂 张九龄 王之涣 贺知章 崔颢 杜审言 宋之问 沈佺期 元稹 张籍 王建
刘长卿 钱起 韦庄 李益 卢纶 张继 张若虚 王翰 常建 储光羲 祖咏 李颀 崔护 许浑 罗隐 皮日休 陆龟蒙 杜荀鹤 顾况
戴叔伦 司空曙 李峤 上官仪 皎然 寒山 金昌绪 张祜 朱庆馀 李绅 聂夷中 黄巢 曹松 鱼玄机 薛涛 綦毋潜 刘方平 柳中庸
韩翃 皇甫冉 郎士元 严武 王湾 丘为 裴迪 李端 耿湋 卢仝 李涉 张旭 贾至 高蟾 秦韬玉 崔涂 郑谷 韩偓 王驾 陈陶""".split())
SONG_CI_POETS = set("""苏轼 辛弃疾 李清照 柳永 晏殊 晏几道 欧阳修 秦观 周邦彦 姜夔 陆游 范仲淹 贺铸 张先 黄庭坚
岳飞 陈亮 刘过 刘克庄 吴文英 张炎 王沂孙 史达祖 蒋捷 朱敦儒 张孝祥 叶梦得 李之仪 晁补之 王安石 毛滂 陈与义
朱淑真 张元干 文天祥 刘辰翁 周密 范成大 宋祁 林逋 潘阆 王观 聂胜琼 严蕊 谢逸 赵佶 李煜 冯延巳 舒亶 康与之
朱彝尊 陈克 万俟咏 吕本中 曾觌 韩元吉 陆淞 张抡 杨万里""".split())


def build_extended():
    """名家全集（全唐诗名家 + 宋词名家），gzip 文本，每行：作者\\t题目\\t正文。供撞句检查、原文核对。"""
    import gzip
    import sqlite3
    rows = []
    for f in sorted(glob.glob(os.path.join(DL, "cp", "tang", "poet.tang.*.json"))):
        for p in json.load(open(f, encoding="utf-8")):
            author = s(p.get("author", ""))
            if author in TANG_POETS:
                rows.append((author, s(p.get("title", "")), s("".join(p.get("paragraphs", [])))))
    con = sqlite3.connect(os.path.join(DL, "cp", "ci.db"))
    for rhythmic, author, content in con.execute("select rhythmic, author, content from ci"):
        if author in SONG_CI_POETS and content:
            rows.append((author, rhythmic, content.split(">>")[0].replace("\n", "").strip()))
    path = os.path.join(ASSETS, "corpus", "extended.txt.gz")
    with gzip.open(path, "wt", encoding="utf-8") as f:
        for r in rows:
            f.write("\t".join(x.replace("\t", " ") for x in r) + "\n")
    print("wrote corpus/extended.txt.gz", len(rows), "poems", os.path.getsize(path) // 1024, "KB")


def build_charfreq():
    cnt = collections.Counter()
    for f in glob.glob(os.path.join(DL, "cp", "tang", "poet.tang.*.json")):
        for p in json.load(open(f, encoding="utf-8")):
            for c in s("".join(p.get("paragraphs", []))):
                if "一" <= c <= "鿿":
                    cnt[c] += 1
    top = [c for c, _ in cnt.most_common(6000)]
    dump({"_source": "全唐诗 character frequency (chinese-poetry, MIT)", "rank": "".join(top)}, "charfreq.json")
    return cnt


def dump(obj, rel, indent=0):
    path = os.path.join(ASSETS, rel)
    with open(path, "w", encoding="utf-8") as f:
        if indent is None:
            json.dump(obj, f, ensure_ascii=False, separators=(",", ":"))
        else:
            json.dump(obj, f, ensure_ascii=False, separators=(",", ":"))
    print("wrote", rel, os.path.getsize(path) // 1024, "KB")


if __name__ == "__main__":
    ps_chars = build_pingshui()
    poems = build_corpus()
    corpus_chars = {c for p in poems for c in p["text"]}
    build_xinyun(set(ps_chars) | corpus_chars)
    build_charfreq()
    build_extended()
