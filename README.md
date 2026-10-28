# OpenCapo

开源的"听歌出弹唱谱"Discord Bot：上传一首歌的音频，几分钟后得到一张吉他弹唱谱（和弦图 + 六线谱节奏型 + 简谱 + 歌词），可以换演唱调、指法调、节奏型，导出 PNG / PDF / MusicXML。中文 / 英文歌曲均支持。

An open-source Discord bot that turns a song's audio into a guitar play-along sheet (chord diagrams, strumming tab, numbered-notation melody, aligned lyrics), with singing-key / fingering-key / strum-pattern options and PNG / PDF / MusicXML export. Chinese and English songs supported.

## 文档

| 文档 | 内容 |
|---|---|
| [docs/REQUIREMENTS.md](docs/REQUIREMENTS.md) | 阶段 1 需求：做什么、做到什么程度、验收标准、后续开发 |
| [docs/ROADMAP.md](docs/ROADMAP.md) | 分步路线图：先做什么后做什么，每步的验收标准 |
| [CLAUDE.md](CLAUDE.md) | 给 agent 的工作说明与硬性边界 |
| [docs/plans/frontend-discord.md](docs/plans/frontend-discord.md) | Discord 前端计划：命令、控件、约束、与后端的接口 |
| [docs/plans/backend.md](docs/plans/backend.md) | 后端计划：架构、分析流水线、编配、渲染、存储、部署 |
| [docs/plans/step-0.md](docs/plans/step-0.md) | 第 0 步实现计划：项目骨架、数据模型、CLI |
| [docs/plans/step-1.md](docs/plans/step-1.md) | 第 1 步实现计划：分轨、节拍、BPM、拍号 |
| [docs/benchmarks/](docs/benchmarks/README.md) | 验收数字（由脚本生成）：节拍 F-measure、各环节耗时 |
| [docs/reference/desperado-sheet.webp](docs/reference/desperado-sheet.webp) | 弹唱谱默认排版标准 |

## 状态

阶段 1 第 1 步（分轨 + 节拍 + BPM）实现中，见 [docs/plans/step-1.md](docs/plans/step-1.md)。`opencapo analyze` 已能解码音频（8 分钟上限）、用 Demucs 分轨（只在内部用，结束即删）、用 Beat This! 输出拍点 / 小节 / 全局 BPM / 拍号。验收数字见 [docs/benchmarks/](docs/benchmarks/README.md)（待在 GPU 上生成）。和弦、调性、编配、渲染与 Discord Bot 尚未开始。

## 开发

需要 Python ≥ 3.11 和 `ffmpeg` 命令行工具（解码音频）。

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
ruff format --check . && ruff check . && mypy && pytest
```

跑分析流水线还要装模型依赖（torch、demucs、beat-this；GPU 版 torch 按 pytorch.org 的说明装）：

```bash
pip install -e ".[dev,analysis]"
python scripts/make_tone.py click.wav --click 120 --seconds 12
opencapo analyze click.wav --out analysis.json --timing -
pytest -m models   # 真模型的端到端测试（CPU 也能跑，首次会下载权重）
```

模型权重首次运行时自动下载，各自的许可证见 [docs/plans/backend.md](docs/plans/backend.md) 第 2.1 节；Demucs 的权重许可证未声明，按非商业对待。

## 许可证

MIT，见 [LICENSE](LICENSE)。依赖的模型权重各有其许可证，选型时逐个核对。
