#!/usr/bin/env python3
"""诗词格律工具（只用标准库）。

子命令：
  check     校验格律：近体（绝/律/排）、古风、对联、词牌；给出逐字平仄和问题清单
  lookup    查字：平水韵韵目、平仄、词林正韵部、新韵
  rhymes    列出某韵部的字（按常用度排序），用于选韵
  annotate  给任意文字逐字标平仄
  cipai     列出支持的词牌，或显示某个词牌的谱

示例：
  python3 meter.py check "白日依山尽，黄河入海流。欲穷千里目，更上一层楼。"
  python3 meter.py check --form 七律 --rhyme xinyun -f poem.txt
  python3 meter.py check --form 词:念奴娇 -f ci.txt --json
  python3 meter.py check --loose "……"          # 定场诗、打油等：押韵严格，平仄只作参考
  python3 meter.py lookup 看思过
  python3 meter.py rhymes 下平七阳 --common 60
  python3 meter.py cipai 浣溪沙

平仄标记：○ 平  ● 仄  ◐ 多音（可平可仄）  ？ 韵书未收
"""
import argparse
import collections
import json
import sys

import shici_data as D
from shici_data import PING, ZE

FORM_ALIASES = {
    "五绝": ("jinti", 5), "五言绝句": ("jinti", 5), "七绝": ("jinti", 7), "七言绝句": ("jinti", 7),
    "五律": ("jinti", 5), "五言律诗": ("jinti", 5), "七律": ("jinti", 7), "七言律诗": ("jinti", 7),
    "五排": ("jinti", 5), "五言排律": ("jinti", 5), "七排": ("jinti", 7), "七言排律": ("jinti", 7),
    "绝句": ("jinti", None), "律诗": ("jinti", None), "排律": ("jinti", None), "近体": ("jinti", None),
    "古风": ("guti", None), "古体": ("guti", None), "歌行": ("guti", None), "乐府": ("guti", None),
    "对联": ("duilian", None), "楹联": ("duilian", None),
}
BOOK_NAMES = {"pingshui": "平水韵", "xinyun": "中华新韵", "cilin": "词林正韵"}


# ======================================================================= report
class Report(object):
    def __init__(self, form, book):
        self.form, self.book = form, book
        self.rhyme = []
        self.lines = []      # {"text","marks","pattern"}
        self.issues = []     # {"level","kind","line","pos","char","msg"}
        self.notes = []

    def add(self, level, kind, msg, line=None, pos=None, char=None):
        self.issues.append({"level": level, "kind": kind, "msg": msg,
                            "line": line, "pos": pos, "char": char})

    @property
    def verdict(self):
        levels = {i["level"] for i in self.issues}
        if "error" in levels:
            return "不合律"
        if "warn" in levels:
            return "小疵"
        return "合律"

    def to_json(self):
        return {"form": self.form, "rhyme_book": BOOK_NAMES.get(self.book, self.book),
                "rhyme": self.rhyme, "verdict": self.verdict, "lines": self.lines,
                "errors": [i for i in self.issues if i["level"] == "error"],
                "warnings": [i for i in self.issues if i["level"] == "warn"],
                "info": [i for i in self.issues if i["level"] == "info"], "notes": self.notes}

    def render(self):
        out = ["体裁：%s    韵书：%s" % (self.form, BOOK_NAMES.get(self.book, self.book))]
        if self.rhyme:
            out.append("韵部：" + "；".join(self.rhyme))
        out.append("")
        width = max([len(l["text"]) for l in self.lines] + [1])
        for n, l in enumerate(self.lines, 1):
            pad = "　" * (width - len(l["text"]))
            row = "%2d  %s%s  %s%s" % (n, l["text"], pad, l["marks"], pad)
            if l.get("pattern"):
                row += "   谱 " + l["pattern"]
            out.append(row)
        out.append("")
        sym = {"error": "✗", "warn": "!", "info": "·"}
        for level, title in (("error", "错误"), ("warn", "小疵"), ("info", "提示")):
            items = [i for i in self.issues if i["level"] == level]
            if items:
                out.append("%s：" % title)
                for i in items:
                    out.append("  %s [%s] %s" % (sym[level], i["kind"], i["msg"]))
        for note in self.notes:
            out.append("※ " + note)
        counts = collections.Counter(i["level"] for i in self.issues)
        out.append("结论：%s（错误 %d，小疵 %d，提示 %d）" % (
            self.verdict, counts["error"], counts["warn"], counts["info"]))
        return "\n".join(out)


def pos_name(line, pos):
    return "第%d句第%d字" % (line + 1, pos + 1)


