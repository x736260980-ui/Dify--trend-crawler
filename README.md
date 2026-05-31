# v4 — 记忆增强·双出口舆情分析系统

> 基于 **Dify Advanced Chat** 构建的第四代舆情分析工作流。在 v3 双 Agent 辩论的基础上，引入**向量记忆检索**、**结构化 JSON 量化**和**双出口报告生成**，实现从"单次分析"到"跨事件记忆积累"的跃迁。

---

## 📈 版本演进总览

| | v1 | v2 | v3 | **v4** |
|:--|:--|:--|:--|:--|
| **架构** | 固定流程 | Agent 自主决策 | 双 Agent 辩论 | **循环辩论 + 记忆系统** |
| **分析方式** | 线性 DAG | 单次推理 | 多轮交叉验证 | **弹性辩论 + JSON 量化** |
| **数据采集** | 手动传入 | Agent 内部调用 | Agent 内部调用 | **独立双 Agent 并行** |
| **历史追溯** | ❌ | ❌ | ✅ 辩论记录 | ✅ 辩论 + **Narrative Memory** |
| **输出** | 纯文本 | 含图表报告 | 含图表报告 | **双出口：共鸣长文 + Obsidian 研报** |
| **状态** | 已归档 | 已归档 | 已归档 | **← 当前版本** |

### v4 核心升级点（vs v3）

| 维度 | v3 | v4 |
|:--|:--|:--|
| **数据采集** | 辩论 Agent 内部调用工具 | 独立的「社媒 Agent」+「网页 Agent」并行采集，采集与分析解耦 |
| **辩论机制** | 固定轮次循环 | **弹性终止**：双方都输出 `0` 才退出（最多 5 轮） |

| **向量记忆** | 无 | ✅ 辩论结束后自动检索历史相似舆情（RAG），注入最终报告 |
| **JSON 量化** | 无 | ✅ 独立 LLM 将辩论结果量化为结构化 JSON（情绪强度、叙事置信度、风险等级） |
| **输出格式** | 单一报告 | **双出口**：共鸣长文（社交媒体发布）+ Obsidian 研报（知识库存档） |
| **记忆归档** | 无 | ✅ JSON → Narrative Memory 压缩 → 本地储存，持续积累向量库素材 |
| **搜索引擎** | Tavily | Tavily + Google 双引擎 |

---

## 🏗️ 架构总览

```
用户输入（关键词 / 视频 ID）
        │
        ▼
   ┌─────────┐
   │  清理    │  初始化：round=1, 清空 history/web_data
   └────┬────┘
        │
        ▼
   "调用工具获取真实舆情数据ing..."
        │
        ├─── 并行 ────────────────────────────────┐
        ▼                                          ▼
┌───────────────┐                      ┌───────────────┐
│  社媒采集 Agent │                      │  网页采集 Agent │
│               │                      │               │
│  · B站视频搜索  │                      │  · Tavily 搜索  │
│  · B站并发探针  │                      │  · Google 搜索  │
│  · 抖音视频搜索 │                      │               │
│  · 抖音评论抓取 │                      │               │
└───────┬───────┘                      └───────┬───────┘
        │  清洗₁                                │  清洗₂
        └───────────────┬───────────────────────┘
                        ▼
                  模板转换（合并）
                        │
                        ▼
               知识库追加 → web_data
                        │
                        ▼
    ┌───────────────────────────────────────────┐
    │              🔄 循环（最多 5 轮）            │
    │                                           │
    │   条件分支：history_A 和 history_B 都含 "0"? │
    │      ├── 是 → 退出循环                     │
    │      └── 否 → 继续辩论                     │
    │                                           │
    │   ┌─────────┐         ┌─────────┐         │
    │   │  LLM A  │         │  LLM B  │         │
    │   │  调查官  │ ──辩论──▶│  风控官  │         │
    │   │ (首轮出  │         │ (逻辑审查│         │
    │   │  报告)   │         │  视角补充)│         │
    │   └────┬────┘         └────┬────┘         │
    │        │ 清洗A              │ 清洗B         │
    │        ▼                    ▼              │
    │   变量赋值A             变量赋值B            │
    │   (→ history_A)        (→ history_B)       │
    │                          round += 1        │
    └───────────────────────────────────────────┘
                        │
                        ▼
                ┌───────────────┐
                │   JSON 量化    │  辩论历史 + 证据池 → 结构化 JSON
                └───────┬───────┘
                        │
              ┌─────────┴─────────┐
              ▼                   ▼
    ┌──────────────┐    ┌────────────────┐
    │  向量检索     │    │  记忆压缩       │
    │  (RAG Agent)  │    │  (Narrative    │
    │  检索历史相似  │    │   Memory)      │
    └──────┬───────┘    └───────┬────────┘
           │                    │
           ▼                    ▼
      similiar 变量         本地储存（memory）
           │
     ┌─────┴──────┐
     ▼            ▼
┌─────────┐  ┌──────────────┐
│ 共鸣长文 │  │ Obsidian 研报 │
│ (社交媒体│  │ (YAML Front  │
│  发布)   │  │  Matter +    │
│         │  │  Mermaid 图)  │
└────┬────┘  └──────┬───────┘
     │              │
     ▼              ▼
  本地储存      HTTP Webhook
```

