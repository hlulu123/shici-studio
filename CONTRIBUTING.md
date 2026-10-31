# 参与贡献

谢谢你愿意帮忙。下面按常见的几种情况说明。

## 报告格律误判

脚本判错是最有价值的反馈。请用 [格律误判](https://github.com/hlulu123/shici-studio/issues/new?template=meter-bug.yml) 模板提 Issue，附上：

1. 原诗全文，以及体裁（如七律、词:念奴娇）
2. 运行的命令和完整输出
3. 你认为正确的判断和依据（韵书、词谱出处）

名篇里的古绝、拗律、折腰体、词的又一体，按正体校验报错是预期行为，不算误判。

## 修改写作指导

`shici-studio/SKILL.md` 和 `shici-studio/references/` 是给模型读的说明。改动时请注意：

- **说清理由，少用命令。** 写“为什么这样做”，模型才能举一反三；一串“必须、禁止”只会让诗变得拘谨。
- **例句只用公版作品**，并注明作者和篇名。
- **典故要有可核对的出处**，写明书名和篇名。
- SKILL.md 保持精简，细节放到 references 里按需读取。

## 加一个词牌

词谱由 `tools/build_cipai.py` 生成：句读和韵位写在脚本的 `SPEC` 里，逐字平仄用全宋词同调作品统计。

1. 在 `SPEC` 里按现有格式加一条，依通行正体（龙榆生《唐宋词格律》一系）。
2. 从 [chinese-poetry](https://github.com/chinese-poetry/chinese-poetry) 取得宋词数据库 `ci.db`，然后运行：

   ```bash
   python3 tools/build_cipai.py <ci.db 路径> shici-studio -v
   ```

3. 用宋词三百首里该词牌的作品跑一遍 `meter.py check --form 词:词牌名`，确认正体作品能通过。

## 重建韵书和诗库

`tools/build_data.py` 从原始数据生成 `shici-studio/assets/` 下的韵书、诗库和字频。一般不需要重建。需要时先准备好下载目录：

```
<下载目录>/
├── pingshui/pingshui.json        rbnyng/pingshui_rhyme 的 organized_ping_ze_rhyme_dict.json
├── cwr/Cilin_Rhyme.json          charlesix59/chinese_word_rhyme
├── opencc/TSCharacters.txt       BYVoid/OpenCC
└── cp/                           chinese-poetry
    ├── tangshisanbaishou.json
    ├── qianjiashi.json
    ├── songci300.json
    ├── ci.db
    └── tang/poet.tang.*.json
```

这一步需要 [pypinyin](https://pypi.org/project/pypinyin/)（技能本身不需要）：

```bash
pip install pypinyin
python3 tools/build_data.py <下载目录> shici-studio
```

## 运行测试

```bash
python3 tools/test_meter.py       # 构造用例 + 选集回测
python3 tools/test_meter.py -v    # 同时列出回测不通过的作品
```

构造用例必须全部通过；选集回测的通过率不应明显下降。提 PR 前请贴上前后的测试输出。

## 评测

`evals/` 里是 [skill-creator](https://github.com/anthropics/skills) 格式的评测用例，用来比较改动前后的写作质量。改了写作指导的话，最好跑一轮看看输出有没有变好。

## 打包

```bash
zip -r shici-studio.skill shici-studio -x '*.DS_Store' '*/__pycache__/*'
```

发布 Release 时，GitHub Actions 会自动打包并上传到 Release 附件（见 `.github/workflows/release.yml`）。
