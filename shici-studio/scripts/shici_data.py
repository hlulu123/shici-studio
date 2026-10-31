"""Shared data access for the shici-studio scripts (standard library only).

Rhyme books:
  pingshui  平水韵 (106 韵)      — default for 近体诗、古风、对联
  xinyun    中华新韵 (14 部)     — modern pronunciation; 入声已派入平上去
  cilin     词林正韵 (19 部)     — for 词; derived from 平水韵
"""
import functools
import json
import os
import re

ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets")

PING, ZE = "平", "仄"
PUNCT_RE = re.compile(r"[，。？！；：、,.?!;:\s　—…·“”‘’\"'（）()《》〈〉【】\[\]/|]+")
HAN_RE = re.compile("[\u3400-\u9fff\uf900-\ufaff\U00020000-\U0003134f]")   # 含扩展 B 以后的生僻字


@functools.lru_cache(maxsize=None)
def _load(rel):
    with open(os.path.join(ASSETS, rel), encoding="utf-8") as f:
        return json.load(f)


def pingshui():
    return _load("rhyme/pingshui.json")


def xinyun():
    return _load("rhyme/xinyun.json")


def cipai_table():
    return _load("cipai.json")


def corpus():
    return _load("corpus/poems.json")["poems"]


@functools.lru_cache(maxsize=None)
def freq_rank():
    rank = _load("charfreq.json")["rank"]
    return {c: i for i, c in enumerate(rank)}


# ------------------------------------------------------------------ text helpers
def split_clauses(text):
    """Split text into clauses at punctuation / line breaks, keeping only Han characters."""
    parts = PUNCT_RE.split(text)
    out = []
    for p in parts:
        han = "".join(HAN_RE.findall(p))
        if han:
            out.append(han)
    return out


def han_only(text):
    return "".join(HAN_RE.findall(text))


# ------------------------------------------------------------------ 平水韵
def ps_readings(ch):
    """List of 韵目 dicts (id, sheng, tone, pz, yun, cilin…) the char belongs to."""
    d = pingshui()
    return [d["yunmu"][i] for i in d["chars"].get(ch, [])]


def ps_yunmu(name):
    """Resolve a 韵目 given as 下平七阳 / 七阳 / 阳 / 下平声七阳."""
    name = name.replace("声", "").replace("聲", "").strip()
    for y in pingshui()["yunmu"]:
        if name in (y["id"], y["id"].replace("声", "")) or name == y["id"][2:] or name == y["yun"]:
            return y
    for y in pingshui()["yunmu"]:
        if y["id"].replace("声", "").endswith(name):
            return y
    return None


def ps_members(yunmu_id):
    d = pingshui()
    idx = next(i for i, y in enumerate(d["yunmu"]) if y["id"] == yunmu_id)
    return [c for c, ids in d["chars"].items() if idx in ids]


# 平声韵的邻韵（首句借邻韵、古风通押时参考）
NEIGHBORS = [
    {"上平一东", "上平二冬"}, {"上平三江", "下平七阳"}, {"上平四支", "上平五微", "上平八齐"},
    {"上平六鱼", "上平七虞"}, {"上平九佳", "上平十灰"}, {"上平十一真", "上平十二文", "上平十三元"},
    {"上平十三元", "上平十四寒", "上平十五删", "下平一先"}, {"下平二萧", "下平三肴", "下平四豪"},
    {"下平五歌"}, {"下平六麻"}, {"下平八庚", "下平九青", "下平十蒸"}, {"下平十一尤"},
    {"下平十二侵"}, {"下平十三覃", "下平十四盐", "下平十五咸"},
]


def are_neighbors(a, b):
    return any(a in g and b in g for g in NEIGHBORS)


# ------------------------------------------------------------------ 中华新韵
def xy_readings(ch):
    """[(部号, 平/仄)], primary reading first."""
    raw = xinyun()["chars"].get(ch)
    if not raw:
        return []
    out = []
    for v in raw.split(","):
        out.append((int(v[:-1]), v[-1]))
    return out


def xy_name(bu):
    return "%s韵（%d）" % (xinyun()["names"][bu], bu)


# ------------------------------------------------------------------ 词林正韵
def cilin_groups(ch):
    """Set of (部, 声类) where 声类 is 平 / 仄(上去) / 入."""
    d = pingshui()
    out = set()
    for y in ps_readings(ch):
        if "cilin" in y:
            bus = [y["cilin"]]
        else:
            bus = d["cilin_split_chars"].get(ch, y["cilin_split"])
        cls = "平" if y["pz"] == PING else ("入" if y["tone"] == "入" else "仄")
        for b in bus:
            out.add((b, cls))
    return out


# ------------------------------------------------------------------ unified tone lookup
class CharTone(object):
    """Possible tones of one character under a rhyme book."""

    __slots__ = ("ch", "tones", "source", "detail")

    def __init__(self, ch, tones, source, detail):
        self.ch, self.tones, self.source, self.detail = ch, tones, source, detail

    @property
    def mark(self):
        if not self.tones:
            return "？"
        if len(self.tones) == 2:
            return "◐"
        return "○" if PING in self.tones else "●"

    def can(self, tone):
        return not self.tones or tone in self.tones


# 韵书里另有极罕用读音、诗中几乎只取一读的字：按常读判定，避免把明显的拗当成合律
PS_COMMON_READING = {"不": ZE}


def char_tone(ch, book="pingshui"):
    if book == "xinyun":
        rs = xy_readings(ch)
        if rs:
            # 新韵按首要读音判平仄；又读只在报告里提示
            return CharTone(ch, {rs[0][1]}, "xinyun", [xy_name(b) + t for b, t in rs])
        return CharTone(ch, set(), "unknown", [])
    rs = ps_readings(ch)
    if ch in PS_COMMON_READING:
        rs = [y for y in rs if y["pz"] == PS_COMMON_READING[ch]] or rs
    if rs:
        return CharTone(ch, {y["pz"] for y in rs}, "pingshui", [y["id"] for y in rs])
    xs = xy_readings(ch)
    if xs:
        # 平水韵未收的字，退回今音并在报告里提示
        return CharTone(ch, {xs[0][1]}, "xinyun-fallback", [xy_name(b) + t for b, t in xs])
    return CharTone(ch, set(), "unknown", [])


def rhyme_keys(ch, book="pingshui", tone=PING):
    """Rhyme-group keys a character can occupy, restricted to the given tone class."""
    if book == "xinyun":
        return {("xy", b) for b, t in xy_readings(ch) if tone is None or t == tone}
    if book == "cilin":
        return {g for g in cilin_groups(ch)
                if tone is None or (tone == PING and g[1] == "平") or (tone == ZE and g[1] != "平")}
    keys = {y["id"] for y in ps_readings(ch) if tone is None or y["pz"] == tone}
    if not keys and not ps_readings(ch):
        # 平水韵未收的字：用新韵兜底，避免一律判出韵
        keys = {("xy", b) for b, t in xy_readings(ch) if tone is None or t == tone}
    return keys


def rhyme_key_name(key):
    if isinstance(key, tuple):
        if key[0] == "xy":
            return "新韵" + xy_name(key[1])
        return "词林正韵第%d部（%s声）" % (key[0], {"平": "平", "仄": "上去", "入": "入"}[key[1]])
    return key
