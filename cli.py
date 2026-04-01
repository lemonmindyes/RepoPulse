import sys

from rich.console import Console, Group
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box


_STDOUT_ENCODING = (getattr(sys.stdout, "encoding", "") or "").lower()
_USE_ASCII_LABELS = "gbk" in _STDOUT_ENCODING or "cp936" in _STDOUT_ENCODING
TITLE_PREFIX = (
    "GitHub Trending Topics" if _USE_ASCII_LABELS else "🔥 GitHub Trending Topics"
)
TOPIC_PREFIX = "Topic" if _USE_ASCII_LABELS else "🔥"
STAR_LABEL = "Stars" if _USE_ASCII_LABELS else "⭐ Stars"
TREND_LABEL_PREFIX = "Trend" if _USE_ASCII_LABELS else "🚀"
HISTORY_PREFIX = "Trend" if _USE_ASCII_LABELS else "📈"


def print_topics_cli_rich(
    data: dict,
    *,
    top_k_topics: int = 5,
    top_k_repos: int = 5,
    time_range: str = "daily",
):
    console = Console(record=True, force_terminal=True, width=120)

    # 按热度排序
    topics = sorted(data.items(), key=lambda x: x[1]["heat"], reverse=True)[
        :top_k_topics
    ]

    console.print(
        Panel(
            Text(TITLE_PREFIX, justify="center", style="bold white"),
            style="bold cyan",
            padding=(1, 2),
        )
    )

    for topic, info in topics:
        heat = info["heat"]
        repo_count = info["repo_count"]
        avg_score = info["avg_score"]

        # 🔥 Heat 颜色映射
        if heat >= 70:
            heat_style = "bold red"
        elif heat >= 50:
            heat_style = "bold orange3"
        else:
            heat_style = "bold yellow"

        header = Text()
        header.append(f"{TOPIC_PREFIX} {topic}\n", style="bold magenta")
        header.append(f"Heat: ", style="dim")
        header.append(f"{heat:.2f}", style=heat_style)
        header.append("   Repos: ", style="dim")
        header.append(str(repo_count), style="bold white")
        header.append("   AvgScore: ", style="dim")
        header.append(f"{avg_score:.3f}", style="bold green")

        console.print(
            Panel(
                header,
                style="bright_black",
                padding=(1, 2),
            )
        )

        table = Table(
            box=box.MINIMAL_DOUBLE_HEAD,
            show_edge=False,
            header_style="bold cyan",
        )

        table.add_column("#", justify="right", style="dim", width=3)
        table.add_column("Repository", style="bold white", min_width=28)
        table.add_column("Lang", justify="center", style="green")
        table.add_column(STAR_LABEL, justify="right")
        table.add_column(f"{TREND_LABEL_PREFIX} {time_range}", justify="right")
        table.add_column("Score", justify="right", style="cyan")

        # Repo 排序：date_range + topic_score
        repos = sorted(
            info["repos"],
            key=lambda r: (
                float(r.get("topic_heat_scores", {}).get(topic, 0.0)),
                r["topic_scores"].get(topic, 0.0),
            ),
            reverse=True,
        )[:top_k_repos]

        for i, r in enumerate(repos, 1):
            stars = int(r.get("repo_stars") or 0)
            added_stars = int(r.get("added_stars") or 0)
            lang = r.get("repo_language") or "-"
            score = r["topic_scores"].get(topic, 0.0)

            # daily stars 高亮
            added_stars_style = (
                "bold red"
                if added_stars >= 500
                else "bold orange3"
                if added_stars >= 100
                else "white"
            )

            table.add_row(
                str(i),
                f"{r['repo_author']}/{r['repo_name']}",
                lang,
                f"{stars:,}",
                Text(f"{added_stars}", style=added_stars_style),
                f"{score:.3f}",
            )

        console.print(table)
        console.print()  # 空行


def _sparkline(values: list[float]) -> str:
    if not values:
        return ""

    if _USE_ASCII_LABELS:
        glyphs = " .:-=+*#"
    else:
        glyphs = "▁▂▃▄▅▆▇█"

    low = min(values)
    high = max(values)
    if high == low:
        index = len(glyphs) - 1 if high > 0 else 0
        return glyphs[index] * len(values)

    chart = []
    for value in values:
        pos = int(round((value - low) / (high - low) * (len(glyphs) - 1)))
        chart.append(glyphs[pos])
    return "".join(chart)


def _bar(value: float, max_value: float, width: int = 28) -> str:
    if value <= 0 or max_value <= 0:
        return "-"

    filled = max(1, int(round(value / max_value * width)))
    return "#" * filled


def _print_trend_header_panel(
    console: Console, title: str, summary: list[tuple[str, str, str]]
):
    title_text = Text(title, style="bold cyan")
    summary_text = Text()

    for index, (label, value, style) in enumerate(summary):
        if index > 0:
            summary_text.append("   ", style="dim")
        summary_text.append(f"{label}: ", style="dim")
        summary_text.append(value, style=style)

    console.print(
        Panel.fit(
            Group(title_text, summary_text),
            style="bright_black",
            padding=(0, 1),
        )
    )


