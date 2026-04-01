import json
from datetime import datetime, timezone
from pathlib import Path


HISTORY_DIR = Path("history")
SNAPSHOT_DIR = HISTORY_DIR / "topic_snapshots"


def normalize_languages(languages: list[str] | None) -> list[str]:
    if not languages:
        return []
    return [str(language).lower() for language in dict.fromkeys(languages)]


def save_topic_snapshot(
    topic_heat: dict,
    *,
    time_range: str,
    languages: list[str] | None,
) -> Path:
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    created_at = datetime.now(timezone.utc)
    payload = {
        "created_at": created_at.isoformat(),
        "time_range": time_range,
        "languages": normalize_languages(languages),
        "topics": {
            topic: {
                "heat": info.get("heat", 0.0),
                "repo_count": info.get("repo_count", 0),
                "avg_score": info.get("avg_score", 0.0),
            }
            for topic, info in topic_heat.items()
        },
    }
    snapshot_path = (
        SNAPSHOT_DIR / f"{created_at.strftime('%Y%m%dT%H%M%S_%fZ')}__{time_range}.json"
    )
    snapshot_path.write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    return snapshot_path


def load_topic_history(
    topic_name: str,
    *,
    time_range: str,
    languages: list[str] | None,
    limit: int = 20,
) -> tuple[str | None, list[dict]]:
    if not SNAPSHOT_DIR.exists():
        return None, []

    normalized_languages = normalize_languages(languages)
    snapshots = []
    topic_lookup = {}

    for path in sorted(SNAPSHOT_DIR.glob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue

        if payload.get("time_range") != time_range:
            continue
        if payload.get("languages") != normalized_languages:
            continue

        topics = payload.get("topics") or {}
        for topic in topics:
            topic_lookup.setdefault(topic.lower(), topic)
        snapshots.append(payload)

    if not snapshots:
        return None, []

    resolved_topic = topic_lookup.get(topic_name.lower())
    if resolved_topic is None:
        return None, []

    history = []
    for payload in snapshots[-limit:]:
        topic_info = (payload.get("topics") or {}).get(resolved_topic) or {}
        created_at = payload.get("created_at") or ""
        try:
            dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            display_time = dt.astimezone().strftime("%m-%d %H:%M")
        except ValueError:
            display_time = created_at

        history.append(
            {
                "timestamp": created_at,
                "display_time": display_time,
                "heat": float(topic_info.get("heat") or 0.0),
                "repo_count": int(topic_info.get("repo_count") or 0),
                "avg_score": float(topic_info.get("avg_score") or 0.0),
            }
        )

    return resolved_topic, history


def load_all_topic_histories(
    *,
    time_range: str,
    languages: list[str] | None,
    limit: int = 20,
) -> dict[str, list[dict]]:
    if not SNAPSHOT_DIR.exists():
        return {}

    normalized_languages = normalize_languages(languages)
    snapshots = []

    for path in sorted(SNAPSHOT_DIR.glob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue

        if payload.get("time_range") != time_range:
            continue
        if payload.get("languages") != normalized_languages:
            continue
        snapshots.append(payload)

    if not snapshots:
        return {}

    topic_names = sorted(
        {
            topic
            for payload in snapshots
            for topic in (payload.get("topics") or {}).keys()
        }
    )
    histories = {}

    for topic_name in topic_names:
        _, history = load_topic_history(
            topic_name,
            time_range=time_range,
            languages=languages,
            limit=limit,
        )
        if history:
            histories[topic_name] = history

    return histories
