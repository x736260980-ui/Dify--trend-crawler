# Dify--trend-crawler

本项目是一个基于 **Python 爬虫 + Dify 工作流** 构建的自动化舆情监测工具。通过封装定制化的数据采集接口，并结合大模型的 Web 搜索与文本分析能力，实现对目标消费趋势与早期舆情的精准感知。

> **注：** 项目目前仅个人使用，所以仅针对本地及内网环境进行开发与测试。

---

## 版本演进 v1 → v2 → v3

| 特性 | v1 (Chatflow) | v2 (Agent) | v3 (辩论交叉验证) |
|------|---------------|------------|-------------------|
| 架构模式 | 固定流程 Chatflow | 动态决策 Agent | 双 Agent 辩论 + LLM 裁判 |
| 工作流类型 | Chatflow | Agent | Advanced Chat |
| 模型 | — | DeepSeek Chat | DeepSeek Chat |
| 工具调度 | 预设节点链路 | Agent 自主决定调用顺序 | Agent A / B 各自调度 |
| 分析方式 | 固定流程 | 单次推理 | 多轮交叉验证 |
| 准确性 | 依赖流程设计 | 依赖单次推理质量 | 多方博弈，结果更客观 |
| 历史追溯 | 无 | 无 | 完整辩论过程可追溯 |
| 图表生成 | 需额外节点处理 | Agent 直接调用 ECharts | Agent 直接调用 ECharts |
| 联网搜索 | 不支持 | 集成 Tavily 搜索 | 集成 Tavily 搜索 |

### v1 — Chatflow（已归档）

v1 采用 Dify Chatflow 模式，通过预设节点链路组成固定 DAG 流程，扩展需修改整个 DAG。

### v2 — Agent 模式

v2 从 Chatflow 升级为 **Agent 模式**，由 DeepSeek 模型驱动，动态决策工具调用链路。

```
用户输入视频 ID (抖音纯数字 / B站 BV号)
        │
        ▼
┌─────────────────────────────────────────────┐
│          Dify Agent (DeepSeek Chat)         │
│  ┌─────────────────────────────────────────┐│
│  │  角色：生态与舆情商业分析专家              ││
│  │  - 动态调度工具                          │ │
│  │  - 交叉验证多源数据                      │ │
│  │  - 构建情绪分布图表                      │ │
│  └─────────────────────────────────────────┘ │
│         │          │          │              │
│         ▼          ▼          ▼              │
│  ┌────────┐ ┌────────┐ ┌──────────┐         │
│  │抖音搜索│ │抖音评论│ │Tavily搜索  │         │
│  │  API   │ │  API   │ │ (联网)   │         │
│  └────────┘ └────────┘ └──────────┘         │
│  ┌────────┐ ┌────────┐ ┌──────────┐         │
│  │B站搜索 │ │B站全量 │ │ ECharts  │          │
│  │  API   │ │并发探针 │ │ 饼图渲染 │         │
│  └────────┘ └────────┘ └──────────┘         │
└─────────────────────────────────────────────┘
        │
        ▼
   舆情分析报告 (含情绪分布饼图)
```

### v3 — 辩论交叉验证（当前）

v3 从单 Agent 升级为 **双 Agent 辩论交叉验证架构**，两个独立 Agent 对同一舆情数据进行多轮交叉验证，最后由 LLM 裁判综合评判。

```
用户输入（关键词 / 视频 ID）
        │
        ▼
┌─────────────────────────────────────────────┐
│            辩论交叉验证工作流                  │
│                                              │
│   ┌──────────┐      ┌──────────┐            │
│   │  Agent A  │      │  Agent B  │           │
│   │  (正方)   │◄────►│  (反方)   │           │
│   └────┬─────┘      └────┬─────┘            │
│        │                  │                  │
│        ▼                  ▼                  │
│   ┌────────────────────────────────────┐     │
│   │         LLM 裁判 (最终裁决)         │     │
│   └────────────────────────────────────┘     │
│                                              │
│   ← ← ← 多轮循环 (可配置轮数) ← ← ←        │
└─────────────────────────────────────────────┘
        │
        ▼
   最终舆情分析报告
```

双 Agent 在辩论过程中可调用的 API 服务：

| API | 功能 |
|-----|------|
| `dy搜索api` | 抖音视频搜索（浏览器模拟） |
| `dy评论api` | 抖音评论抓取 |
| `bilibili_ 搜索api` | B站视频搜索 |
| `bilibili_ 评论api` | B站评论/弹幕抓取 |
| `Tavily 搜索` | 联网搜索（封装为简易工作流调用） |

#### 工作流节点