def reading_hint(ct, tone):
    """For a polyphonic char, name the reading the position requires."""
    if ct.source == "pingshui":
        ids = [y["id"] for y in D.ps_readings(ct.ch) if y["pz"] == tone]
        return "、".join(ids)
    return tone + "声"


def needs_hint(ct, tone):
    """多音字只在所需读音与今天的常读不同时才提示（如“谈笑间”须读仄），常读即合的就不打扰。"""
    if len(ct.tones) != 2:
        return False
    modern = D.xy_readings(ct.ch)
    return not modern or modern[0][1] != tone


def note_unknown(report, cts_lines):
    seen = set()
    for i, cts in enumerate(cts_lines):
        for j, ct in enumerate(cts):
            if ct.ch in seen:
                continue
            if ct.source == "xinyun-fallback":
                seen.add(ct.ch)
                report.add("warn", "未收字", "“%s”平水韵未收，暂按今音作%s声（%s）" % (
                    ct.ch, "".join(sorted(ct.tones)), pos_name(i, j)), i, j, ct.ch)
            elif ct.source == "unknown":
                seen.add(ct.ch)
                report.add("warn", "未收字", "“%s”韵书未收，无法判断平仄（%s）" % (ct.ch, pos_name(i, j)), i, j, ct.ch)


# ======================================================================= 近体诗
CORE = {"a": "中仄平平仄", "A": "中平中仄平", "b": "中平中仄仄", "B": "中仄中平平"}
PREFIX = {"a": "中平", "A": "中仄", "b": "中仄", "B": "中平"}
CORE2 = {"a": ZE, "A": PING, "b": PING, "B": ZE}       # tone of the core's 2nd char
PING_END = {"A", "B"}


def template(t, n):
    return CORE[t] if n == 5 else PREFIX[t] + CORE[t]


def evaluate(cts, t, rhymed):
    """Violations of one line against line-type t. Returns dict with cost and details."""
    n = len(cts)
    off = n - 5
    tpl = template(t, n)
    viol, soft, polys = [], [], []
    for j, req in enumerate(tpl):
        if req == "中":
            continue
        if j == n - 1 and rhymed:
            continue                      # 韵脚由押韵检查负责
        ct = cts[j]
        if t == "a" and j == off + 2:
            if not ct.can(PING):
                soft.append(j)            # 仄仄平平仄 第三字用仄：小拗
            continue
        if not ct.can(req):
            viol.append(j)
        elif needs_hint(ct, req):
            polys.append((j, req))
    res = {"type": t, "viol": viol, "soft": soft, "polys": polys, "special": []}
    # 特拗：平平平仄仄 → 平平仄平仄（七言 仄仄平平仄平仄）
    if t == "b" and (off + 3) in viol and cts[off + 2].can(ZE) and cts[off + 3].can(PING):
        viol.remove(off + 3)
        res["special"].append("te_ao")
    # 孤平：平平仄仄平 → 仄平仄仄平
    res["gu_ping"] = t == "A" and not cts[off].can(PING) and not cts[off + 2].can(PING)
    res["gu_ping_jiu"] = t == "A" and not cts[off].can(PING) and not cts[off + 2].can(ZE)
    # 三平尾
    res["san_ping"] = t in PING_END and all(not ct.can(ZE) for ct in cts[-3:])
    res["cost"] = len(viol) + 2 * res["gu_ping"] + 2 * res["san_ping"]
    return res


