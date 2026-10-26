# AI美术资产生产管理系统

<!-- badges:start -->
[![Last commit](https://img.shields.io/github/last-commit/monkey-sking/ai-art-asset-management?style=flat-square)](https://github.com/monkey-sking/ai-art-asset-management/commits/master) [![Python](https://img.shields.io/github/languages/top/monkey-sking/ai-art-asset-management?style=flat-square)](https://github.com/monkey-sking/ai-art-asset-management/search?l=Python) [![views](https://hits.sh/github.com/monkey-sking/ai-art-asset-management.svg?style=flat-square&label=views&color=0e75b6)](https://github.com/monkey-sking/ai-art-asset-management)
<!-- badges:end -->

面向游戏项目的图标类资产生产流水线，统一管理需求、提示词、生成任务、候选图、最终图、导出规格和交付记录。

## 功能特性

- **资产管理**：节点树结构管理资产需求，支持批量操作
- **AI生图**：调用豆包Seedream模型生成图标图片
- **批量生成**：并行处理多个资产，支持失败重试和进度追踪
- **批量导出**：一键导出已定稿资产，支持自定义导出预设
- **提示词优化**：使用LLM自动优化提示词质量
- **版本管理**：支持资产重新生成和历史版本查看

## 技术栈

- **后端**：Python 3.12+, FastAPI, LangGraph, SQLAlchemy
- **前端**：HTML/JavaScript, Ant Design
- **数据库**：SQLite (开发) / PostgreSQL (生产)
- **AI模型**：豆包Seedream 5.0

## 项目结构

```
src/
├── graphs/           # 工作流定义
│   ├── graph.py      # 主图编排
│   ├── state.py      # 状态定义
│   └── nodes/        # 工作流节点
├── api/              # API路由
│   └── crud.py       # CRUD接口
├── storage/          # 数据存储
│   └── database/     # 数据库连接
├── tools/            # 工具函数
└── main.py           # 服务入口

frontend/
└── index.html        # 前端界面

config/               # 配置文件
docs/                 # 文档
```

## 快速开始

### 1. 安装依赖

```bash
# 使用uv安装
uv sync

# 或使用pip
pip install -e .
```

### 2. 启动服务

```bash
cd src
python main.py -p 5000
```

### 3. 访问前端

打开 `frontend/index.html` 或访问 `http://localhost:5000`

## API接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/nodes` | GET | 获取节点树 |
| `/api/assets` | GET | 获取资产列表 |
| `/api/assets` | POST | 创建资产 |
| `/api/templates` | GET | 获取提示词模板 |
| `/api/stats` | GET | 获取统计数据 |
| `/run` | POST | 执行工作流 |

## 工作流

### AI生图工作流

```json
{
  "workflow_type": "image_generation",
  "asset_request_id": 1,
  "model": "doubao-seedream-5-0-260128",
  "size": "2K",
  "quantity": 1
}
```

### 批量生成工作流

```json
{
  "workflow_type": "batch_generation",
  "asset_request_ids": [1, 2, 3],
  "model": "doubao-seedream-5-0-260128",
  "size": "2K",
  "quantity": 1
}
```

### 批量导出工作流

```json
{
  "workflow_type": "batch_export",
  "export_preset_id": 1,
  "batch_name": "第一批次"
}
```

## 资产状态流转

```
待生成 → 生成中 → 待筛选 → 已定稿 → 已导出
```

## 配置说明

配置文件位于 `config/` 目录：

- `default_generation_cfg.json` - 生图模型配置
- `prompt_optimizer_llm_cfg.json` - 提示词优化配置

## 开发说明

### 添加新节点

1. 在 `src/graphs/nodes/` 创建节点文件
2. 在 `src/graphs/state.py` 定义输入输出状态
3. 在 `src/graphs/graph.py` 注册节点

### 数据库迁移

```bash
# 初始化迁移
alembic init migrations

# 生成迁移
alembic revision --autogenerate -m "description"

# 执行迁移
alembic upgrade head
```

## License

MIT