---
#双LLM交叉对话过程
<img width="2560" height="1246" alt="image" src="https://github.com/user-attachments/assets/b00e79fc-7da7-478e-9e25-d89b785895eb" />

#共鸣报告
<img width="2372" height="1154" alt="屏幕截图_29-5-2026_223021_localhost" src="https://github.com/user-attachments/assets/d080645c-036b-4244-96f8-6d360b91bb72" />

#向量检索召回示例
<img width="2548" height="1169" alt="屏幕截图_30-5-2026_132827_localhost" src="https://github.com/user-attachments/assets/717c5232-806c-41d4-b3b4-8f7bb2bc6df6" />
<img width="2549" height="1229" alt="屏幕截图_30-5-2026_132845_localhost" src="https://github.com/user-attachments/assets/8476a13b-c3ad-485b-a132-c42f9ed3512d" />
（角色）资源分配不平衡，召回两个不同结果

#剖析报告Obsidian储存
<img width="2442" height="1303" alt="image" src="https://github.com/user-attachments/assets/84f37053-151e-4659-b27a-9366a6d44923" />


##案例存储展示
##👉 [案例存储展示](./case)



## 🔑 核心设计解析

### 1. 采集与分析解耦

v3 中辩论 Agent 自己调工具，导致"边采集边分析"，容易出现 Agent 在辩论中途重新搜索、结果不可控的问题。

v4 将采集拆为两个独立 Agent：

| Agent | 职责 | 工具 |
|:--|:--|:--|
| **社媒采集 Agent**「社媒嗅探犬」 | 抖音/B站的视频搜索、评论/弹幕抓取 | B站搜索、B站并发、抖音搜索、抖音评论 |
| **网页采集 Agent**「全网巡洋舰」 | 新闻、长文、官方声明等结构化信息 | Tavily 搜索、Google 搜索 |

两个 Agent 并行执行，各自最多调用 3 次工具，结果合并后写入 `web_data` 证据池，供辩论环节消费。

### 2. 弹性辩论终止

v3 固定跑完所有轮次，v4 引入终止条件：

- LLM A（调查官）和 LLM B（风控官）在每轮发言后，如果认为双方结论已对齐，输出 `0`
- 条件分支节点检查 `history_A` 和 `history_B` 是否都包含 `0`
- **双方都输出 `0` 才退出循环**，确保辩论充分收敛
- 最多 5 轮保底，防止死循环

### 3. 向量记忆系统（RAG）

这是 v4 最大的架构升级。工作流在辩论结束后，自动执行：

```
辩论历史 → JSON 量化 → 向量检索 Agent → 检索历史相似舆情
                                    ↓
                              写入 similiar 变量
                                    ↓
                         注入最终报告（作为参考案例）
```

