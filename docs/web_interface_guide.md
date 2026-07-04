# AI美术资产生产管理系统 - Web界面开发指南

## 📋 概述
本文档提供前端Web界面的开发指南，包括API调用示例、交互流程建议和UI设计参考。

---

## 🚀 快速开始

### 1. 工作流调用方式

系统提供了3个核心工作流，通过统一的API接口调用：

**API Endpoint**: `/api/workflow/run`

**请求方式**: POST

**请求体格式**:
```json
{
  "workflow_type": "image_generation | batch_export",
  ...其他参数
}
```

---

## 📊 工作流调用示例

### 1. AI生图工作流

**场景**: 单个资产需求生成图片

**请求示例**:
```javascript
// JavaScript/TypeScript示例
const response = await fetch('/api/workflow/run', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    workflow_type: 'image_generation',
    asset_request_id: 1,  // 资产需求ID（必填）
    prompt_template_id: 1, // 提示词模板ID（可选）
    custom_prompt: '游戏道具图标，生命药水，高质量', // 自定义提示词（可选）
    model: 'doubao-seedream-5-0-260128', // 模型（可选，默认doubao-seedream-5-0-260128）
    size: '2K', // 图片尺寸（可选，默认2K）
    quantity: 1 // 生成数量（可选，默认1）
  })
});

const result = await response.json();
console.log('生成的图片:', result.image_urls);
console.log('任务ID:', result.task_id);
```

**响应示例**:
```json
{
  "workflow_type": "image_generation",
  "task_id": 1,
  "image_urls": [
    "https://storage.example.com/icons/item_hp_potion_1.png"
  ],
  "run_id": "abc123-def456"
}
```

---

### 2. 批量导出工作流

**场景**: 批量导出已定稿的最终图

**请求示例**:
```javascript
const response = await fetch('/api/workflow/run', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    workflow_type: 'batch_export',
    export_preset_id: 1, // 导出预设ID（必填）
    batch_name: '第一批次_道具图标' // 批次名称（必填）
  })
});

const result = await response.json();
console.log('导出批次ID:', result.export_batch_id);
console.log('文件数量:', result.file_count);
console.log('Manifest:', result.manifest);
```

**响应示例**:
```json
{
  "workflow_type": "batch_export",
  "export_batch_id": 1,
  "file_count": 3,
  "manifest": {
    "files": [
      {
        "file_name": "item_hp_potion.png",
        "request_id": 1,
        "node_name": "普通道具",
        "status": "最终",
        "size": [256, 256]
      }
    ],
    "export_time": "2025-01-15",
    "preset": "手机图标预设"
  },
  "export_path": "exports/batch_1_icons.zip",
  "run_id": "xyz789"
}
```

---

## 💡 前端交互流程建议

### 1. 项目管理流程

```
创建项目工作区
  ↓
建立节点树（道具、技能、装备等）
  ↓
配置节点默认提示词和导出预设
  ↓
统计节点下的资产数量
```

**UI建议**:
- 左侧树形结构展示项目节点
- 支持拖拽排序、右键菜单（新增、重命名、删除）
- 每个节点显示统计信息（需求数、候选数、最终数）

---

### 2. 资产需求管理流程

```
创建资产需求（填写名称、类型、描述）
  ↓
选择节点归属
  ↓
设置优先级和备注
  ↓
状态流转：待生成 → 生成中 → 待筛选 → 已定稿 → 已导出
```

**UI建议**:
- 卡片式布局展示资产需求
- 每个卡片显示：名称、状态标签、候选图缩略图
- 支持批量操作（批量选择、批量生成、批量导出）
- 状态筛选器（按状态快速过滤）

---

### 3. AI生成流程

```
选择资产需求
  ↓
配置提示词（选择模板或自定义）
  ↓
点击生成按钮
  ↓
查看任务队列状态（排队中 → 生成中 → 成功）
  ↓
查看生成结果（候选图展示）
  ↓
标记最终图或废弃候选图
```

**UI建议**:
- 提示词编辑器：支持模板选择、变量预览、实时优化
- 任务队列监控：显示进度条、预估时间
- 候选图展示：网格布局、支持放大查看、标记操作

---

### 4. 批量导出流程

```
筛选已定稿的资产
  ↓
选择导出预设（尺寸、去白底、命名规则）
  ↓
预览导出配置
  ↓
点击导出按钮
  ↓
下载ZIP文件和manifest
```

**UI建议**:
- 导出配置面板：选择预设、自定义参数
- 预览窗口：显示导出文件列表、命名规则
- 导出进度监控：显示处理进度、文件数量

---

## 🔧 数据库查询示例