def print_topic_trend_cli_rich(
    topic: str,
    history: list[dict],
    *,
    time_range: str,
):
    console = Console(force_terminal=True, width=120)

    if not history:
        console.print(
            Panel(
                Text(
                    f"No history found for topic: {topic}",
                    justify="center",
                    style="bold yellow",
                ),
                style="yellow",
                padding=(1, 2),
            )
        )
        return

    heats = [entry["heat"] for entry in history]
    latest = history[-1]
    peak = max(heats)
    min_heat = min(heats)
    trend_line = _sparkline(heats)

    _print_trend_header_panel(
        console,
        f"{HISTORY_PREFIX} {topic}",
        [
            ("TimeRange", time_range, "bold white"),
            ("Points", str(len(history)), "bold white"),
            ("Latest", f"{latest['heat']:.2f}", "bold green"),
            ("Peak", f"{peak:.2f}", "bold red"),
            ("Min", f"{min_heat:.2f}", "bold yellow"),
        ],
    )
    console.print(
        Panel(
            Text(trend_line, justify="center", style="bold magenta"),
            style="cyan",
            padding=(0, 2),
        )
    )

    table = Table(
        box=box.MINIMAL_DOUBLE_HEAD,
        show_edge=False,
        header_style="bold cyan",
    )
    table.add_column("Time", style="bold white", min_width=12)
    table.add_column("Heat", justify="right", style="bold green")
    table.add_column("Delta", justify="right")
    table.add_column("Repos", justify="right")
    table.add_column("AvgScore", justify="right", style="cyan")
    table.add_column("Chart", style="magenta")

    max_heat = max(heats)
    previous_heat = None
    for entry in history:
        heat = entry["heat"]
        if previous_heat is None:
            delta_text = "-"
            delta_style = "dim"
        else:
            delta = heat - previous_heat
            delta_text = f"{delta:+.2f}"
            delta_style = (
                "bold red" if delta > 0 else "bold green" if delta < 0 else "dim"
            )

        table.add_row(
            entry["display_time"],
            f"{heat:.2f}",
            Text(delta_text, style=delta_style),
            str(entry["repo_count"]),
            f"{entry['avg_score']:.3f}",
            _bar(heat, max_heat),
        )
        previous_heat = heat

    console.print(table)
    console.print()


def print_all_topic_trends_cli_rich(
    histories: dict[str, list[dict]],
    *,
    time_range: str,
):
    console = Console(force_terminal=True, width=140)

    if not histories:
        console.print(
            Panel(
                Text(
                    "No stored topic trend history found",
                    justify="center",
                    style="bold yellow",
                ),
                style="yellow",
                padding=(1, 2),
            )
        )
        return

    rows = []
    for topic, history in histories.items():
        latest = history[-1]
        previous = history[-2]["heat"] if len(history) >= 2 else None
        latest_heat = latest["heat"]
        delta = latest_heat - previous if previous is not None else None
        rows.append(
            {
                "topic": topic,
                "latest": latest_heat,
                "delta": delta,
                "peak": max(entry["heat"] for entry in history),
                "repos": latest["repo_count"],
                "avg_score": latest["avg_score"],
                "points": len(history),
                "trend": _sparkline([entry["heat"] for entry in history]),
            }
        )

    rows.sort(key=lambda row: row["latest"], reverse=True)

    _print_trend_header_panel(
        console,
        f"{HISTORY_PREFIX} Topic Trends",
        [
            ("TimeRange", time_range, "bold white"),
            ("Topics", str(len(rows)), "bold white"),
        ],
    )

    table = Table(
        box=box.MINIMAL_DOUBLE_HEAD,
        show_edge=False,
        header_style="bold cyan",
    )
    table.add_column("Topic", style="bold white", min_width=22)
    table.add_column("Latest", justify="right", style="bold green")
    table.add_column("Delta", justify="right")
    table.add_column("Peak", justify="right", style="bold red")
    table.add_column("Repos", justify="right")
    table.add_column("AvgScore", justify="right", style="cyan")
    table.add_column("Points", justify="right")
    table.add_column("Trend", style="magenta", min_width=20)

    for row in rows:
        if row["delta"] is None:
            delta_text = "-"
            delta_style = "dim"
        else:
            delta_text = f"{row['delta']:+.2f}"
            delta_style = (
                "bold red"
                if row["delta"] > 0
                else "bold green"
                if row["delta"] < 0
                else "dim"
            )

        table.add_row(
            row["topic"],
            f"{row['latest']:.2f}",
            Text(delta_text, style=delta_style),
            f"{row['peak']:.2f}",
            str(row["repos"]),
            f"{row['avg_score']:.3f}",
            str(row["points"]),
            row["trend"],
        )

    console.print(table)
    console.print()
