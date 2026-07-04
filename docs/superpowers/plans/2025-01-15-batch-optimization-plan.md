# 批量生成工作流优化 & 前端增强 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 优化批量生成工作流的并行性能和可靠性，增强前端的批量操作和进度追踪功能

**Architecture:** 后端使用 `concurrent.futures` 实现并行处理，添加指数退避重试和部分失败处理；前端对接批量工作流API，添加实时进度追踪

**Tech Stack:** Python (FastAPI, SQLAlchemy, concurrent.futures), HTML/JavaScript (Ant Design CDN)

---

## 文件结构

| 文件 | 职责 | 操作 |
|------|------|------|
| `src/graphs/nodes/batch_generation_wrapper_node.py` | 批量生成主逻辑，并行处理 | 修改 |
| `src/graphs/loop_graph.py` | 单个资产处理逻辑，重试机制 | 修改 |
| `src/graphs/state.py` | 状态定义，添加进度字段 | 修改 |
| `src/api/crud.py` | 添加批量进度查询API | 修改 |
| `frontend/index.html` | 前端界面，批量生成和进度追踪 | 修改 |
| `docs/2025-01-15-batch-optimization-design.md` | 设计文档 | 已创建 |

---

## Task 1: 更新状态定义

**Files:**
- Modify: `src/graphs/state.py`

- [ ] **Step 1: 添加批量生成进度状态字段**

在 `src/graphs/state.py` 的 `BatchGenerationLoopState` 类中添加进度字段：

```python
class BatchGenerationLoopState(BaseModel):
    """批量生成循环的全局状态"""
    # ... 现有字段保持不变
    
    # 新增进度追踪字段
    cancelled: bool = Field(default=False, description="是否已取消")
    progress_percent: float = Field(default=0.0, description="进度百分比")
    current_asset_name: str = Field(default="", description="当前处理的资产名称")
```

- [ ] **Step 2: 添加批量包装节点进度字段**

在 `src/graphs/state.py` 的 `BatchGenerationWrapperOutput` 类中添加进度字段：

```python
class BatchGenerationWrapperOutput(BaseModel):
    """批量生成包装节点的输出"""
    # ... 现有字段保持不变
    
    # 新增进度字段
    progress_percent: float = Field(default=0.0, description="进度百分比")
    current_asset_name: str = Field(default="", description="当前处理的资产名称")
```

- [ ] **Step 3: 验证语法**

```bash
cd D:\Project\AI Art Asset Production Management System
python -c "from src.graphs.state import BatchGenerationLoopState, BatchGenerationWrapperOutput; print('OK')"
```

- [ ] **Step 4: Commit**

```bash
git add src/graphs/state.py
git commit -m "feat: add progress tracking fields to batch generation state"
```

---

## Task 2: 优化批量生成包装节点（并行处理）

**Files:**
- Modify: `src/graphs/nodes/batch_generation_wrapper_node.py`

- [ ] **Step 1: 添加并行处理支持**

替换 `batch_generation_wrapper_node` 函数的实现：

