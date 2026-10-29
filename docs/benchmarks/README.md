# 基准测试结果

这个目录存放验收数字，全部由 `scripts/` 里的脚本生成；手工不改数字。音频与标注文件**不提交**进仓库。

| 文件 | 生成脚本 | 对应验收项 |
|---|---|---|
| `step-1-beats.md` / `.json` | `scripts/eval_beats.py` | 节拍 F-measure ≥ 85%（GTZAN） |
| `step-1-timing.md` / `.json` | `scripts/time_pipeline.py` | 4 分钟歌曲分轨 + 节拍 ≤ 90 秒（单张 GPU） |
| `step-2-chords.md` / `.json` | `scripts/eval_chords.py` | 和弦 majmin ≥ 80%、调性 ≥ 85%（GuitarSet 报数半与 AAM 500 首） |
| `step-2-timing.md` / `.json` | `scripts/time_pipeline.py --out docs/benchmarks/step-2-timing` | 4 分钟歌曲和弦 + 调性 ≤ 30 秒 |

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
   pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu128   # 按服务器的 CUDA 版本选，见 pytorch.org
   pip install -e ".[analysis]" -r scripts/requirements-eval.txt
   python scripts/eval_beats.py --audio /data/gtzan --annotations /data/beat_this_annotations/gtzan/annotations/beats \
       --inputs mix,drums_bass --device cuda
   python scripts/time_pipeline.py /data/some-4-minute-song.mp3 --device cuda
   ```

   先加 `--limit 5` 做一次干跑确认目录对了。两个脚本都把结果写到本目录，提交即可。

## 第 2 步：准备 GuitarSet 与 AAM

两个数据集都在 Zenodo，用它的 API 列文件再下载（`curl -s https://zenodo.org/api/records/<id>` 的 `files` 字段）。

1. **GuitarSet**（Zenodo record 3371780；360 段约 30 秒的原声吉他录音，谱面 / 实奏和弦、调性、拍点）：下载 `annotation.zip` 与 `audio_mono-mic.zip`，解压到 `/data/guitarset/`，得到 `annotation/*.jams` 与 `audio_mono-mic/*_mic.wav`。脚本默认用谱面和弦（lead sheet）与麦克风录音；吉他手 00–02 调参、03–05 报数。
2. **AAM**（Zenodo record 5794629，CC BY 4.0；3000 首合成多轨）：下载标注包 `0001-1000-annotations-v1.1.0.zip` 和覆盖前 500 首混音的音频包，解压到 `/data/aam/`。脚本按编号取前 500 首，按文件名里的 `chord` / `key` / `beat` 关键词找 ARFF 标注、按 `mix` 找音频。
3. 运行：

   ```bash
   pip install -e ".[analysis]" -r scripts/requirements-eval.txt
   python scripts/eval_chords.py --guitarset /data/guitarset --aam /data/aam --inspect      # 先核对格式
   python scripts/eval_chords.py --guitarset /data/guitarset --aam /data/aam --limit 3 --no-tune --out /tmp/dryrun
   python scripts/eval_chords.py --guitarset /data/guitarset --aam /data/aam --device cuda --cache /data/eval-cache
   python scripts/time_pipeline.py /data/song-4min.mp3 --device cuda --out docs/benchmarks/step-2-timing
   ```

   `--cache` 把各专家的逐拍输出存下来，调参和复跑不用重算模型。
