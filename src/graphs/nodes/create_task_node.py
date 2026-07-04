"""
创建生成任务节点
从资产需求中提取信息，组合提示词，创建生成任务记录
"""
import json
import logging
from typing import Any, Dict
from langchain_core.runnables import RunnableConfig
from langgraph.runtime import Runtime
from coze_coding_utils.runtime_ctx.context import Context
from storage.database.supabase_client import get_supabase_client
from postgrest.exceptions import APIError
from graphs.state import CreateTaskInput, CreateTaskOutput

logger = logging.getLogger(__name__)


def create_task_node(state: CreateTaskInput, config: RunnableConfig, runtime: Runtime[Context]) -> CreateTaskOutput:
    """
    title: 创建生成任务
    desc: 从资产需求中提取信息，组合提示词，创建生成任务记录
    integrations: Supabase
    """
    ctx = runtime.context
    client = get_supabase_client()

    try:
        # 1. 查询资产需求
        asset_request_id = state.asset_request_id
        if asset_request_id is None:
            raise Exception("asset_request_id 参数缺失")
        
        asset_response = client.table('asset_requests').select('*').eq('id', asset_request_id).maybe_single().execute()
        if asset_response is None or asset_response.data is None:
            raise Exception(f"资产需求ID {asset_request_id} 不存在")
        
        asset_request: Dict[str, Any] = asset_response.data

        # 2. 组合提示词
        positive_prompt = ""
        negative_prompt: str | None = None

        # 使用提示词模板或自定义提示词
        if state.prompt_template_id:
            template_response = client.table('prompt_templates').select('*').eq('id', state.prompt_template_id).maybe_single().execute()
            if template_response is None or template_response.data is None:
                raise Exception(f"提示词模板ID {state.prompt_template_id} 不存在")
            
            template: Dict[str, Any] = template_response.data
            
            # 使用 isinstance 进行类型收窄
            if isinstance(template, dict):
                positive_prompt = template.get('positive_prompt', '')
                negative_prompt = template.get('negative_prompt')

                # 替换变量（如果有）
                variables = template.get('variables', {})
                if isinstance(variables, dict):
                    # 支持更多变量类型
                    positive_prompt = positive_prompt.replace('{{asset_name}}', asset_request.get('name', ''))
                    positive_prompt = positive_prompt.replace('{{asset_type}}', asset_request.get('asset_type', '道具'))
                    positive_prompt = positive_prompt.replace('{{rarity}}', asset_request.get('priority', '普通'))  # 使用priority作为稀有度
                    
                    # 支持自定义变量（从description或其他字段提取）
                    description = asset_request.get('description', '')
                    positive_prompt = positive_prompt.replace('{{description}}', description)
                    
                    # 支持节点变量（从node_id查询节点名称）
                    node_id = asset_request.get('node_id')
                    if node_id:
                        try:
                            node_response = client.table('nodes').select('name').eq('id', node_id).maybe_single().execute()
                            if node_response and isinstance(node_response.data, dict):
                                node_name = node_response.data.get('name', '')
                                positive_prompt = positive_prompt.replace('{{node_name}}', node_name)
                        except Exception:
                            pass  # 如果查询失败，忽略
                    
                    # 支持风格关键词（从全局配置读取）
                    # TODO: 可以从export_preset或其他配置读取风格关键词
        elif state.custom_prompt:
            positive_prompt = state.custom_prompt
        else:
            # 如果都没有，使用资产描述作为提示词
            positive_prompt = asset_request.get('description', asset_request.get('name', '图标'))

        # 3. 创建生成任务记录
        model = state.model if state.model else "doubao-seedream-5-0-260128"
        size = state.size if state.size else "2K"
        quantity = state.quantity if state.quantity else 1
        
        task_data = {
            'asset_request_id': asset_request_id,
            'prompt_template_id': state.prompt_template_id,
            'model': model,
            'size': size,
            'positive_prompt': positive_prompt,
            'negative_prompt': negative_prompt,
            'quantity': quantity,
            'status': '排队中'
        }

        task_response = client.table('generation_tasks').insert(task_data).execute()
        if task_response.data is None or not isinstance(task_response.data, list) or len(task_response.data) == 0:
            raise Exception("创建任务失败，数据库返回空数据")
        
        task_data_list: list = task_response.data
        task_id = task_data_list[0]['id']

        # 4. 更新资产需求状态为"生成中"
        client.table('asset_requests').update({'status': '生成中'}).eq('id', asset_request_id).execute()

        logger.info(f"创建生成任务成功: task_id={task_id}, asset_request_id={asset_request_id}")

        return CreateTaskOutput(
            task_id=task_id,
            positive_prompt=positive_prompt,
            negative_prompt=negative_prompt,
            model=model,
            size=size,
            quantity=quantity
        )

    except APIError as e:
        logger.error(f"创建生成任务失败: {e.message}")
        raise Exception(f"创建生成任务失败: {e.message}")
    except Exception as e:
        logger.error(f"创建生成任务失败: {str(e)}")
        raise e