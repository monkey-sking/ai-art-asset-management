"""
更新状态节点
更新资产需求状态为"待筛选"，并统计候选图数量
"""
import json
import logging
from typing import Any, Dict
from langchain_core.runnables import RunnableConfig
from langgraph.runtime import Runtime
from coze_coding_utils.runtime_ctx.context import Context
from storage.database.supabase_client import get_supabase_client
from postgrest.exceptions import APIError
from graphs.state import UpdateStatusInput, UpdateStatusOutput

logger = logging.getLogger(__name__)


def update_status_node(state: UpdateStatusInput, config: RunnableConfig, runtime: Runtime[Context]) -> UpdateStatusOutput:
    """
    title: 更新状态
    desc: 更新资产需求状态为"待筛选"，并统计候选图数量
    integrations: Supabase
    """
    ctx = runtime.context
    client = get_supabase_client()
    
    # 参数验证
    asset_request_id = state.asset_request_id
    task_id = state.task_id
    
    if asset_request_id is None:
        raise Exception("asset_request_id 参数缺失")
    if task_id is None:
        raise Exception("task_id 参数缺失")

    try:
        # 1. 查询该资产需求的所有候选图数量
        count_response = client.table('image_assets').select('*', count='exact').eq('asset_request_id', asset_request_id).eq('status', '候选').execute()
        candidate_count = count_response.count if count_response.count else 0

        # 2. 更新资产需求状态
        if candidate_count > 0:
            asset_status = "待筛选"
        else:
            # 如果没有候选图，保持"生成中"状态或标记为失败
            asset_status = "生成中"

        client.table('asset_requests').update({'status': asset_status}).eq('id', asset_request_id).execute()

        # 3. 获取任务状态
        task_response = client.table('generation_tasks').select('status').eq('id', task_id).maybe_single().execute()
        if task_response is None or task_response.data is None:
            raise Exception(f"任务ID {task_id} 不存在")
        
        task_data: Dict[str, Any] = task_response.data
        task_status = task_data.get('status', '未知')

        logger.info(f"更新状态成功: asset_request_id={asset_request_id}, status={asset_status}, candidate_count={candidate_count}")

        return UpdateStatusOutput(
            asset_request_status=asset_status,
            task_status=task_status
        )

    except APIError as e:
        logger.error(f"更新状态失败: {e.message}")
        raise Exception(f"更新状态失败: {e.message}")
    except Exception as e:
        logger.error(f"更新状态失败: {str(e)}")
        raise e