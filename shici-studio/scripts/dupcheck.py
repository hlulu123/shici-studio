#!/usr/bin/env python3
"""撞句检查与原文查找。

诗库：唐诗三百首、千家诗、宋词三百首，外加名家全集（全唐诗约百位名家、宋词约六十位名家，共三万余首）。

用法：
  python3 dupcheck.py "诗文……"            # 撞句检查：与诗库连续 N 字（默认 5）相同即报出
  python3 dupcheck.py -f poem.txt --min 4
  python3 dupcheck.py --find 大鹏一日同风起    # 按诗句片段查原文
  python3 dupcheck.py --title 静夜思          # 按题目查原文（只查三本选集）

诗库查不到不代表原创，也不代表原句不存在；引用古人诗句时，查不到就联网核对。
"""
import argparse
import functools
import gzip
import json
import os
import sys

import shici_data as D


@functools.lru_cache(maxsize=None)
def extended_text():
    path = os.path.join(D.ASSETS, "corpus", "extended.txt.gz")
    if not os.path.exists(path):
        return ""
    with gzip.open(path, "rt", encoding="utf-8") as f:
        return f.read()


@functools.lru_cache(maxsize=None)
def anthology_text():
    return "\n".join("%s\t%s\t%s" % (p["author"], p["title"], p["text"]) for p in D.corpus()) + "\n"


def search(fragment, limit=5):
    """[(author, title, text)] of poems containing fragment, anthologies first."""
    out, seen = [], set()
    for text in (anthology_text(), extended_text()):
        start = 0
        while len(out) < limit:
            k = text.find(fragment, start)
            if k < 0:
                break
            ls = text.rfind("\n", 0, k) + 1
            le = text.find("\n", k)
            author, title, body = text[ls:le].split("\t", 2)
            if (author, body[:20]) not in seen:
                seen.add((author, body[:20]))
                out.append((author, title, body))
            start = le
    return out


def found(fragment):
    return fragment in anthology_text() or fragment in extended_text()


def check(text, n):
    hits = []
    for li, cl in enumerate(D.split_clauses(text)):
        i = 0
        while i <= len(cl) - n:
            if found(cl[i:i + n]):
                j = i + n
                while j < len(cl) and found(cl[i:j + 1]):
                    j += 1
                frag = cl[i:j]
                hits.append({"line": li + 1, "fragment": frag,
                             "sources": ["%s《%s》" % (a, t) for a, t, _ in search(frag, 3)]})
                i = j
            else:
                i += 1
    return hits


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("text", nargs="*")
    ap.add_argument("-f", "--file")
    ap.add_argument("--min", type=int, default=5, help="连续相同多少字算撞句（默认 5）")
    ap.add_argument("--find", help="按诗句片段查原文")
    ap.add_argument("--title", help="按题目查原文")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if args.find or args.title:
        if args.title:
            res = [(p["author"], p["title"], p["text"]) for p in D.corpus() if args.title in p["title"]]
        else:
            res = search(D.han_only(args.find), 10)
        if args.json:
            print(json.dumps([{"author": a, "title": t, "text": x} for a, t, x in res], ensure_ascii=False, indent=1))
            return
        if not res:
            print("本地诗库未找到，请联网核对原文（优先维基文库、中国哲学书电子化计划）。")
        for a, t, x in res:
            print("%s《%s》\n%s\n" % (a, t, x))
        return

    text = open(args.file, encoding="utf-8").read() if args.file else (" ".join(args.text) or sys.stdin.read())
    hits = check(text, args.min)
    if args.json:
        print(json.dumps(hits, ensure_ascii=False, indent=1))
        return
    if not hits:
        print("未发现与诗库连续 %d 字相同的句子。" % args.min)
        return
    for h in hits:
        print("第%d句 “%s” 见于 %s" % (h["line"], h["fragment"], "、".join(h["sources"])))
    print("\n共 %d 处。整句照搬应改写；有意化用的要在注释里说明出处。" % len(hits))


if __name__ == "__main__":
    main()
