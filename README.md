<div align="center">

![RepoPulse Logo](./assert/logo.png)

</div>

![Python](https://img.shields.io/badge/python-3.12+-blue.svg)
![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)
![Visitors](https://visitor-badge.laobi.icu/badge?page_id=lemonmindyes.RepoPulse)

RepoPulse 是一个 GitHub Trending 仓库分析工具，能够自动抓取 GitHub 上最热门的仓库，并结合仓库名称、描述、标签和 README 进行智能分类，计算出当前最热门的技术话题。

⭐ **如果这个项目对你有帮助，请帮忙点亮 Star 支持作者！你们的支持是我持续更新和改进的动力！**

## 🌟 功能特性

- **自动抓取 GitHub Trending 仓库**：从多个编程语言分类中获取最新的热门仓库
- **智能话题分类**：使用 TF-IDF 算法对仓库进行自动分类
- **热度计算**：基于仓库的多个维度加权计算话题热度
- **美观的终端界面**：使用 Rich 库展示清晰的终端分析结果
- **多语言支持**：支持 Python、Go、C、C++ 等多种编程语言的仓库
- **异步爬取**：使用 asyncio 和 aiohttp 实现高效并发爬取，大幅提升数据获取速度
- **代理支持**：支持通过代理访问 GitHub，默认配置为 http://127.0.0.1:7890

## 📊 话题分类

项目目前支持以下技术话题分类：

- **LLM_Infra**: 大语言模型基础设施
- **Multimodal_AI**: 多模态人工智能
- **Agent_MCP**: 智能代理和模型上下文协议
- **Database_Storage**: 数据库和存储系统
- **System_Kernel**: 系统内核开发
- **Embedded_Firmware**: 嵌入式系统和固件
- **Networking_Security**: 网络安全
- **DevTool_Testing**: 开发工具和测试
- **CLI_Editor**: 命令行工具和编辑器
- **WebApp_Monitoring**: Web 应用和监控
- **Game_Physics**: 游戏引擎和物理引擎
- **Collection_Edu**: 教程和教育资源
- **FinTech**: 金融科技

## 🛠️ 安装

### 依赖要求

```bash
pip install lxml scikit-learn rich aiohttp certifi
```

### 安装步骤

1. 克隆项目：
```bash
git clone https://github.com/lemonmindyes/RepoPulse
cd RepoPulse
```

2. 安装依赖：
```bash
pip install -r requirements.txt
```

3. 添加 Cookie，并可选配置 GitHub Token（推荐）
```bash
add Cookie in config.py

# optional but recommended for faster crawling
add GitHubToken in config.py
```

也可以不写入 `config.py`，而是通过环境变量传入 `GITHUB_TOKEN`。

如果项目根目录没有 requirements.txt 文件，可以手动安装依赖：
```bash
pip install lxml scikit-learn rich aiohttp certifi
```

## 🚀 使用方法

### 直接运行

```bash
python main.py
```

推荐使用 `GITHUB_TOKEN` 启动，这样 `crawler.py` 会默认走 GitHub GraphQL 批量接口，速度明显快于逐仓库 HTML 抓取：

```bash
$env:GITHUB_TOKEN="your_token"
python main.py
```

如果没有 `GITHUB_TOKEN`，程序会自动回退到较慢但兼容的 HTML 抓取模式。

### 命令行参数

你可以使用以下命令行参数来自定义分析：

- `--time-range`: 设置分析时间范围，可选值为 `daily` (每日)、`weekly` (每周)、`monthly` (每月)，默认为 `daily`
- `--languages`: 指定要分析的编程语言列表，默认为 `python c++ c java javascript typescript go rust shell`
- `--top-k-topics`: 显示最热门的 K 个主题，默认为 5
- `--top-k-repos`: 显示最热门的 K 个仓库，默认为 5

例如：

```bash
# 分析每日趋势，仅包含Python和Go语言
python main.py --time-range daily --languages python go

# 分析每周趋势，包含多种语言
python main.py --time-range weekly --languages python java javascript

# 显示最热门的 K 个主题
python main.py --top-k-topics 5

# 显示最热门的 K 个仓库
python main.py --top-k-repos 5
```

### 各模块功能

- **crawler.py**: 抓取 GitHub Trending 仓库数据，默认优先使用 GitHub GraphQL 批量接口，无 token 时自动回退到 HTML 抓取
- **analysis.py**: 分析仓库并进行话题分类
- **topic.py**: 计算话题热度
- **cli.py**: 在终端中展示结果
- **main.py**: 主程序入口

## 📁 项目结构

```
RepoPulse/
├── main.py          # 主程序入口
├── crawler.py       # GitHub Trending 仓库爬虫
├── analysis.py      # 仓库分析与话题分类
├── topic.py         # 话题热度计算
├── config.py        # 配置文件
├── cli.py           # 终端界面展示
├── trending.json    # 抓取的仓库数据存储
└── README.md        # 项目说明文档
```

## 🔍 工作原理

1. **数据抓取**：从 GitHub Trending 页面抓取热门仓库列表，并优先通过 GitHub GraphQL 批量获取仓库详情
2. **文本分析**：使用 TF-IDF 算法分析仓库名称、描述、标签和 README
3. **话题分类**：将仓库归类到预定义的技术话题
4. **热度计算**：结合增长、动量、规模和活跃度等信号计算话题热度
5. **结果展示**：在终端中以表格形式展示热门话题和相关仓库

## 🧮 评分公式

当前版本的热点计算分为两层：先算仓库对某个主题的贡献值，再汇总为主题热度。

### 1. 主题归属

仓库不会只强制归到单一主题，而是允许对多个相关主题同时贡献热度。

设某仓库的最佳主题分数为 `best_score`，某主题分数为 `topic_score`，则该仓库会被分配到满足下式的主题中：

```text
topic_score >= max(min_score, best_score * relative_ratio)
```

当前默认参数：

```text
min_score = 0.12
relative_ratio = 0.55
```

这样做的目的是减少“硬单分类”带来的误差，让跨领域仓库能够同时影响多个相关主题。

### 2. 仓库信号

对每个仓库，先计算 5 个基础信号。所有信号都基于当前批次仓库的 `P90` 分位数做归一化，避免极大仓库把分数直接拉爆。

```text
growth_signal = norm(log(1 + added_stars))

momentum_signal = norm(log(1 + added_stars / sqrt(repo_stars + 1)))

scale_signal = norm(log(1 + repo_stars) + 0.6 * log(1 + repo_forks))

activity_signal = norm(log(1 + repo_commit) + 0.7 * log(1 + repo_pr))

issue_pressure = norm(log(1 + repo_issue / (repo_pr + 1)))
```

其中 `norm(x)` 表示：

```text
norm(x) = min(max(x / p90, 0), 1)
```

含义说明：

- `growth_signal`：近期增长强度
- `momentum_signal`：相对爆发性，小仓库短期暴涨时会更明显
- `scale_signal`：项目规模和历史沉淀
- `activity_signal`：近期维护/开发活跃度
- `issue_pressure`：issue 压力，作为轻度惩罚项使用

### 3. 仓库对主题的贡献值

先计算仓库基础强度：

```text
base_signal =
    0.4 * growth_signal
  + 0.25 * momentum_signal
  + 0.2 * scale_signal
  + 0.15 * activity_signal
```

再计算健康因子：

```text
health_factor = 1 - 0.12 * issue_pressure
```

主题匹配强度使用分类器输出的 `topic_score`，并做一个平滑非线性变换：

```text
topic_fit = topic_score ^ 0.7
```

于是单个仓库对某个主题的最终贡献值为：

```text
repo_topic_heat = 100 * topic_fit * base_signal * health_factor
```

这里的改进意图是：

- 既看“最近热不热”，也看“是不是这个主题本身”
- 避免总 star 很大但与主题弱相关的仓库挤占榜单
- 对 issue 压力较高的仓库做轻微降权，而不是一票否决

### 4. 主题总热度

某个主题的总热度为该主题下所有仓库贡献值之和：

```text
topic_heat = Σ repo_topic_heat
```

而 `AvgScore` 不是简单平均，而是按贡献值加权后的主题纯度：

```text
avg_score = Σ(topic_score * repo_topic_heat) / Σ(repo_topic_heat)
```

这意味着：

- `Heat` 高：说明这个主题整体很热
- `AvgScore` 高：说明这个主题下的仓库更“纯”，主题边界更清晰
- 两者一起看，可以区分“泛热度”与“核心热点”

## 📈 输出示例

运行程序后，你将看到类似以下的输出：

```
╭──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│                                                                                                                      │
│                                              🔥 GitHub Trending Topics                                               │
│                                                                                                                      │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
╭──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│                                                                                                                      │
│  🔥 DevTool_Testing                                                                                                  │
│  Heat: 240.31   Repos: 39   AvgScore: 0.172                                                                          │
│                                                                                                                      │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
   # │ Repository                   │    Lang    │ ⭐ Stars │ 🚀 daily │ Score
═════╪══════════════════════════════╪════════════╪══════════╪══════════╪═══════
   1 │ google-ai-edge/mediapipe     │    C++     │   33,309 │      170 │ 0.123
   2 │ Open-Dev-Society/OpenStock   │ TypeScript │    7,498 │       88 │ 0.122
   3 │ rustfs/rustfs                │    Rust    │   19,876 │       78 │ 0.180
   4 │ rustdesk/rustdesk            │    Rust    │  105,848 │       57 │ 0.243
   5 │ jesseduffield/lazydocker     │     Go     │   49,217 │       41 │ 0.207

╭──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│                                                                                                                      │
│  🔥 Agent_MCP                                                                                                        │
│  Heat: 162.43   Repos: 19   AvgScore: 0.289                                                                          │
│                                                                                                                      │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
   # │ Repository                   │    Lang    │ ⭐ Stars │ 🚀 daily │ Score
═════╪══════════════════════════════╪════════════╪══════════╪══════════╪═══════
   1 │ obra/superpowers             │   Shell    │   26,803 │     1406 │ 0.317
   2 │ anthropics/skills            │   Python   │   43,502 │     1247 │ 0.247
   3 │ eigent-ai/eigent             │ TypeScript │    7,964 │      703 │ 0.408
   4 │ iOfficeAI/AionUi             │ TypeScript │    4,570 │      592 │ 0.271
   5 │ anthropics/claude-code       │   Shell    │   57,434 │      312 │ 0.240

╭──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│                                                                                                                      │
│  🔥 Database_Storage                                                                                                 │
│  Heat: 98.03   Repos: 14   AvgScore: 0.226                                                                           │
│                                                                                                                      │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
   # │ Repository                   │ Lang │ ⭐ Stars │ 🚀 daily │ Score
═════╪══════════════════════════════╪══════╪══════════╪══════════╪═══════
   1 │ juicedata/juicefs            │  Go  │   12,987 │      235 │ 0.255
   2 │ tursodatabase/turso          │ Rust │   16,495 │       47 │ 0.280
   3 │ tursodatabase/libsql         │  C   │   16,135 │       39 │ 0.199
   4 │ AutoMQ/automq                │ Java │    9,271 │       25 │ 0.168
   5 │ chroma-core/chroma           │ Rust │   25,508 │       22 │ 0.172

╭──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│                                                                                                                      │
│  🔥 LLM_Infra                                                                                                        │
│  Heat: 97.78   Repos: 13   AvgScore: 0.171                                                                           │
│                                                                                                                      │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
   # │ Repository                   │  Lang  │ ⭐ Stars │ 🚀 daily │ Score
═════╪══════════════════════════════╪════════╪══════════╪══════════╪═══════
   1 │ google/langextract           │ Python │   21,394 │      445 │ 0.198
   2 │ ultralytics/ultralytics      │ Python │   51,861 │      234 │ 0.167
   3 │ Automattic/harper            │  Rust  │    9,223 │      193 │ 0.114
   4 │ ggml-org/whisper.cpp         │  C++   │   45,841 │       60 │ 0.147
   5 │ tracel-ai/burn               │  Rust  │   13,995 │       59 │ 0.262

╭──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│                                                                                                                      │
│  🔥 WebApp_Monitoring                                                                                                │
│  Heat: 93.26   Repos: 14   AvgScore: 0.217                                                                           │
│                                                                                                                      │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
   # │ Repository                         │    Lang    │ ⭐ Stars │ 🚀 daily │ Score
═════╪════════════════════════════════════╪════════════╪══════════╪══════════╪═══════
   1 │ afkarxyz/SpotiFLAC                 │ TypeScript │    3,343 │      255 │ 0.103
   2 │ apify/crawlee                      │ TypeScript │   21,136 │       86 │ 0.246
   3 │ jumpserver/jumpserver              │   Python   │   29,561 │       66 │ 0.262
   4 │ iced-rs/iced                       │    Rust    │   29,109 │       19 │ 0.133
   5 │ tangyoha/telegram_media_downloader │ JavaScript │    4,736 │       18 │ 0.224
```

## 📊 结果解读

根据 RepoPulse 的分析结果，您可以参考以下解读来理解不同指标的含义：

| Heat | AvgScore | 含义                 |
| ---- | -------- | ------------------ |
| 高    | 高        |  🔥 核心热点（又热又纯）  |
| 高    | 低        |  🌊 泛热度（热但边界模糊） |
| 低    | 高        |  🌱 小而美 / 新兴方向  |
| 低    | 低        |  🧊 噪声或过时方向     |

- **Heat（热度）**：表示该话题下的仓库总体关注度，数值越高代表整体热度越高。
- **AvgScore（平均分数）**：表示该话题下仓库的平均质量或专注度，分数高意味着话题内的仓库更加专业化或纯粹。

通过这两个指标的组合，您可以快速识别当前 GitHub 上的热门技术趋势，区分真正的技术热点和短暂的流行话题。

## 🤝 贡献

欢迎提交 Issue 和 Pull Request 来帮助改进这个项目！

## 📄 许可证

本项目采用 Apache 2.0 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 📋 Todo List

以下是我们计划在未来版本中实现的功能和改进:

### 🚀 核心功能增强
- [ ] **更精准的话题分类算法** - 改进TF-IDF算法，尝试使用更先进的NLP模型如BERT进行文本分析
- [ ] **历史趋势追踪** - 存储历史数据，提供话题热度变化的趋势图表
- [ ] **自定义话题分类** - 允许用户定义自己的话题分类规则和关键词
- [x] **多维度排序算法** - 已结合 fork、issue、PR、commit 等多维信号改进热点计算

### 🌐 数据源扩展
- [ ] **多平台支持** - 扩展支持GitLab、Bitbucket等其他代码托管平台
- [ ] **实时数据更新** - 提供实时监控模式，定时刷新数据

### 🎨 用户体验优化
- [ ] **Web界面** - 构建可视化Web界面，使用Flask/Django展示结果
- [ ] **交互式终端界面** - 使用Textual等库创建更丰富的终端交互体验
- [ ] **导出功能** - 支持导出分析结果为JSON、CSV、PDF等格式
- [ ] **国际化支持** - 添加多语言支持，包括中文、英文等

### 🔧 技术改进
- [ ] **性能优化** - 进一步优化爬虫效率，减少请求时间
- [ ] **缓存机制** - 实现本地缓存，避免重复请求相同数据
- [ ] **错误处理增强** - 更完善的异常处理和重试机制
- [ ] **代理池管理** - 实现动态代理切换，提高爬取成功率

### 📊 数据分析增强
- [ ] **开发者洞察** - 分析热门仓库的贡献者和社区活跃度
- [ ] **技术栈预测** - 基于仓库内容预测主要使用的技术栈
- [ ] **相似仓库推荐** - 基于话题分类推荐相似的热门仓库

## 🙏 鸣谢

- 感谢所有开源贡献者
- 使用了以下优秀的开源库：
  - [lxml](https://lxml.de/) - XML 和 HTML 处理库
  - [scikit-learn](https://scikit-learn.org/) - 机器学习库
  - [rich](https://rich.readthedocs.io/) - 终端美化库
  - [aiohttp](https://aiohttp.readthedocs.io/) - 异步 HTTP 客户端/服务器库
  - [certifi](https://certifiio.readthedocs.io/) - SSL 证书包
