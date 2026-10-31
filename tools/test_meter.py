"""Regression tests for shici-studio/scripts/meter.py.

    python3 tools/test_meter.py            # constructed cases + corpus pass rates
    python3 tools/test_meter.py -v         # also list corpus poems that fail
"""
import collections
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "shici-studio", "scripts"))

import meter  # noqa: E402
import shici_data as D  # noqa: E402

VERBOSE = "-v" in sys.argv

# (name, text, form, expect_kinds_present, expect_no_errors)
CASES = [
    ("合律·登鹳雀楼", "白日依山尽，黄河入海流。欲穷千里目，更上一层楼。", None, [], True),
    ("合律·登高", "风急天高猿啸哀，渚清沙白鸟飞回。无边落木萧萧下，不尽长江滚滚来。"
                 "万里悲秋常作客，百年多病独登台。艰难苦恨繁霜鬓，潦倒新停浊酒杯。", None, [], True),
    ("特拗·宿建德江", "移舟泊烟渚，日暮客愁新。野旷天低树，江清月近人。", None, ["特拗"], True),
    ("对句救·赋得古原草", "离离原上草，一岁一枯荣。野火烧不尽，春风吹又生。", None, ["拗救"], True),
    ("失粘", "白日依山尽，黄河入海流。远树连天碧，孤舟向晚收。", None, ["失粘"], False),
    ("失对", "白日依山尽，落日照江流。欲穷千里目，更上一层楼。", None, ["失对"], False),
    ("孤平", "白日依山尽，大河入海流。欲穷千里目，更上一层楼。", None, ["孤平"], False),
    ("三平尾", "白日依山尽，黄河入海流。欲穷千里目，更上高楼头。", None, ["三平尾"], False),
    ("出韵", "白日依山尽，黄河入海流。欲穷千里目，更上一层台。", None, ["出韵"], False),
    ("平仄", "白日依山尽，黄河入海流。欲穷千里目，更上一级楼。", None, ["平仄"], False),
    ("首句借邻韵", "清明时节雨纷纷，路上行人欲断魂。借问酒家何处有，牧童遥指杏花村。", None, [], True),
    ("句数", "白日依山尽，黄河入海流。欲穷千里目。", "五绝", ["字数"], False),
    ("宽式只看押韵", "白日依山尽，大河入海流。欲穷千里目，更上高楼头。", None, ["孤平"], True),
    ("对联", "风声雨声读书声声声入耳\n家事国事天下事事事关心", "对联", [], True),
    ("对联收尾", "春风送暖入屠苏\n爆竹一声除旧岁", "对联", ["仄起平收"], False),
    # 新韵里入声字“一”归平声，“一层楼”成三平尾；平水韵下则合律
    ("新韵", "白日依山尽，黄河入海流。欲穷千里目，更上一层楼。", None, ["三平尾"], False),
]
LOOSE = {"宽式只看押韵"}
XINYUN = {"新韵"}


def run_cases():
    fails = 0
    for name, text, form, kinds, no_err in CASES:
        rep = meter.run_check(text, form, "xinyun" if name in XINYUN else "pingshui", name in LOOSE)
        got = {i["kind"] for i in rep.issues}
        errs = [i for i in rep.issues if i["level"] == "error"]
        ok = all(k in got for k in kinds) and (not errs if no_err else bool(errs))
        fails += not ok
        print("%s %-14s %s  %s" % ("✓" if ok else "✗", name, rep.verdict, "；".join(sorted(got)) or "—"))
        if not ok:
            print(rep.render())
    return fails


def corpus_rates():
    forms = {"五言绝句": "五绝", "七言绝句": "七绝", "五言律诗": "五律", "七言律诗": "七律"}
    stats = collections.defaultdict(collections.Counter)
    kinds = collections.defaultdict(collections.Counter)
    for p in D.corpus():
        if p["type"] not in forms:
            continue
        rep = meter.run_check(p["text"], forms[p["type"]])
        stats[p["type"]][rep.verdict] += 1
        for i in rep.issues:
            if i["level"] == "error":
                kinds[p["type"]][i["kind"]] += 1
        if VERBOSE and rep.verdict == "不合律":
            errs = "；".join(i["msg"] for i in rep.issues if i["level"] == "error")
            print("  [%s] %s《%s》 %s" % (p["type"], p["author"], p["title"], errs))
    print("\n选集近体诗校验（唐诗三百首＋千家诗；含古绝、拗律，不可能 100%）：")
    for t in forms:
        c = stats[t]
        total = sum(c.values())
        ok = c["合律"] + c["小疵"]
        print("  %s  %3d 首  无错误 %3d（%.0f%%）  错误类型 %s" % (
            t, total, ok, 100.0 * ok / max(total, 1), dict(kinds[t].most_common(6))))


def ci_rates():
    table = D.cipai_table()
    ci = [p for p in D.corpus() if p["type"] == "词"]
    print("\n宋词三百首按词牌校验：")
    for name in table:
        poems = [p for p in ci if p["title"] == name or p["title"] in table[name].get("alias", [])]
        if not poems:
            continue
        c = collections.Counter()
        for p in poems:
            rep = meter.run_check(p["text"], "词:" + name)
            c[rep.verdict] += 1
            if VERBOSE and rep.verdict == "不合律":
                errs = "；".join(i["msg"] for i in rep.issues if i["level"] == "error")
                print("  [%s] %s：%s" % (name, p["author"], errs[:200]))
        print("  %-6s %2d 首  合律 %d  小疵 %d  不合律 %d" % (name, len(poems), c["合律"], c["小疵"], c["不合律"]))


if __name__ == "__main__":
    f = run_cases()
    corpus_rates()
    ci_rates()
    print("\n构造用例失败：%d" % f)
    sys.exit(1 if f else 0)
