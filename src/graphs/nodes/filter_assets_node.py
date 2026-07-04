"""
筛选资产节点
根据资产需求ID列表，筛选出最终图资产
"""
import json
import logging
from typing import Any, Dict, List
from langchain_core.runnables import RunnableConfig
from langgraph.runtime import Runtime
from coze_coding_utils.runtime_ctx.context import Context
from storage.database.supabase_client import get_supabase_client
from postgrest.exceptions import APIError
from graphs.state import FilterAssetsInput, FilterAssetsOutput

logger = logging.getLogger(__name__)


def filter_assets_node(state: FilterAssetsInput, config: RunnableConfig, runtime: Runtime[Context]) -> FilterAssetsOutput:
    """
    title: 筛选资产
    desc: 自动查询所有已定稿的资产，筛选出最终图
    integrations: Supabase
    """
    ctx = runtime.context
    client = get_supabase_client()
    
    # 参数验证
    export_preset_id = state.export_preset_id
    if export_preset_id is None:
        raise Exception("export_preset_id 参数缺失")

    try:
        filtered_assets: List[Dict[str, Any]] = []

        # 1. 查询所有已定稿的资产需求
        asset_requests_response = client.table('asset_requests').select('*').eq('status', '已定稿').execute()
        
        if asset_requests_response.data is None or not isinstance(asset_requests_response.data, list):
            logger.info("没有已定稿的资产需求")
            return FilterAssetsOutput(filtered_assets=filtered_assets)
        
        asset_requests_list: list = asset_requests_response.data
        
        # 2. 遍历资产需求，查询最终图
        for asset_request in asset_requests_list:
            asset_request_id = asset_request['id']
            
            # 查询该资产的最终图（status='最终'）
            response = client.table('image_assets').select('*').eq('request_id', asset_request_id).eq('status', '最终').execute()

            if response.data is None or not isinstance(response.data, list) or len(response.data) == 0:
                logger.warning(f"资产需求 {asset_request_id} 暂无最终图，跳过")
                continue

            image_assets_list: list = response.data
            
            # 添加所有最终图到结果列表
            for image_asset in image_assets_list:
                # 组装资产信息
                asset_info: Dict[str, Any] = {
                    'image_asset_id': image_asset['id'],
                    'asset_request_id': asset_request_id,
                    'file_path': image_asset['file_path'],
                    'asset_name': asset_request.get('name', ''),
                    'asset_code': asset_request.get('asset_code', ''),
                    'asset_type': asset_request.get('asset_type', '')
                }
                
                filtered_assets.append(asset_info)

        logger.info(f"筛选资产完成: 共筛选出{len(filtered_assets)}个资产")

        return FilterAssetsOutput(filtered_assets=filtered_assets)

    except APIError as e:
        logger.error(f"筛选资产失败: {e.message}")
        raise Exception(f"筛选资产失败: {e.message}")
    except Exception as e:
        logger.error(f"筛选资产失败: {str(e)}")
        raise e