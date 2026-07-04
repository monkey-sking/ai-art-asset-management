"""
批量生成子图 - 循环处理多个资产需求
使用单一状态模式，所有节点共享BatchGenerationLoopState
数据库层使用SQLAlchemy（兼容本地SQLite）
"""
import logging
import json
import os
import time
from typing import List, Dict, Any, Optional
from langgraph.graph import StateGraph, END
from langchain_core.runnables import RunnableConfig
from langgraph.runtime import Runtime
from coze_coding_utils.runtime_ctx.context import Context
from jinja2 import Template

from graphs.state import (
    BatchGenerationLoopState,
    BatchGenerationLoopInput,
    BatchGenerationLoopOutput,
)

from storage.database.db import get_session
from storage.database.shared.model import AssetRequest, PromptTemplate, GenerationTask, ImageAsset

logger = logging.getLogger(__name__)

# 重试配置
MAX_RETRIES = 3
RETRY_DELAY = 2  # 秒


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


def create_single_task_node(state: BatchGenerationLoopState, config: RunnableConfig, runtime: Runtime[Context]) -> BatchGenerationLoopState:
    """
    title: 创建单个生成任务
    desc: 从批量列表中取出当前资产需求，创建生成任务（带重试）
    """
    ctx = runtime.context
    current_asset_id = state.asset_request_ids[state.current_index]
    logger.info(f"[创建任务] 处理资产ID: {current_asset_id}, 进度: {state.current_index + 1}/{len(state.asset_request_ids)}")

    for attempt in range(1, MAX_RETRIES + 1):
        db = get_session()
        try:
            # 1. 查询资产需求信息
            asset = db.query(AssetRequest).filter(AssetRequest.id == current_asset_id).first()
            if not asset:
                logger.error(f"资产需求不存在: ID={current_asset_id}")
                state.current_index += 1
                state.failed_count += 1
                state.error_messages.append(f"资产需求不存在: ID={current_asset_id}")
                return state

            # 2. 查询提示词模板
            template = None
            if state.prompt_template_id:
                template = db.query(PromptTemplate).filter(PromptTemplate.id == state.prompt_template_id).first()

            # 3. 组合提示词
            if template:
                positive_prompt = template.positive_prompt
                # 替换变量
                positive_prompt = positive_prompt.replace("{{asset_name}}", asset.name)
                positive_prompt = positive_prompt.replace("{{asset_type}}", asset.asset_type)
                if hasattr(asset, 'priority') and asset.priority:
                    positive_prompt = positive_prompt.replace("{{rarity}}", asset.priority)
                if asset.description:
                    positive_prompt = positive_prompt.replace("{{description}}", asset.description)
            else:
                # 使用自定义提示词或默认
                positive_prompt = f"游戏图标，{asset.name}，{asset.asset_type}，高质量，清晰边缘"

            logger.info(f"[创建任务] 组合提示词: {positive_prompt}")

            # 4. 创建生成任务记录
            task = GenerationTask(
                asset_request_id=current_asset_id,
                prompt_template_id=state.prompt_template_id,
                positive_prompt=positive_prompt,
                model=state.model,
                size=state.size,
                quantity=state.quantity,
                status="生成中"
            )
            db.add(task)
            db.commit()
            db.refresh(task)

            state.current_task_id = task.id
            state.current_prompt = positive_prompt

            # 5. 更新资产需求状态为"生成中"
            asset.status = "生成中"
            db.commit()

            logger.info(f"[创建任务] 任务创建成功: task_id={state.current_task_id}")
            return state

        except Exception as e:
            logger.error(f"[创建任务] 尝试 {attempt}/{MAX_RETRIES} 失败: {str(e)}")
            db.rollback()
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY)
            else:
                state.current_index += 1
                state.failed_count += 1
                state.error_messages.append(f"创建任务失败: {str(e)}")
                return state
        finally:
            db.close()

    return state


