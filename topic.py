import math


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

    for topic, repos in buckets.items():
        total_heat = 0.0
        weighted_score_sum = 0.0
        heat_sum = 0.0

        for r in repos:
            scores = r.get('topic_scores', {})
            topic_score = float(scores.get(topic, 0.0))

            repo_stars = int(r.get('repo_stars') or 0) # 仓库stars
            repo_forks = int(r.get('repo_forks') or 0) # 仓库forks
            added_stars = int(r.get('added_stars') or 0) # 仓库新增stars
            repo_watch = int(r.get('repo_watch') or 0) # 仓库watch
            repo_issue = int(r.get('repo_issue') or 0) # 仓库issue
            repo_pr = int(r.get('repo_pr') or 0) # 仓库pr
            repo_commit = int(r.get('repo_commit') or 0) # 仓库commit

            semantic = math.sqrt(0.2 + 0.8 * topic_score)
            trend = math.log1p(added_stars)
            scale = math.log1p(repo_stars) + 0.5 * math.log1p(repo_forks)
            dev = math.log1p(repo_commit) + 0.8 * math.log1p(repo_pr) + 0.5 * math.log1p(repo_issue)
            attention = math.log1p(repo_watch)

            trend_boost = 1 + trend # 放大热度更大的项目，降低热度更小的项目
            heat = semantic * (
                0.4 * trend
                + trend_boost * (0.25 * scale + 0.25 * dev)
                + 0.1 * attention
            )

            total_heat += heat ** 0.7
            weighted_score_sum += topic_score * heat
            heat_sum += heat

        repo_count = len(repos)
        avg_score = weighted_score_sum / heat_sum if repo_count else 0.0

        result[topic] = {
            'heat': round(total_heat, 4),
            'repo_count': repo_count,
            'avg_score': round(avg_score, 4),
            'repos': repos,
        }

    return result
