from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box


def print_topics_cli_rich(
    data: dict,
    *,
    top_k_topics: int = 5,
    top_k_repos: int = 5,
    time_range: str = 'daily'
):
    console = Console(
        record = True,
        force_terminal = True,
        width = 120
    )

    # 按热度排序
    topics = sorted(
        data.items(),
        key = lambda x: x[1]['heat'],
        reverse = True
    )[:top_k_topics]

    console.print(
        Panel(
            Text('🔥 GitHub Trending Topics', justify = 'center', style = 'bold white'),
            style = 'bold cyan',
            padding = (1, 2),
        )
    )

    for topic, info in topics:
        heat = info['heat']
        repo_count = info['repo_count']
        avg_score = info['avg_score']

        # 🔥 Heat 颜色映射
        if heat >= 70:
            heat_style = 'bold red'
        elif heat >= 50:
            heat_style = 'bold orange3'
        else:
            heat_style = 'bold yellow'

        header = Text()
        header.append(f'🔥 {topic}\n', style = 'bold magenta')
        header.append(f'Heat: ', style = 'dim')
        header.append(f'{heat:.2f}', style = heat_style)
        header.append('   Repos: ', style = 'dim')
        header.append(str(repo_count), style = 'bold white')
        header.append('   AvgScore: ', style = 'dim')
        header.append(f'{avg_score:.3f}', style = 'bold green')

        console.print(
            Panel(
                header,
                style = 'bright_black',
                padding = (1, 2),
            )
        )

        table = Table(
            box = box.MINIMAL_DOUBLE_HEAD,
            show_edge = False,
            header_style = 'bold cyan',
        )

        table.add_column('#', justify = 'right', style = 'dim', width = 3)
        table.add_column('Repository', style = 'bold white', min_width = 28)
        table.add_column('Lang', justify = 'center', style = 'green')
        table.add_column('⭐ Stars', justify = 'right')
        table.add_column(f'🚀 {time_range}', justify = 'right')
        table.add_column('Score', justify = 'right', style = 'cyan')

        # Repo 排序：date_range + topic_score
        repos = sorted(
            info['repos'],
            key = lambda r: (
                int(r.get('added_stars') or 0),
                r['topic_scores'].get(topic, 0.0)
            ),
            reverse = True
        )[:top_k_repos]

        for i, r in enumerate(repos, 1):
            stars = int(r.get('repo_stars') or 0)
            added_stars = int(r.get('added_stars') or 0)
            lang = r.get('repo_language') or '-'
            score = r['topic_scores'].get(topic, 0.0)

            # daily stars 高亮
            added_stars_style = (
                'bold red' if added_stars >= 500 else
                'bold orange3' if added_stars >= 100 else
                'white'
            )

            table.add_row(
                str(i),
                f'{r['repo_author']}/{r['repo_name']}',
                lang,
                f'{stars:,}',
                Text(f'{added_stars}', style = added_stars_style),
                f'{score:.3f}',
            )

        console.print(table)
        console.print()  # 空行
    console.save_svg('./repo_pulse.svg', title = 'GitHub Trending Topics')
