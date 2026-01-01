import json
import argparse

from analysis import tag_repo, aggregate_by_best_topic
from cli import print_topics_cli_rich
from crawler import get_trending
from topic import compute_topic_heat


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description = 'Analyze trending topics from GitHub repositories\n'
                      '分析 GitHub Trending 仓库的热门话题'
    )
    # time range（分析时间范围）
    parser.add_argument(
        '--time-range',
        choices = ['daily', 'weekly', 'monthly'],
        default = 'daily',
        help = 'Time range for analysis (daily/weekly/monthly) (default: daily)\n'
               '分析时间范围 (daily/weekly/monthly)'
    )

    # languages (语言列表)
    parser.add_argument(
        '--languages',
        nargs = '+',
        default = ['python', 'c++', 'c', 'java', 'javascript', 'typescript', 'go', 'rust'],
        help = 'List of programming languages to analyze (default: python c++ c java javascript typescript go rust)\n'
               '任何要分析的编程语言列表'
    )

    args = parser.parse_args()

    # 1. 获取 trending
    print(args.languages)
    get_trending(languages = args.languages,
                 time_range = args.time_range)
    # 2. 分析 trending topic
    with open('trending.json', 'r', encoding = 'utf-8') as f:
        data = json.load(f)
    tagged = [tag_repo(repo) for repo in data]
    buckets = aggregate_by_best_topic(tagged)
    topic_heat = compute_topic_heat(buckets)
    # # 3. 打印结果
    print_topics_cli_rich(topic_heat, top_k_topics = 5, top_k_repos = 5, time_range = args.time_range)
