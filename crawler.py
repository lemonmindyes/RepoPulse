import asyncio
import certifi
import os
import json
import re
import socket
import ssl

import aiohttp
from lxml import etree

import config


PROXY_URL = "http://127.0.0.1:7890"
LIST_PAGE_CONCURRENCY = 10
DETAIL_PAGE_CONCURRENCY = 65
REQUEST_RETRIES = 2
REQUEST_RETRY_DELAY = 0.25
GRAPHQL_BATCH_SIZE = 10
GRAPHQL_CONCURRENCY = 4
GITHUB_GRAPHQL_URL = "https://api.github.com/graphql"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36"
)
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN") or getattr(config, "GitHubToken", "")


def keep_latest_repo(data: list[dict]) -> list[dict]:
    seen = set()
    result = []

    for item in data:
        repo_path = (item["repo_author"], item["repo_name"])

        if repo_path not in seen:
            result.append(item)
            seen.add(repo_path)

    return result


def _parse_compact_count(raw: str | None) -> str | None:
    if not raw:
        return None

    normalized = " ".join(raw.replace(",", "").split()).lower()
    match = re.search(r"(\d+(?:\.\d+)?)\s*([km])?\+?", normalized)
    if not match:
        return None

    value = float(match.group(1))
    suffix = match.group(2)

    if suffix == "k":
        value *= 1000
    elif suffix == "m":
        value *= 1000000

    return str(int(value))


def _extract_repo_nav_counts(tree: etree._Element, repo_path: str) -> dict[str, str]:
    counts = {
        "repo_issue": "0",
        "repo_pr": "0",
        "repo_commit": "0",
    }
    anchors = tree.xpath('//nav[@aria-label="Repository"]//a[@href]')

    for anchor in anchors:
        href = anchor.get("href", "")
        if repo_path not in href:
            continue

        candidates = anchor.xpath("@aria-label | .//@aria-label | .//text()")
        count = None
        for candidate in candidates:
            count = _parse_compact_count(candidate)
            if count is not None:
                break
        if count is None:
            continue

        if "/issues" in href:
            counts["repo_issue"] = count
        elif "/pulls" in href:
            counts["repo_pr"] = count
        elif "/commits" in href:
            counts["repo_commit"] = count

    return counts


def _build_graphql_batch_query(batch: list[dict]) -> str:
    query_parts = ["query {"]

    for index, repo in enumerate(batch):
        owner = json.dumps(repo["repo_author"])
        name = json.dumps(repo["repo_name"])
        query_parts.append(
            f"""
repo_{index}: repository(owner: {owner}, name: {name}) {{
  description
  primaryLanguage {{ name }}
  stargazerCount
  forkCount
  openIssues: issues(states: OPEN) {{ totalCount }}
  openPullRequests: pullRequests(states: OPEN) {{ totalCount }}
  defaultBranchRef {{
    target {{
      ... on Commit {{
        history(first: 1) {{ totalCount }}
      }}
    }}
  }}
  repositoryTopics(first: 20) {{
    nodes {{ topic {{ name }} }}
  }}
  readme_md: object(expression: \"HEAD:README.md\") {{
    ... on Blob {{ isBinary text }}
  }}
  readme_md_upper: object(expression: \"HEAD:README.MD\") {{
    ... on Blob {{ isBinary text }}
  }}
  readme_md_lower: object(expression: \"HEAD:readme.md\") {{
    ... on Blob {{ isBinary text }}
  }}
  readme_rst: object(expression: \"HEAD:README.rst\") {{
    ... on Blob {{ isBinary text }}
  }}
  readme_txt: object(expression: \"HEAD:README.txt\") {{
    ... on Blob {{ isBinary text }}
  }}
  readme_plain: object(expression: \"HEAD:README\") {{
    ... on Blob {{ isBinary text }}
  }}
}}
"""
        )

    query_parts.append("}")
    return "\n".join(query_parts)