def jinti_rhyme(cts_lines, book, report, loose):
    """Find the 韵部 shared by the 对句 endings; flag 出韵. Returns (key, first_line_rhymes)."""
    even = [i for i in range(len(cts_lines)) if i % 2 == 1]
    keys = {i: D.rhyme_keys(cts_lines[i][-1].ch, book, PING) for i in even}
    first = D.rhyme_keys(cts_lines[0][-1].ch, book, PING)
    counter = collections.Counter(k for i in even for k in keys[i])
    if not counter:
        report.add("error", "出韵", "对句句尾都不是平声字，近体诗应押平声韵")
        return None, False
    best = max(counter, key=lambda k: (counter[k], k in first))
    report.rhyme.append(D.rhyme_key_name(best))
    for i in even:
        ch = cts_lines[i][-1].ch
        if best in keys[i]:
            if needs_hint(cts_lines[i][-1], PING):
                report.add("info", "多音字", "韵脚“%s”须读平声（%s），请确认字义" % (
                    ch, D.rhyme_key_name(best)), i, len(cts_lines[i]) - 1, ch)
            continue
        if cts_lines[i][-1].source != "pingshui" and book == "pingshui":
            report.add("warn", "未收字", "韵脚“%s”平水韵未收，无法确认是否押%s" % (ch, D.rhyme_key_name(best)),
                       i, len(cts_lines[i]) - 1, ch)
            continue
        if not keys[i]:
            report.add("error", "韵脚仄声", "%s“%s”是仄声，对句须押平声韵" % (
                pos_name(i, len(cts_lines[i]) - 1), ch), i, len(cts_lines[i]) - 1, ch)
            continue
        names = "、".join(D.rhyme_key_name(k) for k in keys[i])
        near = any(isinstance(k, str) and isinstance(best, str) and D.are_neighbors(k, best) for k in keys[i])
        level = "warn" if (loose and near) else "error"
        report.add(level, "出韵", "第%d句韵脚“%s”属%s，不在%s%s" % (
            i + 1, ch, names, D.rhyme_key_name(best), "（邻韵）" if near else ""), i, len(cts_lines[i]) - 1, ch)
    ch1 = cts_lines[0][-1].ch
    if best in first:
        return best, True
    if any(isinstance(k, str) and isinstance(best, str) and D.are_neighbors(k, best) for k in first) \
            and not cts_lines[0][-1].can(ZE):
        report.add("info", "首句邻韵", "首句韵脚“%s”属%s，借用邻韵（首句可借邻韵）" % (
            ch1, "、".join(first)), 0, len(cts_lines[0]) - 1, ch1)
        return best, True
    if not cts_lines[0][-1].can(ZE):
        report.add("error", "出韵", "首句以平声“%s”收尾却不押韵（首句平收应入韵）" % ch1,
                   0, len(cts_lines[0]) - 1, ch1)
        return best, True
    return best, False


