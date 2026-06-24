# Awen Subtitle Engine (ASE)

## 项目概述

独立的 AI 字幕自动生成服务。视频播放时自动检测字幕，若缺失则自动生成原语言字幕 + 中文翻译字幕，输出双语字幕。

**核心定位**：独立后端服务，不绑定任何播放器/NAS 平台。Jellyfin、Plex、Emby、网页播放器均可通过 API 接入。

## 目标用户

- 个人 NAS 用户（绿联、群晖、极空间等）
- 追番/看日剧/看英文视频需要中文字幕的用户

## 技术栈

| 层级 | 选型 |
|------|------|
| Language | Python 3.12 |
| Framework | FastAPI |
| Database | SQLite |
| Cache | Redis |
| Task Queue | Celery + Redis |
| ASR | faster-whisper (medium / large-v3) |
| Translation | Gemini 2.5 Flash (备用: GPT / Qwen) |
| Video | ffmpeg / ffprobe |
| Deploy | Docker Compose |

## 功能范围（V1）

### ✅ 必须有

- MKV / MP4 音频提取
- 日语 / 英语 / 韩语 → 中文
- 原语言字幕 (.srt)
- 中文字幕 (.srt)
- 双语字幕 (.srt)
- REST API（创建任务 / 查询进度 / 获取字幕）
- Docker 一键部署
- 视频 Hash 缓存（相同视频不重复处理）
- 目录监控自动扫描

### ❌ 不做

- 实时字幕（边播边出）
- GPU 集群
- 多用户系统
- 会员系统
- 字幕共享社区
- Web 管理后台
- 字幕编辑器

---

## 系统架构

```
┌─────────────────────────────────────────────────┐
│                   客户端                         │
│  Jellyfin / Plex / 网页播放器 / CLI             │
└──────────────────────┬──────────────────────────┘
                       │ REST API
                       ▼
┌─────────────────────────────────────────────────┐
│               FastAPI Server                     │
│  POST /api/subtitle/generate                    │
│  GET  /api/job/{id}                             │
│  GET  /api/subtitle/video/{id}                  │
│  GET  /api/health                               │
└──────────────────────┬──────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────┐
│              Celery Worker                       │
│                                                  │
│  ┌─────────┐  ┌──────────┐  ┌───────────┐      │
│  │ Whisper  │  │ Translate │  │  Cache    │      │
│  │ ASR      │→│ Gemini    │  │  Redis    │      │
│  └─────────┘  └──────────┘  └───────────┘      │
│                                                  │
└──────────────────────┬──────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────┐
│              Storage                             │
│  SQLite (元数据)  /  文件系统 (字幕/SRT)         │
└─────────────────────────────────────────────────┘
```

---

## 数据库设计

### videos

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 自增主键 |
| path | TEXT UNIQUE | 视频文件路径 |
| hash | TEXT | SHA256(文件前1MB + 文件大小) |
| language | TEXT | 检测到的语言 (ja/en/ko) |
| duration | REAL | 视频时长(秒) |
| created_at | DATETIME | 创建时间 |

### subtitles

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 自增主键 |
| video_id | INTEGER FK | 关联 videos |
| type | TEXT | original / chinese / bilingual |
| file_path | TEXT | SRT 文件路径 |
| created_at | DATETIME | 创建时间 |

### jobs

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 自增主键 |
| video_id | INTEGER FK | 关联 videos |
| status | TEXT | pending / processing / done / failed |
| progress | INTEGER | 0-100 百分比 |
| error | TEXT | 失败原因 |
| created_at | DATETIME | 创建时间 |
| updated_at | DATETIME | 更新时间 |

---

## API 设计

### POST /api/subtitle/generate

创建字幕生成任务。

**Request:**
```json
{
  "video_path": "/movies/isode.mkv"
}
```

**Response:**
```json
{
  "job_id": 1,
  "video_id": 1,
  "status": "pending"
}
```

### GET /api/job/{job_id}

查询任务进度。

**Response:**
```json
{
  "job_id": 1,
  "video_id": 1,
  "status": "processing",
  "progress": 67,
  "current_step": "translating"
}
```

### GET /api/subtitle/video/{video_id}

获取视频的所有字幕。

**Response:**
```json
{
  "video_id": 1,
  "language": "ja",
  "subtitles": {
    "original": "/data/subtitles/movie.jp.srt",
    "chinese": "/data/subtitles/movie.zh.srt",
    "bilingual": "/data/subtitles/movie.bi.srt"
  }
}
```

### GET /api/health

健康检查。

**Response:**
```json
{
  "status": "ok",
  "version": "0.1.0",
  "whisper_model": "medium",
  "uptime": 3600
}
```

---

## 核心流程

```
Step 1: 接收视频路径
        ↓
Step 2: FFmpeg 提取音频 → /tmp/audio_{hash}.wav
        ↓
Step 3: faster-whisper 识别语言 (ja/en/ko)
        ↓
Step 4: faster-whisper ASR → 带时间戳的文本片段
        ↓
Step 5: 生成原语言 .srt 字幕文件
        ↓
Step 6: 批量发送 Gemini API 翻译（非逐句）
        ↓
Step 7: 生成中文 .srt 字幕文件
        ↓
Step 8: 合并生成双语 .srt 字幕文件
        ↓
Step 9: 清理临时文件，更新数据库
```

---

## 字幕格式规范

### 原语言字幕 (original)

```srt
1
00:00:01,200 --> 00:00:03,500
こんにちは

2
00:00:04,000 --> 00:00:06,200
今日はいい天気ですね
```

### 中文字幕 (chinese)