def _pick_graphql_readme(repo_node: dict) -> str:
    candidates = [
        repo_node.get("readme_md"),
        repo_node.get("readme_md_upper"),
        repo_node.get("readme_md_lower"),
        repo_node.get("readme_rst"),
        repo_node.get("readme_txt"),
        repo_node.get("readme_plain"),
    ]

    for candidate in candidates:
        if not candidate or candidate.get("isBinary"):
            continue
        text = candidate.get("text")
        if text:
            return text

    return ""


def _apply_graphql_repo_data(repo_info: dict, repo_node: dict):
    repo_info["repo_describe"] = repo_node.get("description") or repo_info.get(
        "repo_describe", ""
    )

    primary_language = repo_node.get("primaryLanguage") or {}
    repo_info["repo_language"] = primary_language.get("name") or repo_info.get(
        "repo_language", ""
    )

    repo_info["repo_stars"] = str(
        repo_node.get("stargazerCount") or repo_info.get("repo_stars") or 0
    )
    repo_info["repo_forks"] = str(
        repo_node.get("forkCount") or repo_info.get("repo_forks") or 0
    )
    repo_info["repo_issue"] = str(
        (repo_node.get("openIssues") or {}).get("totalCount") or 0
    )
    repo_info["repo_pr"] = str(
        (repo_node.get("openPullRequests") or {}).get("totalCount") or 0
    )

    commit_history = (
        (repo_node.get("defaultBranchRef") or {}).get("target") or {}
    ).get("history") or {}
    repo_info["repo_commit"] = str(commit_history.get("totalCount") or 0)

    repo_topics = []
    for node in (repo_node.get("repositoryTopics") or {}).get("nodes", []):
        topic = (node.get("topic") or {}).get("name")
        if topic:
            repo_topics.append(topic)
    repo_info["repo_topics"] = repo_topics
    repo_info["repo_readme"] = _pick_graphql_readme(repo_node)


async def _fetch_graphql_batch(
    session: aiohttp.ClientSession,
    batch: list[dict],
    semaphore: asyncio.Semaphore,
) -> list[dict]:
    query = _build_graphql_batch_query(batch)
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    payload = {"query": query}
    last_error = None

    for attempt in range(REQUEST_RETRIES):
        try:
            async with semaphore:
                async with session.post(
                    GITHUB_GRAPHQL_URL,
                    json=payload,
                    headers=headers,
                    proxy=PROXY_URL,
                ) as response:
                    response.raise_for_status()
                    body = await response.json()
        except (
            aiohttp.ClientError,
            asyncio.TimeoutError,
            OSError,
        ) as exc:
            last_error = exc
            if attempt == REQUEST_RETRIES - 1:
                raise
            await asyncio.sleep(REQUEST_RETRY_DELAY * (attempt + 1))
            continue

        if body.get("errors"):
            raise RuntimeError(f"GitHub GraphQL error: {body['errors']}")

        data = body.get("data") or {}
        enriched = []
        for index, repo_info in enumerate(batch):
            repo_node = data.get(f"repo_{index}")
            if repo_node:
                _apply_graphql_repo_data(repo_info, repo_node)
            else:
                repo_info.setdefault("repo_issue", "0")
                repo_info.setdefault("repo_pr", "0")
                repo_info.setdefault("repo_commit", "0")
                repo_info.setdefault("repo_topics", [])
                repo_info.setdefault("repo_readme", "")
            enriched.append(repo_info)
        return enriched

    raise last_error


async def _fetch_text(
    session: aiohttp.ClientSession,
    url: str,
    semaphore: asyncio.Semaphore,
) -> str:
    last_error = None

    for attempt in range(REQUEST_RETRIES):
        try:
            async with semaphore:
                async with session.get(url, proxy=PROXY_URL) as response:
                    return await response.text()
        except (
            aiohttp.ClientError,
            asyncio.TimeoutError,
            OSError,
        ) as exc:
            last_error = exc
            if attempt == REQUEST_RETRIES - 1:
                raise
            await asyncio.sleep(REQUEST_RETRY_DELAY * (attempt + 1))

    raise last_error