### 1. 查询项目节点树

```javascript
// 使用Supabase客户端查询
const { data, error } = await supabase
  .from('nodes')
  .select('*')
  .eq('project_id', 1)
  .order('sort_order');

// 构建树形结构
function buildTree(nodes) {
  const tree = [];
  const map = {};
  
  nodes.forEach(node => {
    map[node.id] = { ...node, children: [] };
  });
  
  nodes.forEach(node => {
    if (node.parent_id) {
      map[node.parent_id].children.push(map[node.id]);
    } else {
      tree.push(map[node.id]);
    }
  });
  
  return tree;
}
```

---

### 2. 查询资产需求（按状态筛选）

```javascript
const { data, error } = await supabase
  .from('asset_requests')
  .select(`
    *,
    nodes(name),
    image_assets(file_path, status)
  `)
  .eq('node_id', 4) // 按节点筛选
  .eq('status', '待筛选') // 按状态筛选
  .order('created_at', { ascending: false });
```

---

### 3. 查询提示词模板

```javascript
const { data, error } = await supabase
  .from('prompt_templates')
  .select('*')
  .eq('id', 1);

// 使用模板生成提示词
const template = data[0];
const prompt = template.positive_prompt
  .replace('{{asset_name}}', '生命药水')
  .replace('{{asset_type}}', '道具');
```

---

## 🎨 UI设计参考

### 1. 主界面布局

```
+--------------------------------------------------+
| 顶部导航栏：项目管理 | 任务队列 | 导出历史 | 设置  |
+--------------------------------------------------+
| 左侧面板（30%） | 中间面板（50%） | 右侧面板（20%）|
|                |                |                |
| 项目节点树      | 资产卡片列表    | 提示词编辑器    |
| - 道具          | [卡片1] [卡片2] | - 模板选择      |
|   - 普通道具    | [卡片3] [卡片4] | - 变量替换      |
|   - 稀有道具    |                | - 参数配置      |
| - 技能          | 状态筛选器      |                |
| - 装备          | [待生成] [已定稿] | 生成按钮        |
+--------------------------------------------------+
```

---

### 2. 资产卡片设计

```
+------------------------+
| [缩略图]               |
|                        |
| 名称：生命药水          |
| 状态：[已定稿]          |
| 类型：道具              |
|                        |
| [生成] [导出] [详情]    |
+------------------------+
```

---

### 3. 任务队列面板

```
+------------------------+
| 任务队列（实时更新）    |
+------------------------+
| #1 生命药水   [生成中] |
| #2 魔法药水   [排队中] |
| #3 稀有宝石   [成功]   |
+------------------------+
| 批量操作：              |
| [全部重试] [全部取消]   |
+------------------------+
```

---

## 📝 常见问题

### Q1: 如何查看任务执行进度？
**A**: 工作流返回的run_id可用于查询执行日志：
```javascript
const logs = await fetch(`/api/logs/${runId}`);
```

---

### Q2: 如何处理生成失败的任务？
**A**: 查询generation_tasks表的status字段：
```javascript
const failedTasks = await supabase
  .from('generation_tasks')
  .select('*')
  .eq('status', '失败');
  
// 批量重试
failedTasks.forEach(task => {
  // 调用生成工作流，传入task.asset_request_id
});
```

---

### Q3: 如何查看导出历史？
**A**: 查询export_batches表：
```javascript
const batches = await supabase
  .from('export_batches')
  .select('*')
  .order('created_at', { ascending: false });
```

---

## 🔗 相关资源

- **数据库Schema**: 参见 `src/storage/database/shared/model.py`
- **工作流定义**: 参见 `src/graphs/graph.py` 和 `src/graphs/state.py`
- **节点函数**: 参见 `src/graphs/nodes/` 目录
- **API文档**: 参见 `docs/api.md`（待补充）

---

## 📦 前端技术栈建议

- **框架**: React/Vue/Next.js
- **UI库**: Ant Design / Element Plus / Material-UI
- **状态管理**: Redux / Zustand / Pinia
- **HTTP客户端**: Axios / Fetch API
- **实时通信**: WebSocket（用于任务队列实时更新）

---

## ✅ 下一步建议

1. **开发资产管理页面**：创建资产需求、查看候选图、标记最终图
2. **开发任务监控页面**：实时查看任务队列、进度、错误信息
3. **开发导出管理页面**：配置导出预设、查看导出历史、下载文件
4. **开发提示词编辑器**：模板管理、变量替换、实时优化

---

**提示**: 所有API调用都需要认证token，请在请求头中添加：
```javascript
headers: {
  'Authorization': `Bearer ${token}`
}
```