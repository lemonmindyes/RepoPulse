import math


def _safe_int(value) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _quantile(values: list[float], q: float) -> float:
    if not values:
        return 0.0

    ordered = sorted(values)
    if len(ordered) == 1:
        return float(ordered[0])

    pos = (len(ordered) - 1) * q
    left = int(math.floor(pos))
    right = int(math.ceil(pos))

    if left == right:
        return float(ordered[left])

    weight = pos - left
    return ordered[left] * (1 - weight) + ordered[right] * weight


def _normalize(value: float, upper: float) -> float:
    if upper <= 0:
        return 0.0
    return min(max(value / upper, 0.0), 1.0)


def _repo_key(repo: dict) -> str:
    repo_url = repo.get("repo_url")
    if repo_url:
        return str(repo_url)
    return f"{repo.get('repo_author', '')}/{repo.get('repo_name', '')}"


def _collect_signal_stats(repos: list[dict]) -> dict[str, float]:
    growth_values = []
    momentum_values = []
    scale_values = []
    activity_values = []
    issue_pressure_values = []

    for repo in repos:
        repo_stars = _safe_int(repo.get("repo_stars"))
        repo_forks = _safe_int(repo.get("repo_forks"))
        added_stars = _safe_int(repo.get("added_stars"))
        repo_issue = _safe_int(repo.get("repo_issue"))
        repo_pr = _safe_int(repo.get("repo_pr"))
        repo_commit = _safe_int(repo.get("repo_commit"))

        growth_values.append(math.log1p(added_stars))
        momentum_values.append(
            math.log1p(added_stars / max(math.sqrt(repo_stars + 1), 1.0))
        )
        scale_values.append(math.log1p(repo_stars) + 0.6 * math.log1p(repo_forks))
        activity_values.append(math.log1p(repo_commit) + 0.7 * math.log1p(repo_pr))
        issue_pressure_values.append(math.log1p(repo_issue / max(repo_pr + 1, 1)))

    return {
        "growth": _quantile(growth_values, 0.9),
        "momentum": _quantile(momentum_values, 0.9),
        "scale": _quantile(scale_values, 0.9),
        "activity": _quantile(activity_values, 0.9),
        "issue_pressure": _quantile(issue_pressure_values, 0.9),
    }


def _compute_repo_signal(repo: dict, stats: dict[str, float]) -> tuple[float, float]:
    repo_stars = _safe_int(repo.get("repo_stars"))
    repo_forks = _safe_int(repo.get("repo_forks"))
    added_stars = _safe_int(repo.get("added_stars"))
    repo_issue = _safe_int(repo.get("repo_issue"))
    repo_pr = _safe_int(repo.get("repo_pr"))
    repo_commit = _safe_int(repo.get("repo_commit"))

    growth_signal = _normalize(math.log1p(added_stars), stats["growth"])
    momentum_signal = _normalize(
        math.log1p(added_stars / max(math.sqrt(repo_stars + 1), 1.0)), stats["momentum"]
    )
    scale_signal = _normalize(
        math.log1p(repo_stars) + 0.6 * math.log1p(repo_forks),
        stats["scale"],
    )
    activity_signal = _normalize(
        math.log1p(repo_commit) + 0.7 * math.log1p(repo_pr), stats["activity"]
    )
    issue_pressure = _normalize(
        math.log1p(repo_issue / max(repo_pr + 1, 1)), stats["issue_pressure"]
    )

    base_signal = (
        0.4 * growth_signal
        + 0.25 * momentum_signal
        + 0.2 * scale_signal
        + 0.15 * activity_signal
    )
    health_factor = 1 - 0.12 * issue_pressure
    return base_signal, health_factor


def compute_topic_heat(buckets: dict):
    """
    buckets: {
        topic: [repo_dict, repo_dict, ...]
    }

    return:
    {
        topic: {
            "heat": float,
            "repo_count": int,
            "avg_score": float,
            "repos": [...]
        }
    }
    """
    result = {}
    unique_repos = {}

    for repos in buckets.values():
        for repo in repos:
            unique_repos[_repo_key(repo)] = repo

    stats = _collect_signal_stats(list(unique_repos.values()))

    for topic, repos in buckets.items():
        total_heat = 0.0
        weighted_score_sum = 0.0

        for r in repos:
            scores = r.get("topic_scores", {})
            topic_score = float(scores.get(topic, 0.0))
            if topic_score <= 0:
                continue

            signal_cache = r.setdefault("_topic_signal_cache", {})
            if "base_signal" not in signal_cache or "health_factor" not in signal_cache:
                base_signal, health_factor = _compute_repo_signal(r, stats)
                signal_cache["base_signal"] = base_signal
                signal_cache["health_factor"] = health_factor
            else:
                base_signal = signal_cache["base_signal"]
                health_factor = signal_cache["health_factor"]

            topic_fit = topic_score**0.7
            heat = 100 * topic_fit * base_signal * health_factor

            r.setdefault("topic_heat_scores", {})[topic] = round(heat, 4)
            total_heat += heat
            weighted_score_sum += topic_score * heat

        repo_count = len(repos)
        avg_score = weighted_score_sum / total_heat if total_heat else 0.0

        result[topic] = {
            "heat": round(total_heat, 4),
            "repo_count": repo_count,
            "avg_score": round(avg_score, 4),
            "repos": repos,
        }

    for repo in unique_repos.values():
        repo.pop("_topic_signal_cache", None)

    return result
