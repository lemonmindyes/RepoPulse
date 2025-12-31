import json

import requests
from fake_useragent import UserAgent
from lxml import etree


def keep_latest_repo(data: list[dict]) -> list[dict]:
    seen = set()
    result = []

    for item in data:
        repo_path = (item['repo_author'], item['repo_name'])

        if repo_path not in seen:
            result.append(item)
            seen.add(repo_path)

    return result


def get_trending(languages: list[str] = None):
    if languages is None:
        # 预置一些常见语言的趋势页面
        urls = [
            'https://github.com/trending', # trending主页面
            'https://github.com/trending/python?since=daily', # python trending页面
            'https://github.com/trending/go?since=daily', # go trending页面
            'https://github.com/trending/c?since=daily', # c trending页面
            'https://github.com/trending/c++?since=daily' # c++ trending页面
        ]
    else:
        urls = [f'https://github.com/trending/{language}?since=daily' for language in languages]
    headers = {
        'User-Agent': UserAgent().random
    }
    data = []

    for url in urls:
        response = requests.get(url, headers = headers)
        tree = etree.HTML(response.text)

        articles = tree.xpath('//div[@class="Box"]/div[2]/article')
        for article in articles:
            repo_author = article.xpath('./h2/a/span/text()')[0].replace(' /', '').strip() # 仓库作者
            repo_name = ''.join(article.xpath('./h2/a/text()')).strip() # 仓库名称
            # 仓库描述
            if not article.xpath('./p/text()'):
                repo_describe = ''
            else:
                repo_describe = article.xpath('./p/text()')[0].strip()
            # 仓库语言
            if not article.xpath('./div[2]/span[@class="d-inline-block ml-0 mr-3"]/span[2]/text()'):
                repo_language = ''
            else:
                repo_language = article.xpath('./div[2]/span[@class="d-inline-block ml-0 mr-3"]/span[2]/text()')[0]
            repo_stars = article.xpath('./div[2]/a[1]/text()')[0].strip().replace(',', '') # 仓库 stars
            repo_forks = article.xpath('./div[2]/a[2]/text()')[0].strip().replace(',', '') # 仓库 forks
            daily_stars = ''.join(article.xpath('./div[2]/span[3]/text()')).strip().split(' ')[0] # 今日 stars
            data.append({
                'repo_author': repo_author,
                'repo_name': repo_name,
                'repo_describe': repo_describe,
                'repo_language': repo_language,
                'repo_stars': repo_stars,
                'repo_forks': repo_forks,
                'daily_stars': daily_stars
            })
    data = keep_latest_repo(data)
    with open('trending.json', 'w', encoding = 'utf-8') as f:
        json.dump(data, f, ensure_ascii = False, indent = 4)


if __name__ == '__main__':
    get_trending()