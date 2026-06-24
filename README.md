# Awen Subtitle Engine (ASE)

AI字幕自动生成服务。视频播放时自动检测字幕，若缺失则自动生成原语言字幕 + 中文翻译字幕。

**独立后端服务**，不绑定任何播放器/NAS 平台。Jellyfin、Plex、Emby、网页播放器均可通过 API 接入。

## 功能

- 🎬 自动提取视频音频（FFmpeg）
- 🗣️ 语音识别 + 语言检测（faster-whisper）
- 🌐 批量翻译（Gemini / OpenAI）
- 📝 生成双语字幕（SRT）
- 🔄 视频 Hash 缓存（相同视频不重复处理）
- 📂 目录监控自动扫描
- 🐳 Docker 一键部署

## 支持

| 视频格式 | 语言 |
|---------|------|
| MKV, MP4, AVI, MOV, FLV, WebM | 日语 → 中文 |
| | 英语 → 中文 |
| | 韩语 → 中文 |

## 快速开始

### 1. 克隆

```bash
git clone https://github.com/awenstudio/awen-subtitle-engine.git
cd awen-subtitle-engine
```

### 2. 配置

```bash
cp .env.example .env
# 编辑 .env，填入 Gemini API Key
```

### 3. 启动

```bash
docker compose up -d
```

服务启动在 `http://localhost:8000`

### 4. 使用

**创建字幕生成任务：**

```bash
curl -X POST http://localhost:8000/api/subtitle/generate \
  -H "Content-Type: application/json" \
  -d '{"video_path": "/media/movie.mkv"}'
```

**查询任务进度：**

```bash
curl http://localhost:8000/api/job/1
```

**获取字幕：**

```bash
curl http://localhost:8000/api/subtitle/video/1
```

## API

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/health` | GET | 健康检查 |
| `/api/subtitle/generate` | POST | 创建字幕任务 |
| `/api/job/{id}` | GET | 查询任务进度 |
| `/api/subtitle/video/{id}` | GET | 获取字幕文件 |
| `/api/subtitles` | GET | 列出所有字幕状态 |

## Jellyfin 集成

1. 播放视频时，Jellyfin 插件调用 `GET /api/subtitle/video/{id}`
2. 若返回 `status: processing`，显示"AI字幕生成中..."
3. 若返回字幕路径，直接挂载到播放器

## 目录监控

将视频文件放入 `MEDIA_ROOT` 目录，系统自动检测并创建字幕生成任务。

```bash
# 手动触发
cp movie.mkv /media/movies/
# 系统自动开始处理，字幕输出到 /data/subtitles/
```

## 目录结构

```
/media/
├── movie.mkv

/data/subtitles/
├── movie.ja.original.srt    # 日语原文字幕
├── movie.ja.chinese.srt     # 中文字幕
└── movie.ja.bilingual.srt   # 双语字幕
```

## 性能

在绿联 DXP4800 Plus (Intel 8505) 上的预估：

| 模型 | 1小时视频转录耗时 | 内存占用 |
|------|------------------|---------|
| tiny | ~3 分钟 | ~1GB |
| base | ~5 分钟 | ~1GB |
| small | ~10 分钟 | ~2GB |
| medium (推荐) | ~20 分钟 | ~2GB |
| large-v3 | ~50 分钟 | ~4GB |

翻译耗时：约 10-30 秒（Gemini API）

## License

MIT