```srt
1
00:00:01,200 --> 00:00:03,500
你好

2
00:00:04,000 --> 00:00:06,200
今天天气真好啊
```

### 双语字幕 (bilingual)

```srt
1
00:00:01,200 --> 00:00:03,500
こんにちは
你好

2
00:00:04,000 --> 00:00:06,200
今日はいい天気ですね
今天天气真好啊
```

---

## 翻译 Prompt

```
你是专业影视字幕翻译专家。

要求：
1 保留人物语气
2 保留动漫/影视术语
3 不要解释，只输出翻译
4 返回 JSON 数组，保持顺序一致
5 每条翻译不超过15个中文字符
6 如果原文是语气词/感叹词，翻译成对应的中文语气词

输入：{json_array}

返回格式：["翻译1", "翻译2", ...]
```

---

## 文件结构（运行时）

```
/data/
├── subtitles/
│   ├── movie.jp.srt
│   ├── movie.zh.srt
│   └── movie.bi.srt
├── temp/
│   └── audio_{hash}.wav
└── db/
    └── ase.db
```

---

## 缓存策略

### 视频 Hash

```python
import hashlib

def compute_video_hash(filepath: str) -> str:
    """取文件前1MB + 文件大小作为 hash，速度快且碰撞率低"""
    import os
    size = os.path.getsize(filepath)
    h = hashlib.sha256()
    h.update(str(size).encode())
    with open(filepath, 'rb') as f:
        h.update(f.read(1024 * 1024))
    return h.hexdigest()
```

### 命中逻辑

1. 收到视频路径 → 计算 hash
2. 查 SQLite 是否已有该 hash 的完整字幕
3. 有 → 直接返回字幕路径
4. 无 → 新建 job 开始处理

---

## 部署配置

### 环境变量

```yaml
# Whisper
WHISPER_MODEL=medium          # tiny/base/small/medium/large-v3
WHISPER_DEVICE=cpu            # cpu/cuda
WHISPER_COMPUTE_TYPE=int8     # int8/float16/float32

# 翻译
TRANSLATION_PROVIDER=gemini   # gemini/openai/qwen
GEMINI_API_KEY=xxx
OPENAI_API_KEY=xxx

# 路径
MEDIA_ROOT=/media
SUBTITLE_ROOT=/data/subtitles
TEMP_DIR=/data/temp

# Celery
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0
```

### Docker Compose

```yaml
version: "3.8"

services:
  api:
    build: .
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000
    ports:
      - "8000:8000"
    volumes:
      - ${MEDIA_ROOT}:/media:ro
      - ${SUBTITLE_ROOT}:/data/subtitles
      - ./data/db:/data/db
    environment:
      - CELERY_BROKER_URL=redis://redis:6379/0
      - CELERY_RESULT_BACKEND=redis://redis:6379/0
    depends_on:
      - redis

  worker:
    build: .
    command: celery -A app.workers.celery_app worker --loglevel=info --concurrency=1
    volumes:
      - ${MEDIA_ROOT}:/media:ro
      - ${SUBTITLE_ROOT}:/data/subtitles
      - ${TEMP_DIR}:/data/temp
      - ./data/db:/data/db
    environment:
      - CELERY_BROKER_URL=redis://redis:6379/0
      - CELERY_RESULT_BACKEND=redis://redis:6379/0
      - WHISPER_MODEL=${WHISPER_MODEL:-medium}
    depends_on:
      - redis

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
```

---

## 性能预估（绿联 DXP4800 Plus / Intel 8505）

| 模型 | 1小时视频转录耗时 | 内存占用 |
|------|------------------|---------|
| tiny | ~3 分钟 | ~1GB |
| base | ~5 分钟 | ~1GB |
| small | ~10 分钟 | ~2GB |
| medium | ~20 分钟 | ~2GB |
| large-v3 | ~50 分钟 | ~4GB |

翻译耗时（Gemini API）：约 10-30 秒（取决于字幕条数）

**推荐配置**：medium 模型，平衡速度和精度。

---

## 开发计划

### Phase 1: 核心引擎（能 CLI 跑通）

- [ ] FFmpeg 音频提取
- [ ] faster-whisper 语言检测 + ASR
- [ ] SRT 文件生成
- [ ] Gemini 批量翻译
- [ ] 双语字幕合成
- [ ] 视频 hash 缓存

### Phase 2: API 服务

- [ ] FastAPI 项目结构
- [ ] Celery 任务队列
- [ ] SQLite 数据模型
- [ ] REST API 端点
- [ ] 健康检查

### Phase 3: 部署

- [ ] Dockerfile
- [ ] docker-compose.yml
- [ ] 目录监控（watchdog）
- [ ] 环境变量配置

### Phase 4: 集成

- [ ] Jellyfin 插件（或 API 对接）
- [ ] README + 使用文档

---

## Jellyfin 集成方式

Jellyfin 通过外部字幕源 API 对接：

1. 播放视频时，Jellyfin 插件调用 `GET /api/subtitle/video/{id}`
2. 若返回 `status: processing`，Jellyfin 显示"AI字幕生成中..."
3. 若返回字幕路径，直接挂载到播放器
4. 播放器加载双语字幕显示

---

## 风险与对策

| 风险 | 影响 | 对策 |
|------|------|------|
| CPU 转录太慢 | 用户等待久 | 默认 medium 模型，支持配置 |
| 翻译质量不稳定 | 字幕不准 | 备用 GPT/Qwen，可人工校对 |
| Whisper 识别错误 | 字幕错字 | 后续版本加 WhisperX 对齐 |
| 内存不足 | Worker 崩溃 | 限制 concurrency=1 |
| API 限流 | 翻译失败 | 批量翻译 + 重试机制 |
