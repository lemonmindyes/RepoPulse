import asyncio
import certifi
import json
import socket
import ssl

import aiohttp
from fake_useragent import UserAgent
from lxml import etree

from config import Cookie


def keep_latest_repo(data: list[dict]) -> list[dict]:
    seen = set()
    result = []

    for item in data:
        repo_path = (item['repo_author'], item['repo_name'])

        if repo_path not in seen:
            result.append(item)
            seen.add(repo_path)

    return result


async def get_repo_url(session: aiohttp.ClientSession, url: str, semaphore: asyncio.Semaphore):
    async with semaphore:
        async with session.get(url, proxy = 'http://127.0.0.1:7890') as response:
            html = await response.text()

    tree = etree.HTML(html)
    articles = tree.xpath('//div[@class="Box"]/div[2]/article')

    repo_urls = {}

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

        # 保存信息
        repo_urls[f'{repo_author}/{repo_name}'] = {
            'repo_author': repo_author,
            'repo_name': repo_name,
            'repo_describe': repo_describe,
            'repo_language': repo_language,
            'repo_stars': repo_stars,
            'repo_forks': repo_forks,
            'added_stars': added_stars,
            'repo_url': f'https://github.com/{repo_author}/{repo_name}'
        }
    return repo_urls


async def get_repo_detail_info(session: aiohttp.ClientSession, repo_info: str, semaphore: asyncio.Semaphore):
    async with semaphore:
        async with session.get(repo_info['repo_url'], proxy = 'http://127.0.0.1:7890') as response:
            html = await response.text()
    tree = etree.HTML(html)

    # 1、获取watch
    li_list = tree.xpath('//div[@id="repository-details-container"]/ul/li')
    if len(li_list) == 3:
        script = li_list[0].xpath('//script[@data-target="react-partial.embeddedData"]/text()')
        repo_watch = json.loads(script[2])['props']['watchersCount']
    else:
        script = li_list[1].xpath('//script[@data-target="react-partial.embeddedData"]/text()')
        repo_watch = json.loads(script[2])['props']['watchersCount']
    repo_info['repo_watch'] = str(repo_watch)

    # 2、获取issue数
    repo_issue = tree.xpath('//nav[@aria-label="Repository"]/ul/li[2]/a/span')
    if len(repo_issue) == 2:
        repo_issue = 0
    else:
        repo_issue = repo_issue[2].xpath('./span[1]/text()')[0]
    if isinstance(repo_issue, str) and repo_issue.endswith('k'):
        repo_issue = str(int(float(repo_issue[:-1]) * 1000))
    elif isinstance(repo_issue, str) and repo_issue.endswith('k+'):
        repo_issue = str(int(float(repo_issue[:-2]) * 1000))
    repo_info['repo_issue'] = repo_issue

    # 3、获取Pr数
    repo_pr = tree.xpath('//nav[@aria-label="Repository"]/ul/li[3]/a/span')
    if len(repo_pr) == 2:
        repo_pr = 0
    else:
        repo_pr = repo_pr[2].xpath('./span[1]/text()')[0]
    if isinstance(repo_pr, str) and repo_pr.endswith('k'):
        repo_pr = str(int(float(repo_pr[:-1]) * 1000))
    repo_info['repo_pr'] = repo_pr

    # 4、获取commit数
    repo_commit = tree.xpath('//table[@aria-labelledby="folders-and-files"]/tbody/tr[1]'
                             '//span[@class="fgColor-default"]/text()')
    if not repo_commit:
        repo_commit = 0
    else:
        repo_commit = repo_commit[0].split(' ')[0].replace(',', '')
    repo_info['repo_commit'] = repo_commit
    # 5、获取repo_topics
    topics_div = tree.xpath('//div[@class="hide-sm hide-md"]/div[@class="my-3"]')
    if not topics_div:
        repo_topics = []
    else:
        a_list = topics_div[0].xpath('./div/a')
        repo_topics = [a.xpath('./text()')[0].strip() for a in a_list]
    repo_info['repo_topics'] = repo_topics

    # 6、获取README.md
    repo_readme = tree.xpath('//article[@class="markdown-body entry-content container-lg"]//text()')
    repo_readme = ''.join(repo_readme)
    repo_info['repo_readme'] = repo_readme

    return repo_info


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
        'User-Agent': UserAgent().edge,
        'Cookie': Cookie
    }
    ssl_context = ssl.create_default_context(
        cafile = certifi.where()
    )
    connector = aiohttp.TCPConnector(ssl = ssl_context, family = socket.AF_INET, happy_eyeballs_delay = None)

    semaphore = asyncio.Semaphore(50) # 限制并发数量

    async with aiohttp.ClientSession(headers = headers, connector = connector) as session:
        # 1、获取所有趋势页面仓库的url
        tasks = [get_repo_url(session, url, semaphore) for url in article_urls]
        results = await asyncio.gather(*tasks)
        repo_infos = [value for page in results for key, value in page.items()]
        repo_infos = keep_latest_repo(repo_infos)

        # 2、获取所有仓库的详细信息
        tasks = [get_repo_detail_info(session, repo_info, semaphore) for repo_info in repo_infos]
        repo_infos = await asyncio.gather(*tasks)

    with open('trending.json', 'w', encoding = 'utf-8') as f:
        json.dump(repo_infos, f, ensure_ascii = False, indent = 4)


def get_trending(languages: list[str] | None = None, time_range: str = 'daily'):
    asyncio.run(get_trending_async(languages, time_range))


if __name__ == '__main__':
    import time
    start = time.time()
    get_trending()
    print(f'耗时：{time.time() - start}秒')

