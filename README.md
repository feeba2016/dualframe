# DualFrame · 双帧

**Two frames. Real voices. One timeline.**

把两个人，或同一个人的两个时期，放进同一条时间线。固定上下双画面，轮流播放、另一侧定格，保留原声与中英字幕。

DualFrame 是面向 Codex 等支持 `SKILL.md` 的代理的制作工作流，附带本地 FFmpeg 渲染器。它负责把选题、原片核实、完整句意切点与成片验证连接起来。

## 适合做什么

- 两位人物的公开发言、采访与表达方式对比。
- 同一位人物早期与近期的容貌、神态及表达对照。
- 同一主题、不同年代的原声片段对比。

默认输出为 **1080 × 1920 / 30 fps**，按 **上 → 下 → 上 → 下** 交替。一侧播放时，另一侧保持上一轮末帧及完整句意字幕。原速原声，无新增评论、旁白或配乐。每侧时长默认相差不超过较长者的 10%，按完整语义选择切点。

## 安装与开始

将仓库安装为 Skill：

```bash
git clone https://github.com/feeba2016/dualframe.git ~/.codex/skills/dualframe
```

在代理中使用：

```text
使用 $dualframe，先推荐适合做跨年代对比的人物和原片。
列出来源、日期、预计时长，我选好后再制作。
```

也可以直接指定人物、时期或原片链接。代理先处理本轮选题和确认，再获取素材、核对字幕与切点；有待回复的问题时保留当前任务。**历史确认不能代替新一轮确认。** 只要求选材时先交付候选，不自动制作。

## 本地运行依赖

- Python 3.10+，安装 `requirements.txt` 中的 Pillow、NumPy。
- `ffmpeg` 与 `ffprobe` 在 PATH 中；FFmpeg 需支持 `libx264`、AAC、`ass`/libass 滤镜。
- 自行提供支持中文和英文的 `.ttf` / `.otf` / `.ttc` 字体，例如 Noto Sans CJK。字体不随仓库分发。
- 搜索、原片获取与转写由运行此 Skill 的代理使用现有工具完成；`yt-dlp` 和本地转写器可选。渲染器本身不依赖 API key 或 MoneyPrinterTurbo 服务。

```bash
python3 -m venv .venv
# macOS / Linux；Windows 使用 .venv\Scripts\python.exe
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python scripts/new_job.py --root /path/to/project --font /path/to/cjk-font.ttc
```

填写本轮 `brief.json`、来源记录及 `manifest.json` 后：

```bash
.venv/bin/python scripts/render_video.py /path/to/job/manifest.json --check-only
.venv/bin/python scripts/render_video.py /path/to/job/manifest.json
```

`new_job.py` 创建 `视频任务/时间戳-标识/`，并在状态文件指向未完成任务时复用已有目录。字体也可稍后写入 manifest；媒体与字体的相对路径以 manifest 所在目录为准。默认输出到该任务的 `output/`。不要并发修改同一个任务状态或同时渲染同一输出目录。

配置与生产细节见 [Manifest 格式](references/manifest.md) 和 [生产流程](references/production.md)。

## 交付与验证

| 文件 | 内容 |
| --- | --- |
| `成片_中英双语.mp4` | 上下双画面、烧录双语字幕的成片 |
| `字幕_中英双语.srt` | 当前发言侧的中英双语字幕 |
| `timeline.json` | 每轮成片位置与原片时间码 |
| `qa/report.json` | 暂停区域检查、全片解码、画幅与字幕时序检查 |
| `qa/contact-sheet.jpg` | 各轮画面缩略图 |
| 制作人保存的来源说明 | 官方来源、日期性质、原片时间码、用户确认和切点依据 |

渲染器拒绝缺少本轮确认、无原声音轨、不平衡选段、越界裁切、重叠字幕等配置。原片身份、翻译准确性与切点语义必须由制作人对照原片核实；配置中的 `boundary_reviewed` 是核对记录。帧差检查只抽样检查画面运动与静止，不能证明人物身份或完整句意。

画质优先靠高分辨率原片、合适裁切和较少转码。默认 Lanczos 缩放、H.264 CRF 16；输出 1080p 不能恢复低清原片中缺失的细节。两位人物各使用一个连续文件及固定裁切；同一选段内镜头变化较大时，应先生成经过核实的取景素材，或调整渲染实现。

## 自检

```bash
.venv/bin/python scripts/smoke_test.py --font /path/to/cjk-font.ttc
```

使用临时生成的测试图和提示音验证：任务恢复、不允许未确认任务渲染、四轮交替、SRT 与成片输出、暂停检查及全片解码。测试素材不含真实人物或讲话，运行后自动清理。首次发布在 macOS / Python 3.11 完成验证；Windows/Linux 尚未实机验证。

## 致谢

感谢 **Harry / harry0703** 及 [MoneyPrinterTurbo](https://github.com/harry0703/MoneyPrinterTurbo) 社区。我们最初使用其 [原版视频 Skill](https://github.com/harry0703/MoneyPrinterTurbo/blob/v1.3.8/docs/skill/SKILL.md) 开始视频制作实践，并受到其可执行工作流与成片交付方式的启发。

DualFrame 将真实原片核实、上下暂停交替、完整句意切点和双语字幕整理为独立工作流。独立渲染器不调用 MoneyPrinterTurbo 服务。感谢 FFmpeg、Pillow、NumPy 与 yt-dlp 提供的基础能力。详细说明与上游 MIT 许可全文见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。

代码与文档采用 [MIT License](LICENSE)。原片与字体各自保留其权利归属。
