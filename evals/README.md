# 评测用例

[skill-creator](https://github.com/anthropics/skills) 格式的评测用例，用来比较技能改动前后的写作质量。每个用例目录包含：

- `prompt.md`：发给模型的用户原话
- `case.yaml`：期望结果的描述
- `graders/`：逐条评分标准

| 用例 | 考查点 |
|---|---|
| `jishi-huanxisha-wonton` | 记录生活的小事，按词谱填《浣溪沙》 |
| `yiqi-qilv-with-allusions` | 意气风发的七律，用典并注明出处 |
| `dingchang-programmer-birthday` | 寿宴定场诗，把现代人的事迹化进古典语言 |
| `taibai-gexing-dapeng` | 太白体长篇歌行，化用而不照抄李白 |
| `fix-flawed-qilv` | 修改一首有格律错误的七律，改动最小 |

这个目录不属于技能本体，安装时不需要复制。
