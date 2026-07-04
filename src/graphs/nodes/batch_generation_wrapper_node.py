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