def check_jinti(clauses, book, report, loose):
    n = len(clauses[0])
    cts_lines = [[D.char_tone(c, book) for c in cl] for cl in clauses]
    note_unknown(report, cts_lines)
    key, first_rhymes = jinti_rhyme(cts_lines, book, report, loose)

    # 给每句定句式：对句平收(A/B)，出句仄收(a/b)，首句看是否入韵。
    # 多音字让一句可归两种句式，所以整首一起求最优：句内不合 + 粘对不合（各计 1）总数最少。
    options = []
    for i, cts in enumerate(cts_lines):
        rhymed = i % 2 == 1 or (i == 0 and first_rhymes)
        options.append({t: evaluate(cts, t, rhymed) for t in (("A", "B") if rhymed else ("a", "b"))})

    def link_cost(prev, cur, i):
        same = CORE2[prev] == CORE2[cur]
        return 0 if (same if i % 2 == 0 else not same) else 1      # 对：相反；粘：相同

    best = {t: (e["cost"], [t]) for t, e in options[0].items()}
    for i in range(1, len(options)):
        best = {t: min(((c + link_cost(path[-1], t, i) + e["cost"], path + [t]) for c, path in best.values()),
                       key=lambda x: x[0])
                for t, e in options[i].items()}
    types = min(best.values(), key=lambda x: x[0])[1]
    evals = [options[i][t] for i, t in enumerate(types)]

    lvl = "info" if loose else "error"
    # 对句相救：出句 仄仄平平仄 第四字（七言第六字）拗，对句第三字（七言第五字）用平声
    for i in range(0, len(types) - 1, 2):
        e, f = evals[i], evals[i + 1]
        off = n - 5
        if types[i] == "a" and types[i + 1] == "A" and ((off + 3) in e["viol"] or e["soft"]):
            if cts_lines[i + 1][off + 2].can(PING):
                if (off + 3) in e["viol"]:
                    e["viol"].remove(off + 3)
                e["soft"] = []
                f["gu_ping_jiu"] = False
                report.add("info", "拗救", "第%d句第%d字拗，第%d句第%d字用平声相救，合律" % (
                    i + 1, off + 4, i + 2, off + 3), i)

    for i, (cts, e) in enumerate(zip(cts_lines, evals)):
        tpl = template(e["type"], n)
        report.lines.append({"text": "".join(ct.ch for ct in cts), "marks": "".join(ct.mark for ct in cts),
                             "pattern": tpl.replace("中", "⊙"), "type": e["type"]})
        nianzdui = False
        if i > 0:
            prev, cur = CORE2[types[i - 1]], CORE2[e["type"]]
            p = 1                                  # 粘对看每句第二字
            if i % 2 == 1 and prev == cur:
                report.add(lvl, "失对", "第%d句与第%d句失对：第二字“%s”“%s”平仄相同，出句与对句第二字应相反" % (
                    i, i + 1, cts_lines[i - 1][p].ch, cts[p].ch), i, p, cts[p].ch)
                nianzdui = True
            elif i % 2 == 0 and prev != cur:
                report.add(lvl, "失粘", "第%d句与第%d句失粘：第二字“%s”“%s”平仄应相同（上联对句与下联出句相粘）" % (
                    i, i + 1, cts_lines[i - 1][p].ch, cts[p].ch), i, p, cts[p].ch)
                nianzdui = True
        for j in e["viol"]:
            req = tpl[j]
            if j == n - 1 and e["type"] in ("a", "b") and i > 0:
                report.add(lvl, "平仄", "%s“%s”应为仄声（出句以仄声收尾）" % (pos_name(i, j), cts[j].ch), i, j, cts[j].ch)
            elif e["type"] == "a" and j == n - 2:
                report.add(lvl, "拗而未救", "%s“%s”应平而用仄（拗），对句第%d字也未用平声相救" % (
                    pos_name(i, j), cts[j].ch, n - 2), i, j, cts[j].ch)
            else:
                report.add(lvl, "平仄", "%s“%s”应为%s声" % (pos_name(i, j), cts[j].ch, req), i, j, cts[j].ch)
        for j in e["soft"]:
            report.add("info", "小拗", "%s“%s”用仄（仄仄仄平仄），属可救可不救的小拗" % (pos_name(i, j), cts[j].ch), i, j)
        if "te_ao" in e["special"]:
            if cts[n - 5].can(PING):
                report.add("info", "特拗", "第%d句用“平平仄平仄”特拗句式，合律" % (i + 1), i)
            else:
                report.add("warn", "特拗", "第%d句近“平平仄平仄”特拗，但%s“%s”宜用平声" % (
                    i + 1, pos_name(i, n - 5), cts[n - 5].ch), i, n - 5, cts[n - 5].ch)
        if e["gu_ping"]:
            report.add(lvl, "孤平", "第%d句犯孤平：“%s”除韵脚外只剩一个平声字" % (i + 1, "".join(ct.ch for ct in cts)), i)
        elif e["gu_ping_jiu"]:
            report.add("info", "拗救", "第%d句为“仄平平仄平”式，属孤平拗救，合律" % (i + 1), i)
        if e["san_ping"]:
            report.add(lvl, "三平尾", "第%d句末三字“%s”皆平，犯三平尾" % (i + 1, "".join(ct.ch for ct in cts[-3:])), i)
        for j, req in e["polys"]:
            ct = cts[j]
            report.add("info", "多音字", "%s“%s”此处须读%s（%s），请确认字义" % (
                pos_name(i, j), ct.ch, req, reading_hint(ct, req)), i, j, ct.ch)

    # 起式
    t0 = types[0]
    qi = template(t0, n)[1]
    if qi == "中":
        qi = CORE2[t0]
    report.notes.append("%s起，首句%s入韵" % (qi, "" if first_rhymes else "不"))
    check_repeats(clauses, report)
    if len(clauses) >= 8:
        report.notes.append("律诗中间两联（颔联、颈联）须对仗，脚本不检查对仗，请自查")


def check_repeats(clauses, report):
    text = "".join(clauses)
    cnt = collections.Counter(text)
    for ch, c in cnt.items():
        if c < 2:
            continue
        if ch * 2 in text and text.count(ch * 2) * 2 >= c:
            continue                          # 叠字
        report.add("warn", "重字", "“%s”出现 %d 次（近体诗一般避免重字，有意复沓除外）" % (ch, c), char=ch)


# ======================================================================= 古风
def check_guti(clauses, book, report):
    rb = "cilin" if book == "pingshui" else book    # 古风允许邻韵通押、上去通押：用词林正韵的部来近似
    cts_lines = [[D.char_tone(c, book) for c in cl] for cl in clauses]
    note_unknown(report, cts_lines)
    for cts in cts_lines:
        report.lines.append({"text": "".join(ct.ch for ct in cts), "marks": "".join(ct.mark for ct in cts)})
    ends = [i for i in range(len(clauses)) if i % 2 == 1]
    if len(clauses) % 2 == 1:
        ends.append(len(clauses) - 1)
    runs, cur, cur_keys = [], [], set()
    for i in ends:
        keys = D.rhyme_keys(clauses[i][-1], rb, None)
        inter = cur_keys & keys if cur else keys
        if cur and not inter:
            runs.append((cur, cur_keys))
            cur, cur_keys = [i], keys
        else:
            cur.append(i)
            cur_keys = inter
    if cur:
        runs.append((cur, cur_keys))
    for k, (idx, keys) in enumerate(runs):
        name = "、".join(sorted(D.rhyme_key_name(x) for x in keys)) or "未知"
        report.rhyme.append("第%s句：%s" % ("、".join(str(i + 1) for i in idx), name))
        if len(idx) == 1 and len(runs) > 1:
            report.add("warn", "疑似出韵", "第%d句韵脚“%s”与前后都不相押（古风可换韵，但一韵一般至少两押）" % (
                idx[0] + 1, clauses[idx[0]][-1]), idx[0])
    if len(runs) > 1:
        report.add("info", "换韵", "全诗换韵 %d 次" % (len(runs) - 1))
    report.notes.append("古风不拘平仄，只检查押韵（允许邻韵通押、上去通押）；平仄标记仅供参考")


