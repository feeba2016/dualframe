# Manifest 格式

参考结构如下。空值用于新任务选题草稿，必须按本轮真实内容填写后才能渲染；下方为字段结构示意，需补齐另一侧与其余轮次，不可直接用于真实制作。

```json
{
  "title": "本轮中性标题",
  "brief": {"status": "confirmed", "confirmation": "本轮用户选题或确认的原话", "confirmed_at": "ISO 时间"},
  "font": "/path/to/cjk-font.ttc",
  "source_label": "原片来源的中性简称",
  "max_duration_difference_ratio": 0.10,
  "speakers": {
    "top": {"name_en": "Speaker A", "name_zh": "人物甲", "date": "2026.01.01", "file": "source/a.mp4", "url": "https://example.org/original-a", "source_offset": 0, "crop": [1008, 560, 136, 0]},
    "bottom": {"name_en": "Speaker B", "name_zh": "人物乙", "date": "2026.01.02", "file": "source/b.mp4", "url": "https://example.org/original-b", "source_offset": 100, "crop": [1008, 560, 136, 0]}
  },
  "phases": [
    {"name": "01-top", "speaker": "top", "start": 3.0, "end": 18.0, "ends_after": "完整的英文句尾。", "boundary_reviewed": true, "hold_zh": "暂停保留的完整中文句意。", "hold_en": "The complete English thought to keep while paused.", "cues": [[3.0, 18.0, "对应中文。", "Corresponding English."]]}
  ]
}
```

- `speakers` 必须有且仅有 `top`、`bottom`。每位至少一轮，默认四轮交替；相同人物前后选段按原片先后排列。
- `start/end` 和 cue 时间为所填本地媒体文件的秒数；`source_offset` 为该文件在原片中的起始位置。例如本地 start=3、offset=100，来源原片时间为 103 秒。
- `crop=[宽,高,x,y]` 必须匹配本轮实际画面。渲染为 1080×600，裁切比例应接近 1.8，避免人物变形或字幕推广条入画。
- 字幕 cue 为 `[开始,结束,中文,英文]`。允许 `\n` 手动换行；自动换行超出限制会报错，需缩短单屏内容并依据实际词时码拆分。
- `max_duration_difference_ratio` 默认为 0.10，按 `(较长-较短)/较长` 计算；确因完整语义需放宽时与用户说明并记录，不以填充或变速解决。
- `boundary_reviewed` 只表示制作人完成核对；机器不能从这个字段自动证明语义。填写 `ends_after` 和真实来源时间码便于复查。
- 字体与媒体的相对路径均以 manifest 所在目录为基准。输出默认在该目录 `output/`。

运行：

```bash
python /path/to/dualframe/scripts/render_video.py 本轮目录/manifest.json --check-only
python /path/to/dualframe/scripts/render_video.py 本轮目录/manifest.json
```

- 日期字段是画面展示文字；来源说明必须另外记录日期是拍摄日、事件日还是发布日期。`url` 填可追溯的来源页面，不填带签名的临时媒体地址。
- 同一人物跨时期时，`top` / `bottom` 对应两个时期；姓名可加入时期标签，仍须满足宽度校验。
