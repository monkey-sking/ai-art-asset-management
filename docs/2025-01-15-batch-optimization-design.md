# 批量生成工作流优化 & 前端增强 设计文档

## 1. 背景

AI美术资产生产管理系统的核心工作流已基本完成，但批量生成工作流存在性能和可靠性问题，前端需要对接真实的后端API。

## 2. 问题分析

### 2.1 批量生成工作流问题

| 问题 | 影响 | 优先级 |
|------|------|--------|
| 串行处理 | 批量生成速度慢 | 高 |
| 简单重试 | 失败后固定等待2秒 | 中 |
| 无部分失败处理 | 一个失败全部停止 | 高 |
| 无进度追踪 | 无法了解批量进度 | 中 |
| 无取消支持 | 无法中止长时间任务 | 低 |

### 2.2 前端问题

| 问题 | 影响 | 优先级 |
|------|------|--------|
| 批量生成逐个调用 | 速度慢，无并发 | 高 |
| 导出功能模拟 | 无法实际导出 | 高 |
| 无真实进度 | 用户体验差 | 中 |

## 3. 设计方案

### 3.1 批量生成工作流优化

#### 3.1.1 并行处理

使用 `concurrent.futures.ThreadPoolExecutor` 实现并行处理：

```python
MAX_CONCURRENT = 3  # 最大并发数

def batch_generation_wrapper_node(state, config, runtime):
    with ThreadPoolExecutor(max_workers=MAX_CONCURRENT) as executor:
        futures = []
        for asset_id in state.asset_request_ids:
            future = executor.submit(
                process_single_asset,
                asset_id, state, config, runtime
            )
            futures.append(future)
        
        # 收集结果
        for future in as_completed(futures):
            result = future.result()
            # 更新状态
```

#### 3.1.2 指数退避重试

```python
def retry_with_backoff(func, max_retries=3, base_delay=1):
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            delay = base_delay * (2 ** attempt)  # 1s, 2s, 4s
            time.sleep(delay)
```

#### 3.1.3 部分失败处理

```python
def process_single_asset(asset_id, state, config, runtime):
    try:
        # 处理单个资产
        return {"success": True, "asset_id": asset_id, ...}
    except Exception as e:
        # 记录失败，继续处理其他
        return {"success": False, "asset_id": asset_id, "error": str(e)}
```

#### 3.1.4 进度追踪

在数据库中添加进度追踪：

```sql
CREATE TABLE batch_generation_progress (
    id SERIAL PRIMARY KEY,
    batch_id VARCHAR(100) NOT NULL,
    total_count INTEGER NOT NULL,
    completed_count INTEGER DEFAULT 0,
    success_count INTEGER DEFAULT 0,
    failed_count INTEGER DEFAULT 0,
    status VARCHAR(20) DEFAULT 'running',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

#### 3.1.5 取消支持

在状态中添加取消标志：

```python
class BatchGenerationLoopState(BaseModel):
    # ... 现有字段
    cancelled: bool = Field(default=False, description="是否已取消")
```

在循环中检查取消标志：

```python
def batch_generation_router(state):
    if state.cancelled:
        return "取消"
    if state.current_index < len(state.asset_request_ids):
        return "继续生成"
    return "结束循环"
```

### 3.2 前端优化

#### 3.2.1 批量生成集成

修改 `batchGenerate` 函数，调用批量工作流API：

```javascript
async function batchGenerate() {
    const assetIds = Array.from(state.selectedAssetIds);
    if (assetIds.length === 0) {
        showToast('请先选择资产', 'error');
        return;
    }
    
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
        
        showToast(`批量生成已启动，共 ${assetIds.length} 个资产`, 'success');
        clearSelection();
        
        // 开始轮询进度
        pollBatchProgress(res.run_id);
    } catch (e) {
        showToast(`批量生成失败: ${e.message}`, 'error');
    }
}
```

#### 3.2.2 实时进度追踪

```javascript
async function pollBatchProgress(runId) {
    const poll = async () => {
        try {
            const progress = await api(`/api/batch/${runId}/progress`);
            updateProgressUI(progress);
            
            if (progress.status === 'running') {
                setTimeout(poll, 1000);  // 每秒轮询
            } else {
                // 完成或失败
                await loadAllData();
                renderAll();
            }
        } catch (e) {
            console.error('Progress poll error:', e);
        }
    };
    poll();
}
```

#### 3.2.3 任务取消

```javascript
async function cancelBatch(runId) {
    try {
        await api(`/api/batch/${runId}/cancel`, { method: 'POST' });
        showToast('已取消', 'success');
    } catch (e) {
        showToast('取消失败', 'error');
    }
}
```

#### 3.2.4 导出功能对接

```javascript
async function startExport() {
    const finalizedAssets = state.assets.filter(a => 
        ['已定稿', '已导出'].includes(a.status)
    );
    
    if (finalizedAssets.length === 0) {
        showToast('没有可导出的资产', 'error');
        return;
    }
    
    try {
        const res = await api('/run', {
            method: 'POST',
            body: JSON.stringify({
                workflow_type: 'batch_export',
                export_preset_id: 1,  // 从UI获取
                batch_name: document.getElementById('export-name')?.value || '未命名导出',
                asset_request_ids: finalizedAssets.map(a => a.id)
            })
        });
        
        showToast('导出任务已提交', 'success');
        closeModal('export');
        
        // 轮询导出进度
        pollExportProgress(res.run_id);
    } catch (e) {
        showToast(`导出失败: ${e.message}`, 'error');
    }
}
```

## 4. API接口设计

### 4.1 批量生成进度查询

**GET** `/api/batch/{run_id}/progress`

**响应**:
```json
{
    "run_id": "abc123",
    "status": "running",
    "total_count": 10,
    "completed_count": 5,
    "success_count": 4,
    "failed_count": 1,
    "progress_percent": 50,
    "current_asset": "生命药水",
    "errors": ["冰霜箭: 模型调用超时"]
}
```

### 4.2 批量取消

**POST** `/api/batch/{run_id}/cancel`

**响应**:
```json
{
    "message": "已发送取消信号",
    "run_id": "abc123"
}
```

### 4.3 导出历史查询

**GET** `/api/exports`

**响应**:
```json
{
    "exports": [
        {
            "id": 1,
            "name": "第一批次_道具图标",
            "file_count": 15,
            "export_path": "exports/batch_1.zip",
            "created_at": "2025-01-15 10:30:00"
        }
    ]
}
```

## 5. 实施计划

### Phase 1: 后端优化 (batch_generation_wrapper_node.py)
1. 添加并行处理支持
2. 实现指数退避重试
3. 添加部分失败处理
4. 添加进度追踪

### Phase 2: 数据库Schema更新
1. 添加batch_generation_progress表
2. 更新相关查询

### Phase 3: API层更新
1. 添加进度查询API
2. 添加取消API
3. 添加导出历史API

### Phase 4: 前端更新
1. 修改批量生成调用
2. 添加进度追踪UI
3. 添加取消按钮
4. 对接导出API

## 6. 测试用例

### 6.1 批量生成测试
- 测试10个资产并行生成
- 测试部分失败场景
- 测试取消功能

### 6.2 前端测试
- 测试批量选择和生成
- 测试进度显示
- 测试导出流程

---

**文档版本**: v1.0
**创建时间**: 2025-01-15
**状态**: 待实施