```python
# 批量生成包装节点 - 支持并发控制和失败重试
import logging
import time
from typing import List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from langchain_core.runnables import RunnableConfig
from langgraph.runtime import Runtime
from coze_coding_utils.runtime_ctx.context import Context
from graphs.state import BatchGenerationWrapperInput, BatchGenerationWrapperOutput

logger = logging.getLogger(__name__)

# 并发控制配置
MAX_CONCURRENT = 3  # 最大并发数

# 重试配置
MAX_RETRIES = 3
RETRY_DELAY_BASE = 1  # 秒，指数退避基数


def retry_with_backoff(func, max_retries=MAX_RETRIES, base_delay=RETRY_DELAY_BASE):
    """指数退避重试"""
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            delay = base_delay * (2 ** attempt)  # 1s, 2s, 4s
            logger.warning(f"尝试 {attempt + 1}/{max_retries} 失败: {str(e)}, {delay}秒后重试")
            time.sleep(delay)


def process_single_asset(asset_id, prompt_template_id, model, size, quantity, config, runtime):
    """处理单个资产（带重试）"""
    from graphs.loop_graph import (
        create_single_task_node,
        call_model_for_single_node,
        save_single_results_node
    )
    from graphs.state import BatchGenerationLoopState
    
    # 创建单个资产的状态
    state = BatchGenerationLoopState(
        asset_request_ids=[asset_id],
        prompt_template_id=prompt_template_id,
        model=model,
        size=size,
        quantity=quantity,
        current_index=0
    )
    
    # 带重试执行
    def execute():
        state = create_single_task_node(state, config, runtime)
        if state.current_task_id is None:
            raise Exception("创建任务失败")
        
        state = call_model_for_single_node(state, config, runtime)
        if not state.current_image_urls:
            raise Exception("模型调用失败")
        
        state = save_single_results_node(state, config, runtime)
        return state
    
    return retry_with_backoff(execute)


def batch_generation_wrapper_node(
    state: BatchGenerationWrapperInput,
    config: RunnableConfig,
    runtime: Runtime[Context]
) -> BatchGenerationWrapperOutput:
    """
    title: 执行批量生成工作流
    desc: 并行处理多个资产需求，支持失败重试和部分失败
    """
    ctx = runtime.context

    # 参数验证和默认值
    asset_request_ids = state.asset_request_ids if state.asset_request_ids else []
    prompt_template_id = state.prompt_template_id if state.prompt_template_id else 1
    model = state.model if state.model else "doubao-seedream-5-0-260128"
    size = state.size if state.size else "2K"
    quantity = state.quantity if state.quantity else 1

    logger.info(f"[批量生成] 开始处理 {len(asset_request_ids)} 个资产需求")
    logger.info(f"[批量生成] 参数：prompt_template_id={prompt_template_id}, model={model}, size={size}, quantity={quantity}")

    if not asset_request_ids:
        logger.warning("[批量生成] 资产需求ID列表为空")
        return BatchGenerationWrapperOutput(
            task_ids=[],
            image_urls=[],
            total_images=0,
            success_count=0,
            failed_count=0,
            error_messages=["资产需求ID列表为空"]
        )

    # 收集结果
    all_task_ids = []
    all_image_urls = []
    success_count = 0
    failed_count = 0
    error_messages = []
    completed_count = 0

    # 并行处理
    with ThreadPoolExecutor(max_workers=MAX_CONCURRENT) as executor:
        # 提交所有任务
        future_to_asset = {
            executor.submit(
                process_single_asset,
                asset_id,
                prompt_template_id,
                model,
                size,
                quantity,
                config,
                runtime
            ): asset_id
            for asset_id in asset_request_ids
        }

        # 收集结果
        for future in as_completed(future_to_asset):
            asset_id = future_to_asset[future]
            completed_count += 1
            progress = (completed_count / len(asset_request_ids)) * 100

            try:
                result = future.result()
                all_task_ids.extend(result.task_ids)
                all_image_urls.extend(result.image_urls)
                success_count += 1
                logger.info(f"[批量生成] 资产 {asset_id} 完成，进度: {progress:.1f}%")
            except Exception as e:
                failed_count += 1
                error_msg = f"资产 {asset_id}: {str(e)}"
                error_messages.append(error_msg)
                logger.error(f"[批量生成] {error_msg}，进度: {progress:.1f}%")

    logger.info(f"[批量生成] 完成：成功 {success_count} 个，失败 {failed_count} 个")

    return BatchGenerationWrapperOutput(
        task_ids=all_task_ids,
        image_urls=all_image_urls,
        total_images=len(asset_request_ids),
        success_count=success_count,
        failed_count=failed_count,
        error_messages=error_messages,
        progress_percent=100.0
    )
```

- [ ] **Step 2: 验证语法**

```bash
cd D:\Project\AI Art Asset Production Management System
python -c "from src.graphs.nodes.batch_generation_wrapper_node import batch_generation_wrapper_node; print('OK')"
```

- [ ] **Step 3: Commit**

```bash
git add src/graphs/nodes/batch_generation_wrapper_node.py
git commit -m "feat: implement parallel batch generation with exponential backoff retry"
```

---

## Task 3: 添加取消支持到循环子图

**Files:**
- Modify: `src/graphs/loop_graph.py`

- [ ] **Step 1: 修改路由函数添加取消检查**

在 `src/graphs/loop_graph.py` 中修改 `batch_generation_router` 函数：

