# shici-studio · 诗词工坊

[![test](https://github.com/hlulu123/shici-studio/actions/workflows/test.yml/badge.svg)](https://github.com/hlulu123/shici-studio/actions/workflows/test.yml)
![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)
![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue.svg)
![Claude Agent Skill](https://img.shields.io/badge/Claude-Agent%20Skill-d97757.svg)

An [Agent Skill](https://github.com/anthropics/skills) that teaches Claude to write classical Chinese poetry (诗, 词, couplets and more): decide what the poem is really about first, then craft it, then verify tones and rhymes character by character with a script.

[中文](README.md)

## Why

Language models writing classical Chinese verse tend to fail in two ways:

1. **Tonal rules by "feel".** Characters like 白, 国, 竹, 一, 十 are level tones in modern Mandarin but were entering tones (oblique) in the Pingshui rhyme system. Characters like 看, 思, 过 change tone with meaning. Guessing gets these wrong.
2. **Ornament without a point.** Every line sounds poetic, but the poem as a whole says nothing.

This skill makes Claude settle the poem's intent before writing, and hands all tone and rhyme checking to a deterministic script.

## Features

- **Write**: 12 poem types (celebration, longing, melancholy, everyday life, landscape, object, aspiration, history, farewell, 定场诗 introductions, congratulations, humor), all major forms (jueju, lüshi, pailü, gufeng/gexing, 40 common cipai, couplets, acrostics, pianwen, modern verse) and 12 style guides (Li Bai, Wang Bo's 《滕王阁序》, Su Shi / Xin Qiji, Li Qingzhao, Du Fu, Wang Wei, and more).
- **Revise**: minimal-change meter fixes, word polishing, or restyling, with a before → after → why table.
- **Check**: explains each problem in plain language, proposes the smallest fix, and re-runs the checker to prove it passes. Knows that famous "irregular" poems such as 《静夜思》 and 《黄鹤楼》 belong to older or variant forms.
- **Allusions**: a built-in allusion library; sources must be verified, preferably against Wikisource or ctext.org.
- **Plagiarism check**: flags any 5 consecutive characters shared with ~33,000 Tang and Song poems.

See [`examples/`](examples/) for real outputs (in Chinese).

## Install

**Claude.ai / Claude desktop app**: download `shici-studio.skill` from [Releases](https://github.com/hlulu123/shici-studio/releases/latest), make sure code execution is enabled under Settings → Capabilities, and upload it under Skills. If only `.zip` is accepted, rename the file; the contents are the same.

**Claude Code**:

```bash
git clone https://github.com/hlulu123/shici-studio.git
mkdir -p ~/.claude/skills
cp -r shici-studio/shici-studio ~/.claude/skills/
```

Requires Python 3.9+, standard library only.

## The meter checker

`shici-studio/scripts/meter.py` also works as a standalone CLI. It checks against the Pingshui rhyme (平水韵), the modern Zhonghua Xinyun (中华新韵) or the Cilin Zhengyun (词林正韵), and reports rhyme violations, broken 粘/对 sequencing, 孤平, 三平尾, tone mismatches, unremedied 拗, and cipai pattern errors.

```bash
python3 scripts/meter.py check "白日依山尽，黄河入海流。欲穷千里目，更上一层楼。"
python3 scripts/meter.py check --form 词:浣溪沙 "……"
python3 scripts/meter.py lookup 看思白
python3 scripts/meter.py cipai 水调歌头
```

Backtested on 唐诗三百首 and 千家诗, it finds no errors in 94% of 七绝 and 五律 and 85% of 七律. The rest are mostly legitimate variant forms in the anthologies. It does not check parallelism (对仗); the model handles that.

## Data

Rhyme tables, cipai statistics and the poem corpus are derived from [rbnyng/pingshui_rhyme](https://github.com/rbnyng/pingshui_rhyme), [charlesix59/chinese_word_rhyme](https://github.com/charlesix59/chinese_word_rhyme), [OpenCC](https://github.com/BYVoid/OpenCC), [pypinyin](https://github.com/mozillazg/python-pinyin) and [chinese-poetry](https://github.com/chinese-poetry/chinese-poetry) under MIT / Apache-2.0. See [`shici-studio/assets/LICENSES.md`](shici-studio/assets/LICENSES.md).

## License

[MIT](LICENSE)
