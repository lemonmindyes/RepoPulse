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
        topic_score_sum = 0.0

        for r in repos:
            scores = r.get('topic_scores', {})
            topic_score = float(scores.get(topic, 0.0))

            added_stars = int(r.get('added_stars') or 0)
            repo_stars = int(r.get('repo_stars') or 0)
            repo_forks = int(r.get('repo_forks') or 0)

            heat = (
                topic_score
                * math.log1p(added_stars)
                * math.log1p(repo_stars)
                * math.log1p(repo_forks)
            )

            total_heat += heat
            topic_score_sum += topic_score

        repo_count = len(repos)
        avg_score = topic_score_sum / repo_count if repo_count else 0.0

        result[topic] = {
            'heat': round(total_heat, 4),
            'repo_count': repo_count,
            'avg_score': round(avg_score, 4),
            'repos': repos,
        }

    return result