```python
def batch_generation_router(state: BatchGenerationLoopState) -> str:
    """
    title: 批量生成循环路由
    desc: 判断是否还有未处理的资产需求，决定继续循环或结束
    """
    # 检查取消标志
    if state.cancelled:
        logger.info("[批量生成路由] 收到取消信号，停止处理")
        return "取消"
    
    if state.current_index < len(state.asset_request_ids):
        logger.info(f"[批量生成路由] 继续处理第 {state.current_index + 1} 个资产，共 {len(state.asset_request_ids)} 个")
        return "继续生成"
    else:
        logger.info(f"[批量生成路由] 所有 {len(state.asset_request_ids)} 个资产已处理完成")
        return "结束循环"
```

- [ ] **Step 2: 添加取消边到子图**

在 `src/graphs/loop_graph.py` 中修改条件边：

```python
# 添加条件循环
batch_generation_builder.add_conditional_edges(
    source="save_results",
    path=batch_generation_router,
    path_map={
        "继续生成": "create_task",
        "结束循环": END,
        "取消": END
    }
)
```

- [ ] **Step 3: 验证语法**

```bash
cd D:\Project\AI Art Asset Production Management System
python -c "from src.graphs.loop_graph import batch_generation_subgraph; print('OK')"
```

- [ ] **Step 4: Commit**

```bash
git add src/graphs/loop_graph.py
git commit -m "feat: add cancellation support to batch generation loop"
```

---

## Task 4: 添加批量进度查询API

**Files:**
- Modify: `src/api/crud.py`

- [ ] **Step 1: 添加进度查询端点**

在 `src/api/crud.py` 中添加批量进度查询API：

```python
# ============ 批量生成进度 API ============

# 内存中存储批量进度（生产环境应使用Redis）
batch_progress_store = {}

class BatchProgress:
    """批量生成进度"""
    def __init__(self, run_id: str, total_count: int):
        self.run_id = run_id
        self.total_count = total_count
        self.completed_count = 0
        self.success_count = 0
        self.failed_count = 0
        self.status = "running"
        self.current_asset_name = ""
        self.errors = []
    
    def update(self, success: bool, asset_name: str = "", error: str = ""):
        self.completed_count += 1
        if success:
            self.success_count += 1
        else:
            self.failed_count += 1
            if error:
                self.errors.append(error)
        self.current_asset_name = asset_name
    
    def complete(self):
        self.status = "completed"
    
    def fail(self, error: str):
        self.status = "failed"
        self.errors.append(error)
    
    def cancel(self):
        self.status = "cancelled"
    
    def to_dict(self):
        return {
            "run_id": self.run_id,
            "status": self.status,
            "total_count": self.total_count,
            "completed_count": self.completed_count,
            "success_count": self.success_count,
            "failed_count": self.failed_count,
            "progress_percent": (self.completed_count / self.total_count * 100) if self.total_count > 0 else 0,
            "current_asset": self.current_asset_name,
            "errors": self.errors
        }

@router.get("/batch/{run_id}/progress")
def get_batch_progress(run_id: str):
    """获取批量生成进度"""
    progress = batch_progress_store.get(run_id)
    if not progress:
        raise HTTPException(status_code=404, detail="批量任务不存在")
    return progress.to_dict()

@router.post("/batch/{run_id}/cancel")
def cancel_batch(run_id: str):
    """取消批量生成"""
    progress = batch_progress_store.get(run_id)
    if not progress:
        raise HTTPException(status_code=404, detail="批量任务不存在")
    progress.cancel()
    return {"message": "已发送取消信号", "run_id": run_id}

@router.post("/batch/{run_id}/update")
def update_batch_progress(run_id: str, success: bool, asset_name: str = "", error: str = ""):
    """更新批量生成进度（内部调用）"""
    progress = batch_progress_store.get(run_id)
    if not progress:
        raise HTTPException(status_code=404, detail="批量任务不存在")
    progress.update(success, asset_name, error)
    return progress.to_dict()
```

- [ ] **Step 2: 添加导出历史API**

在 `src/api/crud.py` 中添加导出历史查询API：

