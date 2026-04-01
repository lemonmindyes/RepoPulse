import json
import argparse

from analysis import tag_repo, aggregate_by_topic_score
from cli import print_all_topic_trends_cli_rich, print_topics_cli_rich
from crawler import get_trending
from history_store import load_all_topic_histories, save_topic_snapshot
from topic import compute_topic_heat


def build_topic_heat(*, languages: list[str], time_range: str) -> dict:
    data = get_trending(languages=languages, time_range=time_range)
    if data is None:
        with open("trending.json", "r", encoding="utf-8") as f:
            data = json.load(f)

    tagged = [tag_repo(repo) for repo in data]
    buckets = aggregate_by_topic_score(tagged)
    topic_heat = compute_topic_heat(buckets)
    save_topic_snapshot(
        topic_heat,
        time_range=time_range,
        languages=languages,
    )
    return topic_heat


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Analyze trending topics from GitHub repositories\n"
        "分析 GitHub Trending 仓库的热门话题"
    )
    # time range（分析时间范围）
    parser.add_argument(
        "--time-range",
        choices=["daily", "weekly", "monthly"],
        default="daily",
        help="Time range for analysis (daily/weekly/monthly) (default: daily)\n"
        "分析时间范围 (daily/weekly/monthly)",
    )

    # languages (语言列表)
    parser.add_argument(
        "--languages",
        nargs="+",
        default=[
            "python",
            "c++",
            "c",
            "java",
            "javascript",
            "typescript",
            "go",
            "rust",
            "shell",
        ],
        help="List of programming languages to analyze "
        "(default: python c++ c java javascript typescript go rust shell)\n"
        "任何要分析的编程语言列表",
    )

    # top_k_topics (输出主题数)
    parser.add_argument(
        "--top-k-topics",
        type=int,
        default=5,
        help="Number of topics to print (default: 5)\n",
    )

    # top_k_repos (输出仓库数)
    parser.add_argument(
        "--top-k-repos",
        type=int,
        default=5,
        help="Number of repositories to print (default: 5)\n",
    )

    parser.add_argument(
        "--trending",
        choices=["local", "web"],
        help="Print all topic trends from local history or refresh from web first\n",
    )

    parser.add_argument(
        "--history-limit",
        type=int,
        default=20,
        help="Number of history points to show in trending mode (default: 20)\n",
    )

    args = parser.parse_args()

    if args.trending == "local":
        histories = load_all_topic_histories(
            time_range=args.time_range,
            languages=args.languages,
            limit=args.history_limit,
        )
        print_all_topic_trends_cli_rich(histories, time_range=args.time_range)
        raise SystemExit(0)

    if args.trending == "web":
        build_topic_heat(languages=args.languages, time_range=args.time_range)
        histories = load_all_topic_histories(
            time_range=args.time_range,
            languages=args.languages,
            limit=args.history_limit,
        )
        print_all_topic_trends_cli_rich(histories, time_range=args.time_range)
        raise SystemExit(0)

    # 1. 获取 trending
    topic_heat = build_topic_heat(languages=args.languages, time_range=args.time_range)
    # # 3. 打印结果
    print_topics_cli_rich(
        topic_heat,
        top_k_topics=args.top_k_topics,
        top_k_repos=args.top_k_repos,
        time_range=args.time_range,
    )