def call_model_for_single_node(state: BatchGenerationLoopState, config: RunnableConfig, runtime: Runtime[Context]) -> BatchGenerationLoopState:
    """
    title: 调用模型生成单个资产图片
    desc: 使用AI模型生成图片（带重试）
    """
    ctx = runtime.context

    if state.current_task_id is None:
        logger.error("[调用模型] 当前任务ID为空，跳过生成")
        state.current_index += 1
        state.failed_count += 1
        state.error_messages.append("任务ID为空")
        return state

    logger.info(f"[调用模型] 开始生成图片: task_id={state.current_task_id}")

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            # 尝试导入图片生成SDK（本地开发可能不可用）
            try:
                from coze_coding_dev_sdk import ImageGenerationClient
                client = ImageGenerationClient(ctx=ctx)
                image_response = client.generate(
                    prompt=state.current_prompt,
                    model=state.model,
                    size=state.size
                )
                if image_response.success:
                    state.current_image_urls = image_response.image_urls or []
                    logger.info(f"[调用模型] 生成成功，获得 {len(state.current_image_urls)} 张图片")
                    return state
                else:
                    logger.warning(f"[调用模型] 生成失败: {image_response.error_messages}")
            except ImportError:
                # SDK不可用，模拟生成（用于本地测试）
                logger.warning("[调用模型] ImageGenerationSDK不可用，使用模拟生成")
                state.current_image_urls = [f"mock_image_{state.current_task_id}_{i}.png" for i in range(state.quantity)]
                logger.info(f"[调用模型] 模拟生成 {len(state.current_image_urls)} 张图片")
                return state

        except Exception as e:
            logger.warning(f"[调用模型] 尝试 {attempt}/{MAX_RETRIES} 失败: {str(e)}")
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY)

    # 所有重试失败
    state.current_index += 1
    state.failed_count += 1
    state.error_messages.append(f"模型调用失败: 已重试{MAX_RETRIES}次")
    return state


def save_single_results_node(state: BatchGenerationLoopState, config: RunnableConfig, runtime: Runtime[Context]) -> BatchGenerationLoopState:
    """
    title: 保存单个资产生成结果
    desc: 将生成的图片记录到数据库，更新任务和资产状态
    """
    if not state.current_image_urls:
        logger.error("[保存结果] 当前图片URL列表为空，跳过保存")
        state.current_index += 1
        state.failed_count += 1
        state.error_messages.append("图片URL列表为空")
        return state

    logger.info(f"[保存结果] 开始保存 {len(state.current_image_urls)} 张图片")
    db = get_session()

    try:
        saved_count = 0
        for i, image_url in enumerate(state.current_image_urls):
            try:
                # 创建图片资产记录
                image_asset = ImageAsset(
                    asset_request_id=state.asset_request_ids[state.current_index],
                    generation_task_id=state.current_task_id,
                    file_key=f"generated/{state.current_task_id}_{i}.png",
                    file_url=image_url,
                    status="候选",
                    is_final=False
                )
                db.add(image_asset)
                saved_count += 1
            except Exception as e:
                logger.error(f"[保存结果] 保存单张图片失败: {str(e)}")
                continue

        db.commit()

        # 更新任务状态
        task = db.query(GenerationTask).filter(GenerationTask.id == state.current_task_id).first()
        if task:
            task.result_urls = json.dumps(state.current_image_urls)
            task.status = "成功"
            db.commit()

        # 更新资产需求状态为"待筛选"
        asset = db.query(AssetRequest).filter(AssetRequest.id == state.asset_request_ids[state.current_index]).first()
        if asset:
            asset.status = "待筛选"
            db.commit()

        # 收集结果
        state.task_ids.append(state.current_task_id)
        state.image_urls.extend(state.current_image_urls)
        state.success_count += 1

        logger.info(f"[保存结果] 保存完成: task_id={state.current_task_id}, saved_count={saved_count}")

        # 更新索引，清空当前任务数据
        state.current_index += 1
        state.current_task_id = None
        state.current_prompt = ""
        state.current_image_urls = []

        return state

    except Exception as e:
        logger.error(f"[保存结果] 执行失败: {str(e)}")
        db.rollback()
        state.current_index += 1
        state.failed_count += 1
        state.error_messages.append(f"保存结果失败: {str(e)}")
        return state
    finally:
        db.close()


# 创建批量生成循环子图
batch_generation_builder = StateGraph(
    BatchGenerationLoopState,
    input_schema=BatchGenerationLoopInput,
    output_schema=BatchGenerationLoopOutput
)

# 添加节点
batch_generation_builder.add_node("create_task", create_single_task_node)
batch_generation_builder.add_node("call_model", call_model_for_single_node)
batch_generation_builder.add_node("save_results", save_single_results_node)

# 设置入口点
batch_generation_builder.set_entry_point("create_task")

# 添加边
batch_generation_builder.add_edge("create_task", "call_model")
batch_generation_builder.add_edge("call_model", "save_results")

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

# 编译子图
batch_generation_subgraph = batch_generation_builder.compile()