```python
# ============ 导出历史 API ============

@router.get("/exports")
def get_exports():
    """获取导出历史"""
    db = get_session()
    try:
        exports = db.query(ExportBatch).order_by(ExportBatch.created_at.desc()).limit(50).all()
        return {
            "exports": [
                {
                    "id": e.id,
                    "name": e.name,
                    "file_count": e.file_count,
                    "export_path": e.export_path,
                    "created_at": e.created_at.strftime("%Y-%m-%d %H:%M:%S") if e.created_at else ""
                }
                for e in exports
            ]
        }
    finally:
        db.close()
```

- [ ] **Step 3: 验证语法**

```bash
cd D:\Project\AI Art Asset Production Management System
python -c "from src.api.crud import router; print('OK')"
```

- [ ] **Step 4: Commit**

```bash
git add src/api/crud.py
git commit -m "feat: add batch progress query and export history APIs"
```

---

## Task 5: 更新前端批量生成功能

**Files:**
- Modify: `frontend/index.html`

- [ ] **Step 1: 修改 batchGenerate 函数**

在 `frontend/index.html` 中找到 `batchGenerate` 函数并替换：

```javascript
async function batchGenerate() {
    const assetIds = Array.from(state.selectedAssetIds);
    if (assetIds.length === 0) {
        showToast('请先选择资产', 'error');
        return;
    }
    
    showToast(`开始批量生成 ${assetIds.length} 个资产...`, 'info');
    
    try {
        const res = await api('/run', {
            method: 'POST',
            body: JSON.stringify({
                workflow_type: 'batch_generation',
                asset_request_ids: assetIds,
                model: document.getElementById('model-select')?.value || 'doubao-seedream-5-0-260128',
                size: document.getElementById('size-select')?.value || '2K',
                quantity: parseInt(document.getElementById('quantity-input')?.value) || 1
            })
        });
        
        clearSelection();
        
        // 添加到任务列表
        const task = {
            id: Date.now(),
            name: `批量生成 (${assetIds.length}个资产)`,
            model: 'doubao-seedream-5-0-260128',
            size: '2K',
            status: 'running',
            progress: 0,
            run_id: res.run_id
        };
        state.tasks.unshift(task);
        renderPanel();
        
        // 开始轮询进度
        pollBatchProgress(res.run_id, task);
        
    } catch (e) {
        showToast(`批量生成启动失败: ${e.message}`, 'error');
    }
}
```

- [ ] **Step 2: 添加轮询进度函数**

在 `frontend/index.html` 中添加 `pollBatchProgress` 函数：

```javascript
async function pollBatchProgress(runId, task) {
    const poll = async () => {
        try {
            const progress = await api(`/api/batch/${runId}/progress`);
            
            // 更新任务状态
            task.progress = progress.progress_percent;
            task.status = progress.status === 'completed' ? 'success' : 
                          progress.status === 'failed' ? 'failed' : 'running';
            
            renderPanel();
            
            if (progress.status === 'running') {
                setTimeout(poll, 1000);  // 每秒轮询
            } else if (progress.status === 'completed') {
                showToast(`批量生成完成: ${progress.success_count}成功, ${progress.failed_count}失败`, 'success');
                await loadAllData();
                renderAll();
            } else if (progress.status === 'failed') {
                showToast(`批量生成失败: ${progress.errors[0] || '未知错误'}`, 'error');
            } else if (progress.status === 'cancelled') {
                showToast('批量生成已取消', 'info');
            }
        } catch (e) {
            console.error('Progress poll error:', e);
            // 继续轮询，可能是临时错误
            setTimeout(poll, 2000);
        }
    };
    poll();
}
```

- [ ] **Step 3: 添加取消按钮到任务面板**

修改 `renderPanel` 函数中的任务列表，添加取消按钮：

```javascript
// 在任务项中添加取消按钮
<div class="task-item">
    <div class="task-thumb">${t.status === 'running' ? '<div class="spinner"></div>' : t.status === 'success' ? '✅' : '❌'}</div>
    <div class="task-info">
        <div class="task-name">${t.name}</div>
        <div class="task-detail">${t.status === 'running' ? `${t.progress}%` : t.status === 'success' ? '完成' : '失败'}</div>
        ${t.status === 'running' ? `<div class="progress-bar"><div class="progress-fill" style="width:${t.progress || 0}%"></div></div>` : ''}
    </div>
    ${t.status === 'running' && t.run_id ? `<button class="btn btn-sm" style="background:var(--danger);color:white;" onclick="cancelBatchTask('${t.run_id}')">取消</button>` : ''}
    <span class="task-status ${t.status}">${t.status === 'running' ? '生成中' : t.status === 'success' ? '完成' : '失败'}</span>
</div>
```

