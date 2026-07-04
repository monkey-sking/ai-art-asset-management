"""
调用AI模型生成图片节点
使用图片生成SDK调用模型，生成图片
"""
import json
import logging
import requests
from typing import Any
from langchain_core.runnables import RunnableConfig
from langgraph.runtime import Runtime
from coze_coding_utils.runtime_ctx.context import Context
from coze_coding_dev_sdk import ImageGenerationClient
from graphs.state import CallModelInput, CallModelOutput

logger = logging.getLogger(__name__)


def call_model_node(state: CallModelInput, config: RunnableConfig, runtime: Runtime[Context]) -> CallModelOutput:
    """
    title: 调用AI模型生成图片
    desc: 使用图片生成SDK调用模型，生成图片
    integrations: 图片生成SDK
    """
    ctx = runtime.context
    
    # 参数验证
    task_id = state.task_id
    positive_prompt = state.positive_prompt
    model = state.model if state.model else "doubao-seedream-5-0-260128"
    size = state.size if state.size else "2K"
    
    if task_id is None:
        raise Exception("task_id 参数缺失")
    if positive_prompt is None:
        raise Exception("positive_prompt 参数缺失")

    try:
        # 1. 初始化图片生成客户端
        client = ImageGenerationClient(ctx=ctx)

        # 2. 调用模型生成图片
        response = client.generate(
            prompt=positive_prompt,
            model=model,
            size=size,
            watermark=False  # 不添加水印
        )

        # 3. 检查生成结果
        if response.success:
            image_urls: list[str] = response.image_urls if response.image_urls else []
            status = "成功"

            logger.info(f"AI生图成功: task_id={task_id}, 生成{len(image_urls)}张图片")
        else:
            image_urls = []
            status = "失败"

            logger.error(f"AI生图失败: task_id={task_id}, {response.error_messages}")

        # 4. 更新任务状态（这里只是记录，后续节点会正式更新数据库）
        return CallModelOutput(
            task_id=task_id,
            image_urls=image_urls,
            status=status
        )

    except Exception as e:
        logger.error(f"调用AI模型失败: task_id={task_id}, {str(e)}")
        # 返回失败状态
        return CallModelOutput(
            task_id=task_id,
            image_urls=[],
            status="失败"
        )