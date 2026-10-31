# 诗词工坊 · shici-studio

[![test](https://github.com/hlulu123/shici-studio/actions/workflows/test.yml/badge.svg)](https://github.com/hlulu123/shici-studio/actions/workflows/test.yml)
![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)
![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue.svg)
![Claude Agent Skill](https://img.shields.io/badge/Claude-Agent%20Skill-d97757.svg)

一个让 Claude 写中文旧体诗词的 [Agent Skill](https://github.com/anthropics/skills)：先想清楚写什么，再立意、用典、谋篇、炼字，最后用脚本逐字校验平仄和押韵。

[English](README.en.md)

> 大模型写诗最常见的两个毛病：一是格律靠“语感”，普通话读平声的“白、国、竹、一、十”在平水韵里其实是入声；二是辞藻堆砌，每句都像诗，合起来不知道在说什么。这个技能针对的就是这两点：**立意先行，格律交给脚本。**

## 效果

> **用户**：今晚加班到十一点，下楼在路边小摊吃了碗馄饨，老板娘多给我加了个蛋，突然有点想哭。帮我用《浣溪沙》写一首词记录一下。

**《浣溪沙·夜半馄饨》**（词林正韵 第七部 平声）

> 小序：伏案至夜十一时，下楼就街边小摊食馄饨。店家娘子为添一蛋，忽有泪意。

案牍劳形到夜阑，长街人散一灯寒。馄饨浮碗白团团。<br>
分外犹添鸡子卧，无端忽觉泪光悬。低头只道是汤烟。

**格律**：合律（脚本校验通过）。上片押寒韵（阑、寒、团），下片押先韵（悬、烟），两韵在词林正韵同属第七部，词里可以通押。

完整输出（含注释、创作说明）和更多示例见 [`examples/`](examples/)：

| 示例 | 类型 · 体裁 |
|---|---|
| [夜半馄饨](examples/01-jishi-huanxisha.md) | 记事 · 浣溪沙 |
| [得研究生录取通知书喜赋](examples/02-yiqi-qilv.md) | 意气风发 · 七律，三处典故注明出处 |
| [贺老周四十初度](examples/03-dingchang.md) | 定场诗 · 七律，寿宴开场用 |
| [扶摇歌](examples/04-taibai-gexing.md) | 太白体 · 杂言歌行，六段五换韵 |

以上均为 Claude 加载本技能后的实际输出，从评测记录原样摘录。

## 能做什么

- **写诗填词**：先判断你想写哪一类诗，再选体裁、风格、韵部。
  - 12 种类型：意气风发、柔情、愁怀、记事、写景、咏物、言志、怀古、送别、定场诗、祝颂、谐趣
  - 体裁：五七言绝句、律诗、排律，古风、歌行，40 个常用词牌，对联，藏头和嵌字诗，骈文和短赋，现代诗
  - 12 种风格：太白体（大鹏、游仙）、骈俪（《滕王阁序》式）、豪放、婉约、沉郁、禅意、田园、边塞、绮丽、闲适、通俗谐趣、现代诗
- **改诗**：只修格律（改动最小）、炼字、换风格或换体裁，给出“原句 → 改句 → 理由”的对照。
- **校律**：指出哪一句、哪个字、什么问题，给出最小改法，并重跑脚本证明改后通过。对《静夜思》（古绝）、《黄鹤楼》（拗律）这类名篇的“不合律”，会说明它属于哪种变格，不会当成写错。
- **用典**：自带常用典故库；典故和引用的名句要核对原文，能联网时优先查维基文库、ctext.org。
- **撞句检查**：与三万多首唐诗宋词比对，连续 5 字相同就提示，避免无意中照搬名句。

## 安装

### Claude.ai / Claude 桌面版

1. 到 [Releases](https://github.com/hlulu123/shici-studio/releases/latest) 下载 `shici-studio.skill`。
2. 打开 **设置 → 功能（Capabilities）**，确认已开启代码执行，然后在 **Skills** 里上传这个文件。如果界面只接受 `.zip`，把扩展名改成 `.zip` 再上传，内容是一样的。

### Claude Code

把 `shici-studio/` 这个目录放进 skills 目录即可：

```bash
git clone https://github.com/hlulu123/shici-studio.git
mkdir -p ~/.claude/skills
cp -r shici-studio/shici-studio ~/.claude/skills/
```

只想在某个项目里用，就放到那个项目的 `.claude/skills/` 下。

**环境要求**：Python 3.9 及以上，只用标准库，无需安装任何依赖。运行不了脚本的环境里技能照样能写，但会在交付时注明“格律未经脚本校验”。

## 怎么用

装好之后直接说想写什么，不用提技能名，也不用懂格律：

- 我兄弟下周六四十岁生日，帮我写首定场诗，要有气势
- 用《临江仙》写一下今天和老同学的聚会
- 帮我看看这首七律哪里不合律，尽量少改
- 学李白的口气写一首辞职创业的诗，长一点没关系
- 以“春华秋实”四字写一首藏头诗
- “看”在这里读平还是仄？

## 格律脚本

脚本在 [`shici-studio/scripts/`](shici-studio/scripts/)，也可以单独当命令行工具用。

```console
$ python3 scripts/meter.py check "白日依山尽，大河入海流。欲穷千里目，更上一层台。"
体裁：五言绝句    韵书：平水韵
韵部：下平十一尤

 1  白日依山尽  ●●○○●   谱 ⊙仄平平仄
 2  大河入海流  ●○●●○   谱 ⊙平⊙仄平
 3  欲穷千里目  ●○○●●   谱 ⊙平⊙仄仄
 4  更上一层台  ◐●●○○   谱 ⊙仄⊙平平

错误：
  ✗ [出韵] 第4句韵脚“台”属上平四支、上平十灰，不在下平十一尤
  ✗ [孤平] 第2句犯孤平：“大河入海流”除韵脚外只剩一个平声字
※ 仄起，首句不入韵
结论：不合律（错误 2，小疵 0，提示 0）
```

| 命令 | 作用 |
|---|---|
| `meter.py check "全诗"` | 校验格律，自动识别五七言绝句、律诗、排律 |
| `meter.py check --form 词:浣溪沙 "全词"` | 按词谱校验 |
| `meter.py check --form 古风 "全诗"` | 古风只查押韵，允许换韵、邻韵通押 |
| `meter.py check --loose "全诗"` | 押韵严格，平仄只作提示（定场诗、打油诗用） |
| `meter.py check --rhyme xinyun "全诗"` | 改用中华新韵 |
| `meter.py lookup 看思白` | 查字的平水韵韵目、平仄、词林正韵部、新韵 |
| `meter.py rhymes 下平七阳 --common 60` | 列出韵部常用字，选韵用 |
| `meter.py cipai 水调歌头` | 显示词谱、声情、范例；不带参数列出全部 40 个词牌 |
| `meter.py annotate "任意文字"` | 逐字标平仄 |
| `dupcheck.py "全诗"` | 撞句检查 |
| `dupcheck.py --find 大鹏一日同风起` | 在诗库里查原文 |

能查出的问题：出韵、失粘、失对、孤平、三平尾、平仄不合、拗而未救、韵脚仄声、重字、邻韵通押；能识别常见拗救和特拗；多音字（看、思、过、听、忘、教……）按格律位置给出读音提示。

### 准确度

[`tools/test_meter.py`](tools/test_meter.py) 拿唐诗三百首、千家诗、宋词三百首回测。名篇里本来就有古绝、拗律、折腰体，所以不可能 100% 通过：

| 体裁 | 篇数 | 脚本判为无错误 |
|---|---:|---:|
| 七言绝句 | 145 | 94% |
| 五言律诗 | 125 | 94% |
| 七言律诗 | 101 | 85% |
| 五言绝句 | 68 | 59%（多为古绝） |

16 个构造用例（失粘、失对、孤平、三平尾、出韵、拗救等）全部判对。

### 已知边界

- 不查对仗。律诗中二联和对联的词性相对，由模型自己判断。
- 多音字只给提示，字义由模型判断。
- 平水韵源数据漏收了少数常用字，已用词林正韵补全平仄，具体韵目是推定的，报告里会注明。
- 词谱只收 40 个常用词牌，各取通行正体。长调里又一体较多（如《念奴娇》《贺新郎》），按正体校验时容易报错。

## 目录结构

```
shici-studio/            ← 技能本体，安装时只需要这个目录
├── SKILL.md             ← 入口：工作流程与原则
├── references/          ← 按需读取的参考：类型、体裁、风格、立意、用典、改诗
├── scripts/             ← meter.py（格律）、dupcheck.py（撞句）、shici_data.py
└── assets/              ← 韵书、词谱、诗库（数据来源见 assets/LICENSES.md）
examples/                ← 实际输出示例
evals/                   ← 评测用例（skill-creator 格式）
tools/                   ← 数据构建脚本与回归测试
```

## 数据来源

| 数据 | 来源 | 许可 |
|---|---|---|
| 平水韵 | [rbnyng/pingshui_rhyme](https://github.com/rbnyng/pingshui_rhyme)（取自维基文库），漏收字由 [charlesix59/chinese_word_rhyme](https://github.com/charlesix59/chinese_word_rhyme) 补齐 | MIT |
| 繁简转换 | [OpenCC](https://github.com/BYVoid/OpenCC) | Apache-2.0 |
| 中华新韵 | 由 [pypinyin](https://github.com/mozillazg/python-pinyin) 的拼音数据推导 | MIT |
| 诗库、词谱统计、字频 | [chinese-poetry](https://github.com/chinese-poetry/chinese-poetry) | MIT |

词谱的句读和韵位依通行正体手工整理，逐字平仄据全宋词同调作品统计。古典诗词原文属于公有领域。详细声明见 [`shici-studio/assets/LICENSES.md`](shici-studio/assets/LICENSES.md)。

## 参与

发现格律误判、想加词牌或风格，欢迎提 Issue 或 PR，详见 [CONTRIBUTING.md](CONTRIBUTING.md)。报告误判时请附上原诗和脚本输出。

## 许可证

[MIT](LICENSE)。第三方数据沿用各自的许可，见上表。