# ======================================================================= 对联
def check_duilian(text, book, report):
    raw = [x for x in text.replace("上联", "\n").replace("下联", "\n").splitlines() if D.han_only(x)]
    if len(raw) >= 2:
        up, down = raw[0], raw[1]
    else:
        parts = D.split_clauses(text)
        if len(parts) < 2 or len(parts) % 2:
            report.add("error", "格式", "请用换行分开上联和下联")
            return
        h = len(parts) // 2
        up, down = "，".join(parts[:h]), "，".join(parts[h:])
    u_cl, d_cl = D.split_clauses(up), D.split_clauses(down)
    u, d = "".join(u_cl), "".join(d_cl)
    uc = [D.char_tone(c, book) for c in u]
    dc = [D.char_tone(c, book) for c in d]
    note_unknown(report, [uc, dc])
    report.lines.append({"text": u, "marks": "".join(c.mark for c in uc)})
    report.lines.append({"text": d, "marks": "".join(c.mark for c in dc)})
    if len(u) != len(d) or [len(x) for x in u_cl] != [len(x) for x in d_cl]:
        report.add("error", "字数", "上下联字数或分句不一致（上联 %s，下联 %s）" % (
            "/".join(str(len(x)) for x in u_cl), "/".join(str(len(x)) for x in d_cl)))
        return
    if not uc[-1].can(ZE):
        report.add("error", "仄起平收", "上联末字“%s”应为仄声" % u[-1], 0, len(u) - 1, u[-1])
    if not dc[-1].can(PING):
        report.add("error", "仄起平收", "下联末字“%s”应为平声" % d[-1], 1, len(d) - 1, d[-1])
    start = 0
    for cl in u_cl:
        L = len(cl)
        points = [start + j for j in range(1, L, 2)] + [start + L - 1]
        for p in sorted(set(points))[:-1] if start + L == len(u) else sorted(set(points)):
            a, b = uc[p], dc[p]
            if len(a.tones) == 1 and a.tones == b.tones:
                report.add("warn", "平仄相对", "第%d字“%s”“%s”同为%s声，节奏点上下联宜平仄相反" % (
                    p + 1, a.ch, b.ch, "".join(a.tones)), None, p)
        start += L
    for p in range(len(u)):
        if u[p] == d[p]:
            report.add("warn", "同位重字", "上下联第%d字都用“%s”" % (p + 1, u[p]), None, p, u[p])
    report.notes.append("对仗（词性、结构相对）脚本不检查，请自查；多分句长联的句脚平仄（马蹄韵）也请自查")


# ======================================================================= 词
def find_cipai(name):
    table = D.cipai_table()
    if name in table:
        return name, table[name]
    for k, v in table.items():
        if name in v.get("alias", []):
            return k, v
    return None, None


def parse_seg(seg):
    """'中仄平平仄a。' -> (pattern, rhyme_label, end_punct)"""
    punct = ""
    if seg and seg[-1] in "，。、；":
        seg, punct = seg[:-1], seg[-1]
    label = ""
    while seg and seg[-1] not in "平仄中":
        label = seg[-1] + label
        seg = seg[:-1]
    return seg, label, punct


def check_ci(text, name, report):
    pname, entry = find_cipai(name)
    if not entry:
        report.add("error", "词牌", "暂不支持词牌《%s》。可用 `meter.py cipai` 查看支持的词牌，其余请改用 annotate 自查" % name)
        return
    report.form = "词·" + pname
    chars = D.han_only(text)
    bodies = entry["forms"]
    fits = [b for b in bodies if sum(len(parse_seg(s)[0]) for part in b["parts"] for s in part) == len(chars)]
    if not fits:
        totals = "、".join("%s %d字" % (b["name"], sum(len(parse_seg(s)[0]) for part in b["parts"] for s in part))
                           for b in bodies)
        report.add("error", "字数", "《%s》应为 %s，实际 %d 字" % (pname, totals, len(chars)))
        cts = [D.char_tone(c, "cilin") for c in chars]
        report.lines.append({"text": chars, "marks": "".join(c.mark for c in cts)})
        return
    best = None
    for body in fits:
        sub = Report(report.form, "cilin")
        _check_ci_body(chars, body, sub)
        score = sum(1 for i in sub.issues if i["level"] == "error")
        if best is None or score < best[0]:
            best = (score, body, sub)
    _, body, sub = best
    if len(bodies) > 1:
        report.notes.append("按《%s》%s校验" % (pname, body["name"]))
    report.rhyme, report.lines, report.issues = sub.rhyme, sub.lines, sub.issues
    report.notes.extend(sub.notes)


