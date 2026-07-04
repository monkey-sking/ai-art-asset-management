"""
提示词优化节点
使用LLM自动优化提示词，使其更适合游戏图标生成
"""
import logging
import json
import os
from typing import Dict, Any
from langchain_core.runnables import RunnableConfig
from langgraph.runtime import Runtime
from coze_coding_utils.runtime_ctx.context import Context
from jinja2 import Template

from graphs.state import PromptOptimizerInput, PromptOptimizerOutput
from storage.database.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)


def prompt_optimizer_node(state: PromptOptimizerInput, config: RunnableConfig, runtime: Runtime[Context]) -> PromptOptimizerOutput:
    """
    title: 提示词优化
    desc: 使用LLM自动优化提示词，增强质量、清晰度和风格一致性
    integrations: 大语言模型
    """
    ctx = runtime.context
    
    # 参数验证
    if not state.original_prompt:
        logger.error("[提示词优化] original_prompt 不能为空")
        return PromptOptimizerOutput(
            optimized_prompt="",
            optimization_details={"error": "original_prompt不能为空"}
        )
    
    asset_name = state.asset_name if state.asset_name else "未知资产"
    asset_type = state.asset_type if state.asset_type else "道具"
    
    logger.info(f"[提示词优化] 开始优化提示词，资产名称: {asset_name}, 类型: {asset_type}")
    
    # 读取LLM配置文件
    cfg_file = os.path.join(os.getenv("COZE_WORKSPACE_PATH"), config['metadata']['llm_cfg'])
    with open(cfg_file, 'r', encoding='utf-8') as fd:
        llm_cfg = json.load(fd)
    
    model_config = llm_cfg.get("config", {})
    sp = llm_cfg.get("sp", "")
    up = llm_cfg.get("up", "")
    
    logger.info(f"[提示词优化] 使用模型: {model_config.get('model', 'unknown')}")
    
    # 渲染系统提示词
    sp_tpl = Template(sp)
    system_prompt = sp_tpl.render({})
    
    # 渲染用户提示词（包含原始提示词和资产信息）
    up_tpl = Template(up)
    user_prompt = up_tpl.render({
        "original_prompt": state.original_prompt,
        "asset_name": asset_name,
        "asset_type": asset_type
    })
    
    # 调用LLM API优化提示词
    try:
        from coze_coding_dev_sdk import LLMClient
        from langchain_core.messages import SystemMessage, HumanMessage
        
        llm_client = LLMClient(ctx=ctx)
        
        # 构建消息（使用LangChain消息格式）
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]
        
        # 调用模型（使用invoke方法）
        response = llm_client.invoke(
            messages=messages,
            model=model_config.get("model"),
            temperature=model_config.get("temperature", 0.7),
            max_completion_tokens=model_config.get("max_completion_tokens", 2000)
        )
        
        # 提取优化后的提示词（response.content可以是str或list）
        if isinstance(response.content, str):
            optimized_prompt = response.content.strip()
        elif isinstance(response.content, list):
            # 如果是list，提取文本部分
            text_parts = []
            for item in response.content:
                if isinstance(item, str):
                    text_parts.append(item)
                elif isinstance(item, dict) and item.get("type") == "text":
                    text_parts.append(item.get("text", ""))
            optimized_prompt = " ".join(text_parts).strip()
        else:
            optimized_prompt = state.original_prompt  # 如果失败，返回原始提示词
        
        logger.info(f"[提示词优化] 优化完成，原始长度: {len(state.original_prompt)}, 优化后长度: {len(optimized_prompt)}")
        
        # 返回优化结果
        return PromptOptimizerOutput(
            optimized_prompt=optimized_prompt,
            optimization_details={
                "original_prompt": state.original_prompt,
                "asset_name": asset_name,
                "asset_type": asset_type,
                "model": model_config.get("model"),
                "success": True
            }
        )
        
    except Exception as e:
        logger.error(f"[提示词优化] LLM调用失败: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # 失败时返回原始提示词
        return PromptOptimizerOutput(
            optimized_prompt=state.original_prompt,
            optimization_details={
                "original_prompt": state.original_prompt,
                "asset_name": asset_name,
                "asset_type": asset_type,
                "error": str(e),
                "success": False
            }
        )