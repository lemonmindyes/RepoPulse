from collections import defaultdict

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

TOPIC_KEYWORDS = {
    "LLM_Infra": [
        "llm", "inference", "serving", "vllm", "llama.cpp",
        "quantization", "high-throughput", "transformer",
        "rag", "semantic retrieval", "context-aware"
    ],
    "Multimodal_AI": [
        "tts", "speech-to-text", "transcription", "ocr",
        "avatar", "digital human", "song generation",
        "audio", "video generation", "pdf linearization"
    ],
    "Agent_MCP": [
        "agent", "coding agent", "mcp", "model context protocol",
        "skills", "workflow", "prompt engineering", "system prompt",
        "claude code", "autonomous"
    ],
    "Database_Storage": [
        "database", "postgres", "mysql", "mariadb", "sqlite",
        "redis", "mongodb", "timescale", "time-series",
        "kv", "key-value", "object store", "s3", "zfs"
    ],
    "System_Kernel": [
        "kernel", "os", "xv6", "linux distribution",
        "interpreter", "emulator", "x86-64 emulator",
        "runtime", "virtual machine"
    ],
    "Embedded_Firmware": [
        "firmware", "embedded", "freertos", "zephyr",
        "iot", "esp32", "microcontroller", "u-boot",
        "flight control", "navigation", "keyboard firmware",
        "qmk", "zmk"
    ],
    "Networking_Security": [
        "network", "wireguard", "overlay network", "proxy",
        "gateway", "traefik", "sso", "mfa", "encryption",
        "tls", "vault", "secrets management", "honeypot",
        "detection tests", "sigma rule"
    ],
    "DevTool_Testing": [
        "framework", "sdk", "library", "testing framework",
        "unit-test", "mocking", "profiling", "tracing",
        "ci/cd", "deployment", "docker"
    ],
    "CLI_Editor": [
        "cli", "terminal", "shell", "prompt renderer",
        "oh-my-posh", "text editor", "hex editor",
        "notepad", "reverse engineering"
    ],
    "WebApp_Monitoring": [
        "self-hosted", "web ui", "dashboard", "monitoring",
        "uptime", "alerting", "rss", "news aggregation",
        "youtube downloader"
    ],
    "Game_Physics": [
        "game engine", "physics engine", "collision detection",
        "rigid body", "rendering", "godot", "graphics",
        "gpu kernel"
    ],
    "Collection_Edu": [
        "awesome", "curated list", "collection", "roadmap",
        "programming books", "algorithms", "educational"
    ],
    "FinTech": [
        "algorithmic trading", "quant", "backtesting",
        "financial library"
    ]
}

_TOPIC_NAMES = list(TOPIC_KEYWORDS.keys())
_TOPIC_DOCS = [' '.join(TOPIC_KEYWORDS[t]) for t in _TOPIC_NAMES]
_VECTORIZER = TfidfVectorizer(
    stop_words = 'english',
    ngram_range = (1, 3)
)
_TOPIC_VECS = _VECTORIZER.fit_transform(_TOPIC_DOCS)


def classify_repo(text: str):
    """
    input: repo_name + repo_description
    output: best_topic, (topic: score)
    """
    repo_vec = _VECTORIZER.transform([text])
    sims = cosine_similarity(repo_vec, _TOPIC_VECS)[0]

    scores = {
        topic: float(score)
        for topic, score in zip(_TOPIC_NAMES, sims)
    }
    best_topic = max(scores, key = scores.get)

    if scores[best_topic] < 0.12:
        best_topic = "Unknown"
    return best_topic, scores


def tag_repo(repo: dict):
    text = f'{repo.get('repo_name', '')} {repo.get('repo_describe', '')}'
    topic, scores = classify_repo(text)

    repo['topic'] = topic
    repo['topic_scores'] = scores
    return repo


def aggregate_by_best_topic(repos):
    buckets = defaultdict(list)

    for r in repos:
        topic = r.get("topic")
        if topic and topic != "Unknown":
            buckets[topic].append(r)

    return dict(buckets)
