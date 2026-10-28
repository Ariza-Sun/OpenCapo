# 基准测试结果

这个目录存放验收数字，全部由 `scripts/` 里的脚本生成；手工不改数字。音频与标注文件**不提交**进仓库。

| 文件 | 生成脚本 | 对应验收项 |
|---|---|---|
| `step-1-beats.md` / `.json` | `scripts/eval_beats.py` | 节拍 F-measure ≥ 85%（GTZAN） |
| `step-1-timing.md` / `.json` | `scripts/time_pipeline.py` | 4 分钟歌曲分轨 + 节拍 ≤ 90 秒（单张 GPU） |

## 第 1 步：准备 GTZAN

1. **标注**（拍点 + 强拍，MIT）：

   ```bash
   git clone --depth 1 https://github.com/CPJKU/beat_this_annotations /data/beat_this_annotations
   # 用到的目录：/data/beat_this_annotations/gtzan/annotations/beats/  （gtzan_<流派>_<编号>.beats）
   ```

   文件格式：每行 `时间(秒)<TAB>拍序号`，拍序号为 1 的是强拍。来源是 Marchand & Peeters 2015 的 GTZAN-Rhythm 标注（经 Böck 整理）。

2. **音频**（1000 首 × 30 秒，10 个流派；原始服务器已下线，用镜像）：
   - Kaggle "GTZAN Dataset - Music Genre Classification"（约 1.2 GB），解压后用 `Data/genres_original/`；
   - 或 Hugging Face `marsyas/gtzan`。

   脚本按 `<流派>.<编号>.wav`（或原版的 `.au`）递归匹配，所以放在任意子目录都行。已知 `jazz.00054` 损坏，会被报出并跳过，实际曲目数写在结果里。

3. **安装与运行**（在 GPU 服务器上）：

   ```bash
   pip install -e ".[analysis]" -r scripts/requirements-eval.txt
   python scripts/eval_beats.py --audio /data/gtzan --annotations /data/beat_this_annotations/gtzan/annotations/beats \
       --inputs mix,drums_bass --device cuda
   python scripts/time_pipeline.py /data/some-4-minute-song.mp3 --device cuda
   ```

   先加 `--limit 5` 做一次干跑确认目录对了。两个脚本都把结果写到本目录，提交即可。
