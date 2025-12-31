import json

from analysis import tag_repo, aggregate_by_best_topic
from cli import print_topics_cli_rich
from crawler import get_trending
from topic import compute_topic_heat


if __name__ == '__main__':
    # 1. 获取 trending
    get_trending()
    # 2. 分析 trending topic
    with open('trending.json', 'r', encoding = 'utf-8') as f:
        data = json.load(f)
    tagged = [tag_repo(repo) for repo in data]
    buckets = aggregate_by_best_topic(tagged)
    topic_heat = compute_topic_heat(buckets)
    # 3. 打印结果
    print_topics_cli_rich(topic_heat)