def _check_ci_body(chars, body, report):
    pos = 0
    groups = collections.defaultdict(list)          # label -> [(line_idx, ch)]
    line_idx = 0
    for part_no, part in enumerate(body["parts"]):
        for seg in part:
            pat, label, punct = parse_seg(seg)
            piece = chars[pos:pos + len(pat)]
            cts = [D.char_tone(c, "pingshui") for c in piece]
            for j, req in enumerate(pat):
                if req == "中":
                    continue
                if label and j == len(pat) - 1:
                    continue                         # 韵脚由押韵检查负责（可押可不押的位置不定平仄）
                if not cts[j].can(req):
                    report.add("error", "平仄", "%s第%d字“%s”应为%s声" % (
                        "上片" if part_no == 0 else "下片", pos + j + 1, piece[j], req), line_idx, j, piece[j])
                elif needs_hint(cts[j], req):
                    report.add("info", "多音字", "“%s”此处须读%s（%s），请确认字义" % (
                        piece[j], req, reading_hint(cts[j], req)), line_idx, j, piece[j])
            optional = label.endswith("?")
            report.lines.append({"text": piece, "marks": "".join(c.mark for c in cts),
                                 "pattern": pat.replace("中", "⊙") + ("（可韵）" if optional else "（韵）" if label else "")})
            if label:
                groups[label.rstrip("?")].append((line_idx, piece[-1], optional))
            pos += len(pat)
            line_idx += 1
    note_unknown(report, [[D.char_tone(c, "pingshui") for c in chars]])
    for label, members in groups.items():
        tone = body["rhymes"][label]
        want = PING if tone == "平" else ZE
        keyset = [D.rhyme_keys(ch, "cilin", want) for _, ch, _ in members]
        counter = collections.Counter(k for (_, _, opt), ks in zip(members, keyset) if not opt for k in ks)
        if not counter:
            report.add("error", "出韵", "%s韵位的字都不是%s声" % (label, tone))
            continue
        bestk = max(counter, key=lambda k: counter[k])
        report.rhyme.append(D.rhyme_key_name(bestk))
        for (li, ch, opt), ks in zip(members, keyset):
            if bestk in ks:
                continue
            if opt:
                report.add("info", "可不押韵", "“%s”处可押可不押，此处未押" % ch, li, None, ch)
                continue
            # 宋人常按诗韵押词（如灰韵的“杯台回来”同押，而词林正韵分属三、五部）
            mates = {k for (_, c2, o2), ks2 in zip(members, keyset) if bestk in ks2 for k in D.rhyme_keys(c2, "pingshui", want)}
            shared = mates & D.rhyme_keys(ch, "pingshui", want)
            if shared:
                report.add("info", "诗韵通押", "韵脚“%s”与其他韵脚同属平水韵%s，宋词常见，可接受" % (
                    ch, "、".join(sorted(x for x in shared if isinstance(x, str)))), li, None, ch)
                continue
            if not ks:
                report.add("error", "韵脚平仄", "韵脚“%s”应为%s声" % (ch, tone), li, None, ch)
            elif bestk[1] == "入" and any(k[1] == "入" for k in ks):
                report.add("warn", "入声通押", "韵脚“%s”属%s，与第%d部邻部通押（宋词常见）" % (
                    ch, "、".join(D.rhyme_key_name(k) for k in ks), bestk[0]), li, None, ch)
            else:
                report.add("error", "出韵", "韵脚“%s”属%s，不在%s" % (
                    ch, "、".join(D.rhyme_key_name(k) for k in ks), D.rhyme_key_name(bestk)), li, None, ch)
    report.notes.append("词用词林正韵押韵；⊙ 表示可平可仄")


# ======================================================================= dispatch
def detect_form(clauses):
    lens = {len(c) for c in clauses}
    n = len(clauses)
    if len(lens) == 1 and lens <= {5, 7} and n % 2 == 0 and n >= 4:
        L = lens.pop()
        kind = {4: "绝句", 8: "律诗"}.get(n, "排律")
        return "jinti", ("五言" if L == 5 else "七言") + kind
    return "guti", "古风（句数或字数不整齐，按古体处理）"