async def _get_repo_details_from_api(
    session: aiohttp.ClientSession,
    repo_infos: list[dict],
) -> list[dict]:
    graphql_semaphore = asyncio.Semaphore(GRAPHQL_CONCURRENCY)
    batches = [
        repo_infos[index : index + GRAPHQL_BATCH_SIZE]
        for index in range(0, len(repo_infos), GRAPHQL_BATCH_SIZE)
    ]
    tasks = [
        asyncio.create_task(_fetch_graphql_batch(session, batch, graphql_semaphore))
        for batch in batches
    ]
    results = await asyncio.gather(*tasks)
    return [repo_info for batch in results for repo_info in batch]


async def _get_repo_details_from_html(
    session: aiohttp.ClientSession,
    repo_infos: list[dict],
    detail_semaphore: asyncio.Semaphore,
) -> list[dict]:
    detail_tasks = [
        asyncio.create_task(get_repo_detail_info(session, repo_info, detail_semaphore))
        for repo_info in repo_infos
    ]
    return [await task for task in asyncio.as_completed(detail_tasks)]


async def get_repo_url(
    session: aiohttp.ClientSession, url: str, semaphore: asyncio.Semaphore
):
    html = await _fetch_text(session, url, semaphore)

    tree = etree.HTML(html)
    articles = tree.xpath('//div[@class="Box"]/div[2]/article')

    repo_urls = {}

    for article in articles:
        repo_author = (
            article.xpath("./h2/a/span/text()")[0].replace(" /", "").strip()
        )  # 仓库作者
        repo_name = "".join(article.xpath("./h2/a/text()")).strip()  # 仓库名称
        # 仓库描述
        if not article.xpath("./p/text()"):
            repo_describe = ""
        else:
            repo_describe = article.xpath("./p/text()")[0].strip()
        # 仓库语言
        repo_language = article.xpath(
            'string(.//span[@itemprop="programmingLanguage"])'
        ).strip()
        repo_stars = (
            article.xpath("./div[2]/a[1]/text()")[0].strip().replace(",", "")
        )  # 仓库 stars
        repo_forks = (
            article.xpath("./div[2]/a[2]/text()")[0].strip().replace(",", "")
        )  # 仓库 forks
        # 今日 stars
        texts = article.xpath(
            './div[2]/span[@class="d-inline-block float-sm-right"]/text()'
        )
        raw = "".join(texts).strip()
        added_stars = raw.replace(",", "").split()[0]

        # 保存信息
        repo_urls[f"{repo_author}/{repo_name}"] = {
            "repo_author": repo_author,
            "repo_name": repo_name,
            "repo_describe": repo_describe,
            "repo_language": repo_language,
            "repo_stars": repo_stars,
            "repo_forks": repo_forks,
            "added_stars": added_stars,
            "repo_url": f"https://github.com/{repo_author}/{repo_name}",
        }
    return repo_urls


async def get_repo_detail_info(
    session: aiohttp.ClientSession, repo_info: str, semaphore: asyncio.Semaphore
):
    html = await _fetch_text(session, repo_info["repo_url"], semaphore)
    tree = etree.HTML(html)
    repo_path = repo_info["repo_url"].replace("https://github.com", "")
    repo_counts = _extract_repo_nav_counts(tree, repo_path)

    # 1、获取issue数
    repo_info["repo_issue"] = repo_counts["repo_issue"]

    # 2、获取Pr数
    repo_info["repo_pr"] = repo_counts["repo_pr"]

    # 3、获取commit数
    repo_commit = repo_counts["repo_commit"]
    if repo_commit == "0":
        repo_commit_nodes = tree.xpath(
            '//table[@aria-labelledby="folders-and-files"]/tbody/tr[1]'
            '//span[@class="fgColor-default"]/text()'
        )
        if repo_commit_nodes:
            parsed = _parse_compact_count(repo_commit_nodes[0])
            if parsed is not None:
                repo_commit = parsed
    repo_info["repo_commit"] = repo_commit

    # 4、获取repo_topics
    repo_topics = tree.xpath(
        '//div[contains(@class, "hide-sm") and contains(@class, "hide-md")]/div[@class="my-3"]//a/text()'
    )
    repo_topics = [topic.strip() for topic in repo_topics if topic.strip()]
    repo_info["repo_topics"] = repo_topics

    # 5、获取README.md
    repo_info["repo_readme"] = tree.xpath(
        'string(//article[contains(@class, "markdown-body")])'
    )

    return repo_info


