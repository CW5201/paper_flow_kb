# Paper Flow KB

基于 RAG（检索增强生成）技术的企业级智能知识库系统，为垂直领域提供精准、智能的知识检索与问答服务。

## 项目概述

### 项目定位

Paper Flow KB 是一个端到端文档检索增强生成知识库工程，集成 MinerU 文档解析、BGE-M3 向量嵌入、Milvus 向量数据库，通过 LangGraph 搭建文档导入、用户问答双流程编排；基于 FastAPI 提供文件上传、任务管理、SSE 流式对话接口，搭配 MinIO 对象存储、MongoDB 对话历史存储。

### 核心目标

- 将非结构化文档（PDF、Markdown）转化为可检索的结构化知识
- 通过多路召回策略提升检索准确率
- 提供流畅的流式问答交互体验

## 核心功能

| 功能模块 | 描述 |
| --- | --- |
| **文档智能导入** | 支持 PDF/Markdown 文件上传，自动解析、切分、向量化 |
| **混合向量检索** | 稠密向量 + 稀疏向量（BM25）混合检索 |
| **多路召回融合** | 向量检索 + HyDE + Web 搜索 |
| **智能重排序** | Reranker 模型重排序，断崖检测动态截断 |
| **流式问答** | SSE 实时推送，逐字输出答案 |
| **会话历史管理** | MongoDB 存储对话历史，支持上下文连续对话 |

## 技术栈

| 类别 | 技术选型 |
| --- | --- |
| **后端框架** | FastAPI + Uvicorn |
| **工作流引擎** | LangGraph |
| **大语言模型** | 阿里云 DashScope (Qwen) |
| **向量嵌入** | BGE-M3 (1024维+稀疏) |
| **重排序模型** | BGE-Reranker-Large |
| **向量数据库** | Milvus |
| **文档数据库** | MongoDB |
| **对象存储** | MinIO |
| **PDF 解析** | MinerU |
| **前端** | HTML5 + JS |

## 项目结构

```
paper_flow_kb/
├── api/                              # API 路由层
│   ├── query_router.py              # 查询服务路由 (port 8001)
│   └── import_router.py             # 导入服务路由 (port 8000)
│
├── core/                             # 核心配置
│   ├── deps.py                      # 依赖注入（单例管理）
│   └── paths.py                     # 路径常量配置
│
├── processor/                        # 业务处理流程（LangGraph）
│   ├── import_processor/            # 导入流程
│   │   ├── base.py                  # 导入节点基类
│   │   ├── config.py                # 导入流程配置管理
│   │   ├── exceptions.py            # 导入流程自定义异常
│   │   ├── main_graph.py            # 导入流程图定义
│   │   ├── state.py                 # 状态类型定义
│   │   └── nodes/                   # 处理节点
│   │       ├── node_entry.py        # 入口节点
│   │       ├── node_pdf_to_md.py    # PDF 转 MD
│   │       ├── node_md_img.py       # 图片处理
│   │       ├── node_document_split.py  # 文档切分
│   │       ├── node_item_name_recognition.py  # 商品识别
│   │       ├── node_bge_embedding.py  # 向量嵌入
│   │       └── node_import_milvus.py  # Milvus 存储
│   │
│   └── query_processor/            # 查询流程
│       ├── base.py                  # 查询节点基类
│       ├── config.py                # 查询流程配置管理
│       ├── exceptions.py            # 查询流程自定义异常
│       ├── main_graph.py            # 查询流程图定义
│       ├── state.py                 # 状态类型定义
│       ├── prompt.py                # 提示词模板
│       └── nodes/                   # 处理节点
│           ├── node_item_name_confirm.py  # 商品确认
│           ├── node_vector_search.py  # 向量检索
│           ├── node_hyde_search.py   # HyDE 检索
│           ├── node_web_search_mcp.py  # Web 搜索
│           ├── node_rrf.py           # RRF 融合
│           ├── node_rerank.py        # 重排序
│           └── node_answer_output.py  # 答案生成
│
├── schema/                          # 数据模型定义
├── services/                        # 业务服务层
├── utils/                           # 工具函数库
├── front/                           # 前端页面
├── test/                            # 测试代码
└── .env.example                     # 环境变量示例
```

## 快速开始

### 环境要求

- Python 3.10+
- uv (Python 包管理器)

### 安装依赖

```bash
uv sync
```

### 配置环境变量

复制 `.env.example` 为 `.env` 并填写配置：

```bash
cp .env.example .env
```

### 启动服务

```bash
# 启动导入服务 (port 8000)
uvicorn api.import_router:app --host 0.0.0.0 --port 8000

# 启动查询服务 (port 8001)
uvicorn api.query_router:app --host 0.0.0.0 --port 8001
```

## API 接口

### 导入服务 (port 8000)

| 方法 | 路径 | 描述 |
| --- | --- | --- |
| POST | `/upload` | 上传文件 |
| GET | `/status/{task_id}` | 查询任务状态 |

### 查询服务 (port 8001)

| 方法 | 路径 | 描述 |
| --- | --- | --- |
| POST | `/query` | 发起查询 |
| GET | `/stream/{session_id}` | SSE 流式获取 |
| GET | `/history/{session_id}` | 获取历史 |
| DELETE | `/history/{session_id}` | 清除历史 |

## 适用场景

- **产品手册问答**：电子产品使用说明、维修手册等
- **技术文档检索**：API 文档、开发指南、FAQ 等
- **企业知识库**：内部制度、操作规范、培训资料等
- **售后客服支持**：产品故障排查、使用指导等

## License

MIT