def run_check(text, form=None, book="pingshui", loose=False):
    clauses = D.split_clauses(text)
    if form and (form.startswith("词:") or form.startswith("词：")):
        rep = Report("词", "cilin")
        check_ci(text, form[2:].strip("《》 "), rep)
        return rep
    if form in ("对联", "楹联"):
        rep = Report("对联", book)
        check_duilian(text, book, rep)
        return rep
    if not clauses:
        rep = Report("?", book)
        rep.add("error", "格式", "没有读到诗句")
        return rep
    kind, label = detect_form(clauses)
    if form:
        if form not in FORM_ALIASES:
            rep = Report(form, book)
            rep.add("error", "格式", "未知体裁“%s”，可选：%s、对联、词:词牌名" % (form, "、".join(FORM_ALIASES)))
            return rep
        want, L = FORM_ALIASES[form]
        if want == "jinti":
            if kind != "jinti" or (L and len(clauses[0]) != L):
                rep = Report(form, book)
                rep.add("error", "字数", "%s应为%s言、偶数句且每句字数相同；实际每句字数 %s，共 %d 句" % (
                    form, L and ("五" if L == 5 else "七") or "五/七",
                    "/".join(str(len(c)) for c in clauses), len(clauses)))
                return rep
            expect = {"绝": 4, "律": 8}
            for k, v in expect.items():
                if k in form and len(clauses) != v:
                    rep = Report(form, book)
                    rep.add("error", "句数", "%s应为 %d 句，实际 %d 句" % (form, v, len(clauses)))
                    return rep
        kind = want
        if want == "guti":
            label = "古风"
    rep = Report(label + ("（宽式：平仄仅供参考）" if loose and kind == "jinti" else ""), book)
    if kind == "jinti":
        check_jinti(clauses, book, rep, loose)
    else:
        check_guti(clauses, book, rep)
    return rep


# ======================================================================= other commands
def cmd_lookup(chars):
    for ch in D.han_only(chars):
        rs = D.ps_readings(ch)
        ps = "、".join("%s（%s）" % (y["id"], y["pz"]) for y in rs) or "未收"
        cl = "、".join(sorted("第%d部%s" % (b, c) for b, c in D.cilin_groups(ch))) or "—"
        xy = "、".join(D.xy_name(b) + t for b, t in D.xy_readings(ch)) or "—"
        mark = D.char_tone(ch).mark
        print("%s %s  平水韵：%s\n     词林正韵：%s    新韵：%s" % (ch, mark, ps, cl, xy))


def cmd_rhymes(name, book, common, show_all):
    rank = D.freq_rank()
    if book == "xinyun":
        names = D.xinyun()["names"]
        bu = int(name) if name.isdigit() else (names.index(name.replace("韵", "")) if name.replace("韵", "") in names else 0)
        if not bu:
            ch = D.han_only(name)[:1]
            rs = D.xy_readings(ch) if ch else []
            if not rs:
                print("找不到新韵韵部：%s（可用：%s）" % (name, "、".join(names[1:])))
                return
            bu = rs[0][0]
        for tone in (PING, ZE):
            # 只按首要读音归部，避免生僻又读把字带进别的韵
            mem = [c for c, v in D.xinyun()["chars"].items() if v.split(",")[0] == "%d%s" % (bu, tone)]
            mem.sort(key=lambda c: rank.get(c, 99999))
            if not show_all:
                mem = [c for c in mem if c in rank][:common]
            print("%s %s声（%d 字）：%s" % (D.xy_name(bu), tone, len(mem), "".join(mem)))
        return
    targets = []
    y = D.ps_yunmu(name)
    if y:
        targets = [y]
    else:
        ch = D.han_only(name)[:1]
        targets = D.ps_readings(ch) if ch else []
        if not targets:
            print("找不到韵目：%s（示例：下平七阳、七阳、阳，或直接给一个字）" % name)
            return
    for y in targets:
        mem = sorted(set(D.ps_members(y["id"])), key=lambda c: rank.get(c, 99999))
        simp = [c for c in mem if c in rank]              # 字频表是简体，顺带滤掉繁体重复
        shown = mem if show_all else simp[:common]
        width = "宽韵" if len(simp) > 150 else ("中韵" if len(simp) > 60 else "窄韵")
        print("%s（%s声，%s，常用字约 %d）：\n%s\n" % (y["id"], y["pz"], width, len(simp), "".join(shown)))