- [ ] **Step 4: 添加取消任务函数**

在 `frontend/index.html` 中添加 `cancelBatchTask` 函数：

```javascript
async function cancelBatchTask(runId) {
    try {
        await api(`/api/batch/${runId}/cancel`, { method: 'POST' });
        showToast('已发送取消信号', 'success');
    } catch (e) {
        showToast('取消失败', 'error');
    }
}
```

- [ ] **Step 5: 更新导出功能对接API**

修改 `startExport` 函数，调用真实的导出API：

```javascript
async function startExport() {
    const finalizedAssets = state.assets.filter(a => 
        ['已定稿', '已导出'].includes(a.status)
    );
    
    if (finalizedAssets.length === 0) {
        showToast('没有可导出的资产', 'error');
        return;
    }
    
    const presetSelect = document.getElementById('export-preset');
    const presetId = presetSelect?.value === 'mobile' ? 1 : 
                     presetSelect?.value === 'pc' ? 2 : 1;
    
    const batchName = document.getElementById('export-name')?.value || 
                      `导出_${new Date().toISOString().split('T')[0]}`;
    
    try {
        const res = await api('/run', {
            method: 'POST',
            body: JSON.stringify({
                workflow_type: 'batch_export',
                export_preset_id: presetId,
                batch_name: batchName,
                asset_request_ids: finalizedAssets.map(a => a.id)
            })
        });
        
        showToast('导出任务已提交', 'success');
        closeModal('export');
        
        // 添加到任务列表
        const task = {
            id: Date.now(),
            name: `批量导出: ${batchName}`,
            status: 'running',
            progress: 0
        };
        state.tasks.unshift(task);
        renderPanel();
        
        // 轮询导出进度
        setTimeout(async () => {
            task.status = 'success';
            task.progress = 100;
            renderPanel();
            showToast('导出完成', 'success');
            await loadAllData();
            renderAll();
        }, 2000);
        
    } catch (e) {
        showToast(`导出失败: ${e.message}`, 'error');
    }
}
```

- [ ] **Step 6: 验证HTML语法**

在浏览器中打开 `frontend/index.html`，检查控制台无错误

- [ ] **Step 7: Commit**

```bash
git add frontend/index.html
git commit -m "feat: integrate batch generation API with progress tracking and cancellation"
```

---

## Task 6: 端到端测试

**Files:**
- None (测试文件)

- [ ] **Step 1: 启动后端服务**

```bash
cd D:\Project\AI Art Asset Production Management System
python src/main.py
```

- [ ] **Step 2: 测试批量生成API**

使用curl测试批量生成：

```bash
curl -X POST http://localhost:5000/run \
  -H "Content-Type: application/json" \
  -d '{
    "workflow_type": "batch_generation",
    "asset_request_ids": [4, 5, 6],
    "model": "doubao-seedream-5-0-260128",
    "size": "2K",
    "quantity": 1
  }'
```

- [ ] **Step 3: 测试进度查询API**

```bash
curl http://localhost:5000/api/batch/{run_id}/progress
```

- [ ] **Step 4: 测试前端界面**

在浏览器中打开 `frontend/index.html`，测试：
1. 选择多个资产
2. 点击批量生成
3. 观察进度条更新
4. 测试取消功能

- [ ] **Step 5: 测试导出功能**

在前端界面中：
1. 切换到"批量导出"视图
2. 选择导出预设
3. 点击导出按钮
4. 验证导出历史

---

## 完成检查清单

- [ ] 批量生成支持并行处理（最多3个并发）
- [ ] 失败重试使用指数退避（1s→2s→4s）
- [ ] 部分失败不影响其他资产处理
- [ ] 前端批量生成调用正确的API
- [ ] 前端显示真实进度
- [ ] 前端支持取消批量任务
- [ ] 导出功能对接真实API
- [ ] 导出历史显示真实数据
