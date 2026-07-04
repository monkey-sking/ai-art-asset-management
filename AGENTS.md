# AI美术资产生产管理系统 - 项目结构索引

## 项目概述
- **名称**: AI美术资产生产管理系统（AI Art Asset Production Management System）
- **功能**: 面向游戏项目的图标类资产生产流水线，统一管理需求、提示词、生成任务、候选图、最终图、导出规格和交付记录

---

## 数据库架构

### 核心数据表
| 表名 | 说明 | 关键字段 |
|------|------|---------|
| projects | 项目工作区 | id, name, description |
| nodes | 资产节点树 | id, project_id, parent_id, name, node_type |
| asset_requests | 资产需求 | id, node_id, name, asset_type, status, priority, asset_code |
| prompt_templates | 提示词模板 | id, name, positive_prompt, negative_prompt, variables |
| generation_tasks | 生成任务记录 | id, asset_request_id, final_prompt, model, status |
| image_assets | 图片资产 | id, request_id, task_id, file_path, status, generation_index |
| export_presets | 导出预设 | id, name, final_width, final_height, padding, remove_background |
| export_batches | 导出批次 | id, batch_name, manifest, export_path |

### 测试数据统计
- 项目：1个（测试游戏项目）
- 节点：9个（道具、技能、装备分类）
- 资产需求：8个（覆盖所有状态）
- 提示词模板：2个（道具图标模板、技能图标模板）
- 导出预设：2个（手机图标预设、PC图标预设）
- 导出批次：2个（已完成的导出记录）

---

## 工作流清单

### 1. AI生图工作流（已测试通过）
**路径**: workflow_router → create_task → call_model → save_results → update_status → END

**入参**:
```json
{
  "workflow_type": "image_generation",
  "asset_request_id": 1,  // 必填
  "prompt_template_id": 1, // 可选
  "custom_prompt": "...",  // 可选
  "model": "doubao-seedream-5-0-260128", // 可选
  "size": "2K",  // 可选
  "quantity": 1  // 可选
}
```

**出参**:
```json
{
  "workflow_type": "image_generation",
  "task_id": 1,
  "image_urls": ["https://storage.example.com/icons/..."],
  "run_id": "..."
}
```

---

### 2. 批量导出工作流（已测试通过）
**路径**: workflow_router → batch_export_wrapper → (filter_assets → process_images → package_export → create_export_batch) → END

**入参**:
```json
{
  "workflow_type": "batch_export",
  "export_preset_id": 1,  // 必填
  "batch_name": "测试批次"  // 必填
}
```

**出参**:
```json
{
  "workflow_type": "batch_export",
  "export_batch_id": 1,
  "file_count": 3,
  "manifest": {...},
  "export_path": "exports/...",
  "run_id": "..."
}
```

---

### 3. 批量生成工作流（代码已完成，待优化）
**路径**: workflow_router → batch_generation_wrapper → (循环子图) → END

**状态**: 代码已完成，需要优化数据库查询和API调用逻辑

---

## 节点清单

### AI生图工作流节点
| 节点名 | 文件位置 | 类型 | 功能描述 | 配置文件 |
|-------|---------|------|---------|---------|
| workflow_router | graph.py | task | 工作流路由器，初始化全局状态 | - |
| create_task | nodes/create_task_node.py | task | 创建生成任务，组合提示词 | - |
| call_model | nodes/call_model_node.py | task | 调用AI模型生图 | config/default_generation_cfg.json |
| save_results | nodes/save_results_node.py | task | 保存图片到对象存储 | - |
| update_status | nodes/update_status_node.py | task | 更新资产状态为"待筛选" | - |

### 批量导出工作流节点
| 节点名 | 文件位置 | 类型 | 功能描述 | 配置文件 |
|-------|---------|------|---------|---------|
| batch_export_wrapper | graph.py | task | 批量导出包装节点 | - |
| filter_assets | nodes/filter_assets_node.py | task | 筛选已定稿资产 | - |
| process_images | nodes/process_images_node.py | task | 处理图片（去白底、调整尺寸） | - |
| package_export | nodes/package_export_node.py | task | 打包导出ZIP文件 | - |
| create_export_batch | nodes/create_export_batch_node.py | task | 创建导出批次记录 | - |

### 提示词优化节点（已完成）
| 节点名 | 文件位置 | 类型 | 功能描述 | 配置文件 |
|-------|---------|------|---------|---------|
| prompt_optimizer | nodes/prompt_optimizer_node.py | agent | 使用LLM自动优化提示词 | config/prompt_optimizer_llm_cfg.json |

---

## 子图清单

| 子图名 | 文件位置 | 功能描述 | 被调用节点 | 状态 |
|-------|---------|------|---------|------|
| batch_generation_subgraph | graphs/loop_graph.py | 循环处理多个资产需求 | batch_generation_wrapper_node | 代码已完成，待优化 |

---

## 技能使用

### 已集成的技能
1. **Supabase（数据库）**: 用于存储所有资产数据、任务记录、导出历史
2. **对象存储（S3）**: 用于存储生成的图片文件、导出的ZIP文件
3. **图片生成（ImageGeneration）**: 用于调用AI模型生成图片（豆包生图模型）
4. **大语言模型（LLM）**: 用于优化提示词（豆包大模型）

