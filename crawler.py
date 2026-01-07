import asyncio
import certifi
import json
import socket
import ssl

import aiohttp
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


# 获取仓库详细页面信息
# def get_repo_detail_info(repo_url: str, headers: dict):
#     response = requests.get(repo_url, headers = headers, timeout = 5)
#     tree = etree.HTML(response.text)
#
#     repo_topics = tree.xpath('//div[@class="BorderGrid about-margin"]/div[1]//div[@class="hide-sm hide-md"]'
#                              '/div[@class="my-3"]')
#     if not repo_topics:
#         return []
#     else:
#         repo_topics = [s.strip() for s in repo_topics[0].xpath('.//text()') if s.strip()]
#     return repo_topics


async def parse_trending_page(session: aiohttp.ClientSession, url: str, semaphore: asyncio.Semaphore):
    async with semaphore:
        async with session.get(url, proxy = 'http://127.0.0.1:7890') as response:
            html = await response.text()

    tree = etree.HTML(html)
    articles = tree.xpath('//div[@class="Box"]/div[2]/article')

    page_data = []

    for article in articles:
        repo_author = article.xpath('./h2/a/span/text()')[0].replace(' /', '').strip()  # 仓库作者
        repo_name = ''.join(article.xpath('./h2/a/text()')).strip()  # 仓库名称
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
        repo_stars = article.xpath('./div[2]/a[1]/text()')[0].strip().replace(',', '')  # 仓库 stars
        repo_forks = article.xpath('./div[2]/a[2]/text()')[0].strip().replace(',', '')  # 仓库 forks
        # 今日 stars
        texts = article.xpath('./div[2]/span[@class="d-inline-block float-sm-right"]/text()')
        raw = ''.join(texts).strip()
        added_stars = raw.replace(',', '').split()[0]
        # 获取仓库详细页面信息
        # repo_url = f'{base_repo_url}/{repo_author}/{repo_name}'
        # repo_topics = get_repo_detail_info(repo_url, headers)

        # 保存信息
        page_data.append({
            'repo_author': repo_author,
            'repo_name': repo_name,
            'repo_describe': repo_describe,
            'repo_language': repo_language,
            'repo_stars': repo_stars,
            'repo_forks': repo_forks,
            'added_stars': added_stars,
            # 'repo_topics': repo_topics
        })
    return page_data


async def get_trending_async(languages: list[str] | None = None, time_range: str = 'daily'):
    if languages is None:
        # 预置一些常见语言的趋势页面
        article_urls = [
            'https://github.com/trending', # 默认 trending页面
            f'https://github.com/trending/python?since={time_range}', # python trending页面
            f'https://github.com/trending/go?since={time_range}', # go trending页面
            f'https://github.com/trending/c?since={time_range}', # c trending页面
            f'https://github.com/trending/c++?since={time_range}', # c++ trending页面
            f'https://github.com/trending/javascript?since={time_range}', # javascript trending页面
            f'https://github.com/trending/typescript?since={time_range}' # typescript trending页面
        ]
    else:
        article_urls = ['https://github.com/trending'] # 默认 trending页面
        for language in languages:
            article_urls.append(f'https://github.com/trending/{language}?since={time_range}')

    headers = {
        'User-Agent': UserAgent().edge
    }
    ssl_context = ssl.create_default_context(
        cafile = certifi.where()
    )
    connector = aiohttp.TCPConnector(ssl = ssl_context, family = socket.AF_INET, happy_eyeballs_delay = None)

    semaphore = asyncio.Semaphore(10) # 限制并发数量

    async with aiohttp.ClientSession(headers = headers, connector = connector) as session:
        tasks = [parse_trending_page(session, url, semaphore) for url in article_urls]
        results = await asyncio.gather(*tasks)

    data = [item for page in results for item in page]
    data = keep_latest_repo(data)

    with open('trending.json', 'w', encoding = 'utf-8') as f:
        json.dump(data, f, ensure_ascii = False, indent = 4)


def get_trending(languages: list[str] | None = None, time_range: str = 'daily'):
    asyncio.run(get_trending_async(languages, time_range))


if __name__ == '__main__':
    import time
    start = time.time()
    get_trending()
    print(f'耗时：{time.time() - start}秒')