def cmd_annotate(text, book):
    for line in text.splitlines():
        if not D.han_only(line):
            continue
        out_t, out_m = [], []
        for ch in line:
            if D.HAN_RE.match(ch):
                out_t.append(ch)
                out_m.append(D.char_tone(ch, book).mark)
            else:
                out_t.append(ch)
                out_m.append(ch if ch in "，。？！；：、 " else " ")
        print("".join(out_t))
        print("".join(out_m))


def cmd_cipai(name):
    table = D.cipai_table()
    if not name:
        rows = collections.defaultdict(list)
        for k, v in table.items():
            rows[v.get("length", "")].append("%s（%s）" % (k, v["forms"][0]["name"] if len(v["forms"]) > 1 else
                                                         "%d字" % sum(len(parse_seg(s)[0]) for p in v["forms"][0]["parts"] for s in p)))
        for k in ("小令", "中调", "长调"):
            if rows.get(k):
                print("%s：%s" % (k, "、".join(rows[k])))
        return
    pname, entry = find_cipai(name)
    if not entry:
        print("暂不支持《%s》" % name)
        return
    print("《%s》%s" % (pname, ("又名" + "、".join(entry["alias"])) if entry.get("alias") else ""))
    for key in ("desc", "mood", "example"):
        if entry.get(key):
            print({"desc": "格式", "mood": "声情", "example": "范例"}[key] + "：" + entry[key])
    for body in entry["forms"]:
        total = sum(len(parse_seg(s)[0]) for p in body["parts"] for s in p)
        rh = "，".join("%s=%s韵" % (k, v) for k, v in body["rhymes"].items())
        print("\n【%s】%d字  （韵组：%s）" % (body["name"], total, rh))
        for i, part in enumerate(body["parts"]):
            segs = []
            for s in part:
                pat, label, punct = parse_seg(s)
                pat = pat.replace("中", "⊙")
                mark = ("(%s韵，可不押)" % label[:-1]) if label.endswith("?") else ("(%s韵)" % label if label else "")
                segs.append(pat + mark + (punct or ("。" if label else "，")))
            title = ("上片" if i == 0 else "下片") if len(body["parts"]) > 1 else "全词"
            if len(body["parts"]) > 2:
                title = "第%d段" % (i + 1)
            print("%s：%s" % (title, "".join(segs)))
    print("\n⊙ 可平可仄；(a韵) 为韵位，同字母同押一韵")


def read_text(args):
    if args.file:
        with open(args.file, encoding="utf-8") as f:
            return f.read()
    if args.text and args.text != ["-"]:
        return "\n".join(args.text)
    return sys.stdin.read()


def main(argv=None):
    ap = argparse.ArgumentParser(description="诗词格律工具", formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog=__doc__)
    sub = ap.add_subparsers(dest="cmd")
    c = sub.add_parser("check", help="校验格律")
    c.add_argument("text", nargs="*")
    c.add_argument("-f", "--file")
    c.add_argument("--form", help="五绝/七绝/五律/七律/五排/七排/古风/对联/词:词牌名；不填则自动判断")
    c.add_argument("--rhyme", default="pingshui", choices=["pingshui", "xinyun"])
    c.add_argument("--loose", action="store_true", help="宽式：押韵严格，平仄只作提示（定场诗、打油等）")
    c.add_argument("--json", action="store_true")
    l = sub.add_parser("lookup", help="查字")
    l.add_argument("chars")
    r = sub.add_parser("rhymes", help="列韵部字")
    r.add_argument("name")
    r.add_argument("--rhyme", default="pingshui", choices=["pingshui", "xinyun"])
    r.add_argument("--common", type=int, default=80)
    r.add_argument("--all", action="store_true")
    a = sub.add_parser("annotate", help="逐字标平仄")
    a.add_argument("text", nargs="*")
    a.add_argument("-f", "--file")
    a.add_argument("--rhyme", default="pingshui", choices=["pingshui", "xinyun"])
    p = sub.add_parser("cipai", help="词牌谱")
    p.add_argument("name", nargs="?")
    args = ap.parse_args(argv)

    if args.cmd == "check":
        rep = run_check(read_text(args), args.form, args.rhyme, args.loose)
        if args.json:
            print(json.dumps(rep.to_json(), ensure_ascii=False, indent=1))
        else:
            print(rep.render())
    elif args.cmd == "lookup":
        cmd_lookup(args.chars)
    elif args.cmd == "rhymes":
        cmd_rhymes(args.name, args.rhyme, args.common, args.all)
    elif args.cmd == "annotate":
        cmd_annotate(read_text(args), args.rhyme)
    elif args.cmd == "cipai":
        cmd_cipai(args.name)
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
