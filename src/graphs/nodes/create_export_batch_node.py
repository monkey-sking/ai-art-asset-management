"""
创建导出批次节点
在数据库中创建导出批次记录，并更新资产状态为"已导出"
"""
import json
import logging
from typing import Any, Dict
from langchain_core.runnables import RunnableConfig
from langgraph.runtime import Runtime
from coze_coding_utils.runtime_ctx.context import Context
from storage.database.supabase_client import get_supabase_client
from postgrest.exceptions import APIError
from graphs.state import CreateExportBatchInput, CreateExportBatchOutput

logger = logging.getLogger(__name__)


def create_export_batch_node(state: CreateExportBatchInput, config: RunnableConfig, runtime: Runtime[Context]) -> CreateExportBatchOutput:
    """
    title: 创建导出批次
    desc: 在数据库中创建导出批次记录，并更新资产状态为"已导出"
    integrations: Supabase
    """
    ctx = runtime.context
    client = get_supabase_client()
    
    # 参数验证
    batch_name = state.batch_name
    export_preset_id = state.export_preset_id
    asset_request_ids = state.asset_request_ids
    manifest = state.manifest
    export_path = state.export_path
    
    if batch_name is None:
        raise Exception("batch_name 参数缺失")
    if export_preset_id is None:
        raise Exception("export_preset_id 参数缺失")
    if not asset_request_ids:
        raise Exception("asset_request_ids 参数缺失或为空列表")
    if export_path is None:
        raise Exception("export_path 参数缺失")

    try:
        # 1. 查询项目ID（从第一个资产需求中获取）
        first_asset_id = asset_request_ids[0]
        first_asset_response = client.table('asset_requests').select('node_id').eq('id', first_asset_id).maybe_single().execute()
        if first_asset_response is None or first_asset_response.data is None:
            raise Exception(f"资产需求ID {first_asset_id} 不存在")
        
        first_asset_data: Dict[str, Any] = first_asset_response.data
        node_id = first_asset_data.get('node_id', 0)

        # 查询节点所属项目
        node_response = client.table('nodes').select('project_id').eq('id', node_id).maybe_single().execute()
        if node_response is None or node_response.data is None:
            raise Exception(f"节点ID {node_id} 不存在")
        
        node_data: Dict[str, Any] = node_response.data
        project_id = node_data.get('project_id', 0)

        # 2. 创建导出批次记录
        batch_data: Dict[str, Any] = {
            'name': batch_name,
            'project_id': project_id,
            'export_preset_id': export_preset_id,
            'asset_ids': json.dumps(asset_request_ids),
            'file_count': len(asset_request_ids),
            'manifest': manifest,
            'export_path': export_path
        }

        batch_response = client.table('export_batches').insert(batch_data).execute()
        if batch_response.data is None or not isinstance(batch_response.data, list) or len(batch_response.data) == 0:
            raise Exception("创建导出批次失败，数据库返回空数据")
        
        batch_data_list: list = batch_response.data
        export_batch_id = batch_data_list[0]['id']

        # 3. 更新资产需求状态为"已导出"
        for asset_request_id in asset_request_ids:
            client.table('asset_requests').update({'status': '已导出'}).eq('id', asset_request_id).execute()

        logger.info(f"创建导出批次成功: export_batch_id={export_batch_id}, file_count={len(asset_request_ids)}")

        return CreateExportBatchOutput(
            export_batch_id=export_batch_id,
            file_count=len(asset_request_ids)
        )

    except APIError as e:
        logger.error(f"创建导出批次失败: {e.message}")
        raise Exception(f"创建导出批次失败: {e.message}")
    except Exception as e:
        logger.error(f"创建导出批次失败: {str(e)}")
        raise e