async def get_trending_async(
    languages: list[str] | None = None, time_range: str = "daily"
):
    if languages is None:
        # 预置一些常见语言的趋势页面
        article_urls = [
            "https://github.com/trending",  # 默认 trending页面
            f"https://github.com/trending/python?since={time_range}",  # python trending页面
            f"https://github.com/trending/c++?since={time_range}",  # c++ trending页面
            f"https://github.com/trending/c?since={time_range}",  # c trending页面
            f"https://github.com/trending/java?since={time_range}",  # java trending页面
            f"https://github.com/trending/javascript?since={time_range}",  # javascript trending页面
            f"https://github.com/trending/typescript?since={time_range}",  # typescript trending页面
            f"https://github.com/trending/go?since={time_range}",  # go trending页面
            f"https://github.com/trending/rust?since={time_range}",  # rust trending页面
            f"https://github.com/trending/shell?since={time_range}",  # shell trending页面
        ]
    else:
        article_urls = []
        for language in dict.fromkeys(languages):
            article_urls.append(
                f"https://github.com/trending/{language}?since={time_range}"
            )

    headers = {"User-Agent": USER_AGENT, "Cookie": config.Cookie}
    ssl_context = ssl.create_default_context(cafile=certifi.where())
    connector = aiohttp.TCPConnector(
        ssl=ssl_context,
        family=socket.AF_INET,
        happy_eyeballs_delay=None,
        limit=DETAIL_PAGE_CONCURRENCY,
        ttl_dns_cache=300,
    )

    list_semaphore = asyncio.Semaphore(LIST_PAGE_CONCURRENCY)
    detail_semaphore = asyncio.Semaphore(DETAIL_PAGE_CONCURRENCY)

    async with aiohttp.ClientSession(
        headers=headers,
        connector=connector,
    ) as session:
        seen_repo_paths = set()
        list_tasks = [
            asyncio.create_task(get_repo_url(session, url, list_semaphore))
            for url in article_urls
        ]

        if GITHUB_TOKEN:
            # 1、有 token 时先收集唯一 repo，再走 GraphQL 批量详情接口
            repo_infos = []

            for list_task in asyncio.as_completed(list_tasks):
                page_repo_infos = await list_task
                for repo_info in page_repo_infos.values():
                    repo_path = (repo_info["repo_author"], repo_info["repo_name"])
                    if repo_path in seen_repo_paths:
                        continue
                    seen_repo_paths.add(repo_path)
                    repo_infos.append(repo_info)

            try:
                repo_infos = await _get_repo_details_from_api(session, repo_infos)
            except (
                aiohttp.ClientError,
                asyncio.TimeoutError,
                OSError,
                RuntimeError,
            ):
                repo_infos = await _get_repo_details_from_html(
                    session, repo_infos, detail_semaphore
                )
        else:
            # 1、无 token 时保留 HTML 流水线抓取，避免性能回退
            detail_tasks = []

            for list_task in asyncio.as_completed(list_tasks):
                page_repo_infos = await list_task
                for repo_info in page_repo_infos.values():
                    repo_path = (repo_info["repo_author"], repo_info["repo_name"])
                    if repo_path in seen_repo_paths:
                        continue
                    seen_repo_paths.add(repo_path)
                    detail_tasks.append(
                        asyncio.create_task(
                            get_repo_detail_info(session, repo_info, detail_semaphore)
                        )
                    )

            repo_infos = [await task for task in asyncio.as_completed(detail_tasks)]

    with open("trending.json", "w", encoding="utf-8") as f:
        json.dump(repo_infos, f, ensure_ascii=False, separators=(",", ":"))


def get_trending(languages: list[str] | None = None, time_range: str = "daily"):
    asyncio.run(get_trending_async(languages, time_range))


if __name__ == "__main__":
    import time

    start = time.time()
    get_trending()
    print(f"耗时：{time.time() - start}秒")