**向量检索 Agent** 的工作方式：
1. 读取上游 JSON，提取深层逻辑（`core_narratives`）、核心情绪（`main_emotions`）和结构性矛盾（`summary`）
2. 剥离具体表象名词（游戏名、角色名等），生成高密度检索字符串
3. 调用知识库工具，召回最相似的历史舆情案例
4. 结果作为"历史 Narrative Memory"注入最终报告

### 4. JSON 量化层

辩论结束后，独立 LLM 将辩论历史 + 证据池量化为结构化 JSON：

```json
{
  "event_name": "事件核心名称缩写",
  "event_type": "事件类型",
  "summary": "一句话冷酷总结",
  "main_emotions": [{"emotion": "...", "intensity": 0.0}],
  "core_narratives": [{"narrative": "...", "confidence": 0.0}],
  "risk_evolution": [{"stage": "...", "description": "..."}],
  "platform_features": {"bilibili": "...", "douyin": "..."},
  "high_spread_keywords": [],
  "group_conflicts": [],
  "official_response_analysis": {"response_type": "...", "problem": "...", "effect": "..."},
  "strategy_suggestions": [],
  "risk_level": "极危 / 高危 / 中度 / 低度 / 已冷却",
  "similar_cases": []
}
```

**双轨交叉校验规范**：
- 事实与词频维度（情绪、关键词）→ 优先审计原始证据池
- 逻辑与策略维度（叙事、风险演化）→ 必须以辩论历史中达成的共识为准

### 5. 双出口报告

v4 同时生成两份报告，走不同出口：

| 出口 | 报告类型 | 特点 | 输出方式 |
|:--|:--|:--|:--|
| **出口 A** | 共鸣长文 | 社交媒体发布级，无 YAML/Mermaid，纯 Markdown，网感强 | 本地储存 + 对话回复 |
| **出口 B** | Obsidian 研报 | YAML Front Matter + Mermaid 时序图 + 结构化表格，冷峻文风 | HTTP Webhook → 知识库 |

两份报告**并行生成**，互不影响。

### 6. Narrative Memory 归档

JSON 量化结果还会经过"记忆压缩"LLM，转化为高密度 Markdown 记忆文档：

```
# 事件名称

【事件类型】底层分类
【核心摘要】结构性本质（抛弃具体专有名词）
【核心情绪】情绪核心词（每行一个）
【核心 Narrative】抽象为社会学/传播学叙事
【群体心理与冲突】底层原因 + 对立锚点
【风险演化路径】单向箭头链条
【平台阵地特征】传播职能短句
【官方回应判定】操作失败/有效诊断
【高频检索词】空格分隔
【Narrative Archetype】跨界召回锚点
【跨界复用法则】可迁移经验
【风险等级】灾难级/警戒级/常规级
```

这份 Memory 存入本地，持续为向量库积累素材，让系统越用越聪明。

---

## 📊 工作流节点清单

| 节点 | 类型 | 作用 |
|:--|:--|:--|
| 用户输入 | start | 接收关键词或视频 ID |
| 清理 | assigner | 初始化全局变量（round=1, 清空历史/证据池） |
| 数据获取（社媒）| agent | 抖音/B站多维数据采集 |
| 数据获取（网页）| agent | Tavily + Google 全网信息采集 |
| 清洗₁ / 清洗₂ | code | 剥离 `<think>` 标签 |
| 模板转换 | template | 合并两个 Agent 的输出 |
| 知识库追加 | assigner | 将合并数据写入 `web_data` 证据池 |
| 循环 | loop | 控制辩论轮次（最多 5 轮） |
| 条件分支 | if-else | 检查双方是否都输出 `0`，决定是否退出 |
| LLM A | llm | 调查官：首轮出报告，后续轮次回应质疑 |
| LLM B | llm | 风控官：逻辑审查 + 视角补充 |
| 清洗A / 清洗B | code | 剥离 LLM 输出的 `<think>` 标签 |
| 变量赋值 A/B | assigner | 追踪辩论历史 |
| LLM json | llm | 将辩论结果量化为结构化 JSON |
| 向量检索 | agent | 检索历史相似舆情（RAG） |
| 变量赋值（similiar）| assigner | 将检索结果写入全局变量 |
| LLM conclusion | llm | 生成共鸣长文（社交媒体发布级） |
| LLM conclusion123 | llm | 生成 Obsidian 研报（YAML + Mermaid） |
| 本地储存 | tool | 将报告/记忆写入本地文件 |
| HTTP 请求 | http | 通过 Webhook 将研报推送到外部系统 |
| 直接回复 | answer | 向用户输出中间结果或最终报告 |

