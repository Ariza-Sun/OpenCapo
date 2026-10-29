# 第 1 步：节拍评测（GTZAN）

由 `scripts/eval_beats.py` 生成于 2026-10-29。
设备：NVIDIA GeForce RTX 3090；Python 3.12.13；opencapo 0.0.1、torch 2.5.1+cu121、beat-this 1.1.0、demucs 4.1.0、mir_eval 0.8.2、numpy 2.5.4

曲目数：998（标注与音频都齐全的）。指标：mir_eval `beat.f_measure`，70 ms 容差，去掉前 5 秒。验收门槛：拍点 F1 ≥ 85%。

| 系统 | 拍点 F1 | 强拍 F1 | 每曲耗时（秒） | 验收 |
|---|---|---|---|---|
| annotations | 1.000 | 1.000 | 0.00 | 自检 |
| beat_this | 0.891 | 0.786 | 0.35 | 通过 |
| beat_this (drums_bass) | 0.770 | 0.684 | 1.02 | 未通过 |

## 按流派（拍点 F1 / 强拍 F1）

| 流派 | beat_this | beat_this (drums_bass) |
|---|---|---|
| blues | 0.831 / 0.640 | 0.630 / 0.465 |
| classical | 0.660 / 0.512 | 0.089 / 0.068 |
| country | 0.944 / 0.913 | 0.882 / 0.845 |
| disco | 0.966 / 0.939 | 0.970 / 0.900 |
| hiphop | 0.977 / 0.898 | 0.966 / 0.888 |
| jazz | 0.869 / 0.745 | 0.735 / 0.596 |
| metal | 0.877 / 0.769 | 0.853 / 0.753 |
| pop | 0.952 / 0.939 | 0.935 / 0.919 |
| reggae | 0.906 / 0.681 | 0.793 / 0.664 |
| rock | 0.930 / 0.821 | 0.852 / 0.735 |

## 跳过的文件

- undecodable audio jazz.00054.wav: cannot decode jazz.00054.wav: /datasdc1/peiyan/opencapo-data/gtzan/genres/jazz/jazz.00054.wav: Invalid data found when processing input