| 节点 | 作用 |
|------|------|
| 用户输入 | 接收关键词或视频 ID |
| 循环 | 控制辩论轮次 |
| Agent A | 正方观点，对数据进行第一轮分析 |
| Agent B | 反方观点，对 A 的分析进行质询与补充 |
| LLM 裁判 | 综合 A 和 B 的辩论内容，给出最终评判 |
| 条件分支 | 判断是否达到最大轮次，决定继续辩论或退出 |
| 代码节点 | 清洗 Agent 输出中的 `<think>` 标签（详见下方说明） |
| 变量赋值 | 追踪每轮的辩论历史（history_A / history_B） |

> **数据清洗说明**：DeepSeek 输出中会包含 `<think>...</think>` 标签，为保留纯文本内容，工作流中通过代码节点进行清洗。该节点在 Agent A、Agent B、LLM 裁判三处输出后各有一个，代码一致：
>
> ```python
> import re
>
> def main(text: str) -> str:
>     cleaned = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
>     return {"result": cleaned.strip()}
> ```

---

## 项目结构

```
./
├── v1/                           【已归档】
│   └── Chatflow 模式，固定流程 DAG 编排
│
├── v2/                           【Agent 模式】
│   ├── 视频分析助手.yml          # Dify Agent 工作流 (DeepSeek)
│   ├── dy搜索api.py              # 抖音搜索微服务
│   ├── dy评论api.py              # 抖音评论微服务
│   ├── dy搜索schema.yml          # 抖音搜索 OpenAPI Schema
│   ├── dy评论schema.yml          # 抖音评论 OpenAPI Schema
│   ├── bilibili_ 搜索api.py      # B站搜索微服务
│   ├── bilibili_ 评论api.py      # B站评论微服务
│   ├── bilibili_ 搜索schema.yml  # B站搜索 OpenAPI Schema
│   ├── bilibili_ 评论schema.yml  # B站评论 OpenAPI Schema
│   
│
├── v3/                           【辩论交叉验证 ← 当前】
│   ├── （舆情检索分析）辩论交叉验证.yml  # 核心：Dify 辩论工作流
│   ├── dy搜索api.py              # 抖音搜索微服务
│   ├── dy评论api.py              # 抖音评论微服务
│   ├── dy搜索schema.yml          # 抖音搜索 OpenAPI Schema
│   ├── dy评论schema.yml          # 抖音评论 OpenAPI Schema
│   ├── bilibili_ 搜索api.py      # B站搜索微服务
│   ├── bilibili_ 评论api.py      # B站评论微服务
│   ├── bilibili_ 搜索schema.yml  # B站搜索 OpenAPI Schema
│   ├── bilibili_ 评论schema.yml  # B站评论 OpenAPI Schema
│
└── README.md                     
```

---

## 技术栈

- **Dify Workflow** — Chatflow / Agent / Advanced Chat 流程编排
- **DeepSeek Chat** — 驱动 Agent 决策与 LLM 裁判
- **FastAPI** — 各微服务 API 框架
- **DrissionPage** — 抖音浏览器模拟（绕过搜索风控）
- **httpx / aiohttp** — B站 API 请求与并发数据拉取

## 环境变量

抖音服务需要配置 `.env` 文件：

```env
DY_COOKIES=your_douyin_cookies_here
```

> 抖音平台的搜索风控较为严格，这里采用本地浏览器模拟（Chrome 远程调试模式）代替。评论拉取参考了 [cv-cat/DouYin_Spider](https://github.com/cv-cat/DouYin_Spider) 的代码。

> Tavily 搜索作为工具给 Agent 调用会报错，这里封装为简易工作流后再次调用。

---

## 快速开始（v3）

### 1. 启动微服务

先进入 v3 目录，启动 Chrome 远程调试模式（端口 9222），然后分别启动各服务：

```bash
cd v3

# B站服务
python "bilibili_ 搜索api.py"
python "bilibili_ 评论api.py"

# 抖音服务（需要 Chrome）
python "dy搜索api.py"
python "dy评论api.py"
```

### 2. 导入 Dify 工作流

- 打开 Dify 控制台
- 导入 `v3/（舆情检索分析）辩论交叉验证.yml`
- 配置各工具对应的微服务地址

### 3. 使用

在 Dify 对话界面输入关键词即可开始辩论交叉验证分析。

---

> Tips：各 API 服务使用 FastAPI 独立部署，未合并为一个服务。这是为了保持复用性和拆解性，方便后续升级时单独修改，避免牵一发而动全身。

⚠️ **免责声明**：本项目仅供学术研究、分析逻辑验证及大模型工程化学习使用。请严格遵守目标平台的相关协议与反爬虫规范，合理控制请求频次，禁止用于任何非法数据采集或商业牟利活动。

📄 **开源协议**：MIT License