---

## 🛠️ 依赖服务

| 服务 | 用途 | 工具名 |
|:--|:--|:--|
| B站视频搜索 | 跨分区检索 B 站视频 | `search_videos` |
| B站并发探针 | 批量获取视频元数据、弹幕、评论 | `get_batch_full_bili_data` |
| 抖音视频搜索 | 关键词搜索抖音视频 | `search_douyin_videos` |
| 抖音评论抓取 | 获取视频评论数据 | `fetch_douyin_comments` |
| Tavily 搜索 | 联网搜索（封装为工作流） | `tavily_search` |
| Google 搜索 | Google SERP 搜索 | `google_search` |
| 知识库调用 | 向量数据库相似度检索 | `database_delve` |
| 本地储存 | 数据归档（本地文件） | `post` |
| Webhook | 推送研报到外部系统 | HTTP POST |

---

## 🧹 数据清洗

v4 使用 mimo-v2.5-pro 模型，输出中仍可能包含 `<think>` 标签。工作流中在以下位置各有一个清洗节点，代码一致：

- 社媒采集 Agent 输出后
- 网页采集 Agent 输出后
- LLM A 输出后
- LLM B 输出后
- JSON 量化输出后
- 共鸣长文输出后
- Obsidian 研报输出后

```python
import re

def main(text: str) -> str:
    cleaned = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    return {"result": cleaned.strip()}
```

---

## 📝 变量说明

| 变量名 | 类型 | 说明 |
|:--|:--|:--|
| `round` | integer | 当前辩论轮次，初始值 1，每轮 +1 |
| `history_A` | array[string] | 调查官（LLM A）的历史发言记录 |
| `history_B` | array[string] | 风控官（LLM B）的历史发言记录 |
| `web_data` | array[string] | 证据池：社媒 + 网页采集的原始数据 |
| `similiar` | string | 向量检索返回的历史相似舆情案例 |

---

## 🚀 快速开始（v4）

### 1. 启动微服务

```bash
cd v3  # 复用 v3 的微服务

# B站服务
python "bilibili_ 搜索api.py"
python "bilibili_ 评论api.py"

# 抖音服务（需要 Chrome 远程调试模式，端口 9222）
python "dy搜索api.py"
python "dy评论api.py"
```

### 2. 配置 Dify

- 导入 `v4.yml` 到 Dify 控制台
- 配置各工具对应的微服务地址
- 确保向量知识库已创建并有历史数据（否则 RAG 检索为空）
- 配置 HTTP Webhook 地址（用于接收 Obsidian 研报）

### 3. 使用

在 Dify 对话界面输入关键词，系统将自动：

1. **并行采集**：社媒 Agent + 网页 Agent 同时抓取数据
2. **循环辩论**：调查官 vs 风控官，弹性轮次交叉验证
3. **JSON 量化**：辩论结果 → 结构化量化指标
4. **向量检索**：检索历史相似舆情，注入报告
5. **双出口输出**：共鸣长文 + Obsidian 研报，同时归档

---

## 💡 设计理念

> **v3 的问题是"辩论完就完了"** — 每次分析都是独立的，没有跨事件的知识积累。
>
> **v4 的核心思想是"让系统越用越聪明"** — 通过向量记忆系统，每次分析都会：
> 1. 先检索历史相似案例，校准当前判断
> 2. 分析完成后，将结果压缩为 Narrative Memory 存入向量库
> 3. 下次分析时，这些 Memory 就会成为可检索的历史案例
>
> 形成 **分析 → 归档 → 检索 → 校准 → 再分析** 的正向飞轮。
