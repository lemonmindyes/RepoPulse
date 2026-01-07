from collections import defaultdict

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

TOPIC_KEYWORDS = {

    # =======================
    # LLM Infra / 推理 & 服务
    # =======================
    "LLM_Infra": [
        "llm", "large language model",
        "inference", "serving", "inference server",
        "high throughput", "low latency",
        "distributed inference", "batching",
        "kv cache", "context length",
        "quantization", "int8", "int4",
        "model serving", "model runtime",
        "transformer", "decoder-only",
        "rag", "retrieval augmented generation",
        "semantic retrieval", "vector search",
        "gateway", "api gateway",
        "llama", "mistral", "gemini", "deepseek"
    ],

    # =======================
    # Multimodal / 音视频 & OCR
    # =======================
    "Multimodal_AI": [
        "multimodal",
        "tts", "text to speech",
        "speech to text", "asr", "transcription",
        "voice cloning", "speech synthesis",
        "ocr", "pdf", "document understanding",
        "pdf linearization",
        "image generation", "video generation",
        "face swap", "deepfake",
        "avatar", "digital human",
        "song generation", "music generation",
        "audio", "video", "vision"
    ],

    # =======================
    # Agent / MCP / 自动化
    # =======================
    "Agent_MCP": [
        "agent", "ai agent", "coding agent",
        "autonomous", "agentic",
        "mcp", "model context protocol",
        "skills", "tool calling",
        "workflow", "orchestration",
        "prompt engineering", "system prompt",
        "planning", "reasoning",
        "claude", "claude code",
        "copilot", "assistant runtime",
        "multi-agent", "agent swarm"
    ],

    # =======================
    # Database / Storage
    # =======================
    "Database_Storage": [
        "database", "distributed database",
        "sql", "nosql",
        "postgres", "postgresql",
        "mysql", "mariadb", "sqlite",
        "mongodb", "redis",
        "timeseries", "time-series",
        "olap", "analytics database",
        "data warehouse",
        "object storage", "s3",
        "kv store", "key value",
        "lakehouse", "parquet"
    ],

    # =======================
    # System / OS / Runtime
    # =======================
    "System_Kernel": [
        "kernel", "operating system",
        "linux", "wayland",
        "runtime", "interpreter",
        "virtual machine", "microvm",
        "emulator", "simulation",
        "x86", "arm",
        "scheduler", "memory allocator",
        "profiling", "tracing"
    ],

    # =======================
    # Embedded / Firmware
    # =======================
    "Embedded_Firmware": [
        "embedded", "firmware",
        "microcontroller", "mcu",
        "freertos", "zephyr",
        "iot", "esp32", "esp8266",
        "flight controller",
        "navigation",
        "keyboard firmware", "qmk", "zmk",
        "bare metal"
    ],

    # =======================
    # Network / Security
    # =======================
    "Networking_Security": [
        "network", "networking",
        "proxy", "reverse proxy",
        "gateway", "load balancer",
        "vpn", "wireguard",
        "encryption", "tls", "ssl",
        "security", "vulnerability",
        "scanner", "sbom",
        "xdr", "siem",
        "auth", "sso", "oauth"
    ],

    # =======================
    # DevTools / 工具链
    # =======================
    "DevTool_Testing": [
        "developer tool", "devtool",
        "sdk", "framework", "library",
        "testing", "unit test",
        "mock", "fuzzing",
        "ci", "cd", "pipeline",
        "build system",
        "docker", "container",
        "deployment"
    ],

    # =======================
    # CLI / Editor / 本地工具
    # =======================
    "CLI_Editor": [
        "cli", "command line",
        "terminal", "shell",
        "prompt", "prompt renderer",
        "text editor", "code editor",
        "reverse engineering",
        "disassembler", "decompiler",
        "hex editor"
    ],

    # =======================
    # Web App / 监控 / 自托管
    # =======================
    "WebApp_Monitoring": [
        "web", "web ui",
        "self hosted", "self-hosted",
        "dashboard",
        "monitoring", "metrics",
        "alerting", "uptime",
        "rss", "news aggregation",
        "crawler", "scraper",
        "youtube downloader",
        "web service"
    ],

    # =======================
    # 游戏 / 物理 / 图形
    # =======================
    "Game_Physics": [
        "game engine",
        "physics engine",
        "collision detection",
        "rigid body",
        "rendering", "graphics",
        "2d engine", "3d engine",
        "godot",
        "gpu", "shader"
    ],

    # =======================
    # 集合 / 教育 / 资料
    # =======================
    "Collection_Edu": [
        "awesome",
        "curated list",
        "collection",
        "roadmap",
        "tutorial",
        "learning",
        "educational",
        "algorithms",
        "data structures",
        "book"
    ],

    # =======================
    # 金融 / 量化
    # =======================
    "FinTech": [
        "fintech",
        "trading",
        "algorithmic trading",
        "quant", "quantitative",
        "backtesting",
        "market data",
        "financial system"
    ]
}


_TOPIC_NAMES = list(TOPIC_KEYWORDS.keys())
_TOPIC_DOCS = [' '.join(TOPIC_KEYWORDS[t]) for t in _TOPIC_NAMES]
_VECTORIZER = TfidfVectorizer(
    stop_words = 'english',
    ngram_range = (1, 3)
)
_TOPIC_VECS = _VECTORIZER.fit_transform(_TOPIC_DOCS) # [n_topics, n_words]


def classify_repo(text: str):
    """
    input: repo_name + repo_description
    output: best_topic, (topic: score)
    """
    repo_vec = _VECTORIZER.transform([text]) # [1, n_words]
    sims = cosine_similarity(repo_vec, _TOPIC_VECS)[0] # [n_topics]

    topic_scores = {
        topic: float(score)
        for topic, score in zip(_TOPIC_NAMES, sims)
    }
    best_topic = max(topic_scores, key = topic_scores.get)

    if topic_scores[best_topic] < 0.1:
        best_topic = 'Unknown'
    return best_topic, topic_scores


def tag_repo(repo: dict):
    # 基础文本 （名称 + 描述）
    base_text = f'{repo.get('repo_name', '')} {repo.get('repo_describe', '')}'

    # 仓库标签
    repo_topics = repo.get('repo_topics', [])
    # 如果有标签，增强文本
    if repo_topics:
        text = base_text + ' ' + ' '.join(repo_topics)
    else:
        text = base_text
    topic, topic_scores = classify_repo(text)

    repo['topic'] = topic
    repo['topic_scores'] = topic_scores
    return repo


# 按 topic 聚合 repo
def aggregate_by_best_topic(repos):
    buckets = defaultdict(list) # 当key不存在时会自动创建一个

    for r in repos:
        topic = r.get('topic')
        if topic and topic != 'Unknown':
            buckets[topic].append(r)

    return dict(buckets)