### 技能文档位置
- Supabase: `/skills/public/prod/supabase/references/python/README.md`
- 对象存储: `/skills/public/prod/storage/python/README.md`
- 图片生成: `/skills/public/prod/image-generation/python/README.md`

---

## 配置文件清单

| 配置文件 | 说明 | 模型 | 用途 |
|---------|------|------|------|
| config/prompt_optimizer_llm_cfg.json | 提示词优化模型配置 | doubao-pro-32k-241215 | 自动优化提示词 |
| config/default_generation_cfg.json | 默认生图模型配置 | doubao-seedream-5-0-260128 | 生成图标图片 |

---

## 提示词变量列表

系统支持以下提示词变量（在create_task_node中自动替换）：

| 变量名 | 替换值 | 说明 |
|--------|--------|------|
| {{asset_name}} | 资产需求名称 | 例如："生命药水" |
| {{asset_type}} | 资产类型 | 例如："道具"、"技能"、"装备" |
| {{rarity}} | 优先级（作为稀有度） | 例如："普通"、"高级"、"稀有" |
| {{description}} | 资产描述 | 从asset_requests.description字段读取 |
| {{node_name}} | 所属节点名称 | 例如："普通道具"、"高级技能" |

---

## 资产状态流转图

```
待生成 → 生成中 → 待筛选 → 已定稿 → 已导出
  ↓         ↓        ↓        ↓        ↓
废弃      废弃     废弃     废弃     废弃
```

**状态说明**:
- **待生成**: 已有需求但尚未生成图片
- **生成中**: 任务正在队列中或模型处理中
- **待筛选**: 已有候选图但未定稿
- **已定稿**: 已有最终候选图
- **已导出**: 最终图已进入某次导出批次
- **废弃**: 该资产或候选图不再使用

---

## 测试数据详情

### 资产需求测试数据（覆盖所有状态）
| ID | 名称 | 类型 | 状态 | 所属节点 |
|----|------|------|------|---------|
| 1 | 生命药水 | 道具 | 已定稿 | 普通道具 |
| 2 | 魔法药水 | 道具 | 已定稿 | 普通道具 |
| 3 | 稀有宝石 | 道具 | 已定稿 | 稀有道具 |
| 4 | 火球术 | 技能 | 待生成 | 普通技能 |
| 5 | 冰霜箭 | 技能 | 生成中 | 普通技能 |
| 6 | 雷霆一击 | 技能 | 待筛选 | 高级技能 |
| 7 | 铁剑 | 装备 | 已导出 | 普通装备 |
| 8 | 魔法杖 | 装备 | 已导出 | 稀有装备 |

---

## 后续优化建议

### 1. 批量生成工作流优化
- 修复数据库查询逻辑，确保正确获取资产需求和提示词模板
- 添加失败重试机制，支持部分失败时继续执行
- 优化并行生成性能，控制并发数量避免API限流

### 2. 图片质量评估节点
- 添加自动化质量检测逻辑（清晰度、色彩、构图）
- 支持质量评分和排序，辅助筛选最终图

### 3. 资产版本管理
- 支持资产的重新生成、变体生成
- 添加历史版本查看和对比功能
- 记录每次生成的参数变化

### 4. Web界面开发
- 参见 `docs/web_interface_guide.md` 的开发指南
- 建议使用React/Vue框架开发前端
- 实现实时任务监控、批量操作、导出管理等功能

---

## 项目文件结构

```
/workspace/projects/
├── src/
│   ├── graphs/
│   │   ├── state.py          # 状态定义（节点出入参）
│   │   ├── graph.py          # 主图编排
│   │   ├── loop_graph.py     # 批量生成循环子图
│   │   └── nodes/
│   │       ├── create_task_node.py
│   │       ├── call_model_node.py
│   │       ├── save_results_node.py
│   │       ├── update_status_node.py
│   │       ├── filter_assets_node.py
│   │       ├── process_images_node.py
│   │       ├── package_export_node.py
│   │       ├── create_export_batch_node.py
│   │       └── prompt_optimizer_node.py
│   ├── storage/
│   │   └── database/
│   │       ├── shared/
│   │       │   └ model.py    # 数据库Schema定义
│   │       └── supabase_client.py
│   └── tools/
├── config/
│   ├── prompt_optimizer_llm_cfg.json
│   └── default_generation_cfg.json
├── docs/
│   └ web_interface_guide.md  # Web界面开发指南
└── AGENTS.md                  # 本文档
```

---

## 使用示例

### 1. 测试AI生图工作流
```bash
test_run({
  "workflow_type": "image_generation",
  "asset_request_id": 1,
  "prompt_template_id": 1,
  "model": "doubao-seedream-5-0-260128",
  "size": "2K",
  "quantity": 1
})
```

### 2. 测试批量导出工作流
```bash
test_run({
  "workflow_type": "batch_export",
  "export_preset_id": 1,
  "batch_name": "测试批次"
})
```

### 3. 查询数据库测试数据
```sql
SELECT * FROM asset_requests WHERE status = '已定稿';
SELECT * FROM generation_tasks WHERE status = '成功';
SELECT * FROM export_batches ORDER BY created_at DESC;
```

---

**更新时间**: 2025-01-15  
**版本**: v1.0  
**状态**: 核心功能已完成，AI生图和批量导出工作流已测试通过