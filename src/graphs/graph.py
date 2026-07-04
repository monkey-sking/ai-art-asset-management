"""
AI美术资产生产管理系统 - 简化主图编排
暂时只保留AI生图和批量导出两个工作流
"""
import logging
import time
from langgraph.graph import StateGraph, END
from langchain_core.runnables import RunnableConfig
from langgraph.runtime import Runtime
from coze_coding_utils.runtime_ctx.context import Context

from graphs.state import (
    GlobalState,
    GraphInput,
    GraphOutput,
    WorkflowRouterOutput,
    BatchGenerationWrapperInput,
    BatchGenerationWrapperOutput,
    BatchExportWrapperInput,
    BatchExportWrapperOutput,
    FilterAssetsInput,
    ProcessImagesInput,
    PackageExportInput,
    CreateExportBatchInput,
)

# 导入AI生图工作流节点
from graphs.nodes.create_task_node import create_task_node
from graphs.nodes.call_model_node import call_model_node
from graphs.nodes.save_results_node import save_results_node
from graphs.nodes.update_status_node import update_status_node
from graphs.nodes.quality_assessment_node import quality_assessment_node

# 导入批量导出工作流节点
from graphs.nodes.filter_assets_node import filter_assets_node
from graphs.nodes.process_images_node import process_images_node
from graphs.nodes.package_export_node import package_export_node
from graphs.nodes.create_export_batch_node import create_export_batch_node
from graphs.nodes.batch_export_wrapper_node import batch_export_wrapper_node

# 导入批量生成工作流节点
from graphs.nodes.batch_generation_wrapper_node import batch_generation_wrapper_node

logger = logging.getLogger(__name__)


def workflow_router_node(state: GraphInput, config: RunnableConfig, runtime: Runtime[Context]) -> WorkflowRouterOutput:
    """
    title: 工作流路由器
    desc: 根据 workflow_type 参数初始化全局状态，为后续节点准备数据
    """
    workflow_type = state.workflow_type
    
    # 初始化全局状态
    if workflow_type == "image_generation":
        # AI生图工作流参数
        return WorkflowRouterOutput(
            workflow_type=workflow_type,
            asset_request_id=state.asset_request_id,
            prompt_template_id=state.prompt_template_id,
            custom_prompt=state.custom_prompt,
            model=state.model,
            size=state.size,
            quantity=state.quantity
        )
    elif workflow_type == "batch_generation":
        # 批量生成工作流参数
        return WorkflowRouterOutput(
            workflow_type=workflow_type,
            asset_request_ids=state.asset_request_ids,
            prompt_template_id=state.prompt_template_id,
            model=state.model,
            size=state.size,
            quantity=state.quantity
        )
    elif workflow_type == "batch_export":
        # 批量导出工作流参数
        return WorkflowRouterOutput(
            workflow_type=workflow_type,
            export_preset_id=state.export_preset_id,
            asset_request_ids=state.asset_request_ids,
            batch_name=state.batch_name
        )
    else:
        # 默认返回生图工作流参数
        return WorkflowRouterOutput(
            workflow_type=workflow_type,
            asset_request_id=state.asset_request_id,
            prompt_template_id=state.prompt_template_id,
            custom_prompt=state.custom_prompt,
            model=state.model,
            size=state.size,
            quantity=state.quantity
        )


def batch_export_wrapper_node(state: BatchExportWrapperInput, config: RunnableConfig, runtime: Runtime[Context]) -> BatchExportWrapperOutput:
    """
    title: 批量导出包装节点
    desc: 执行批量导出工作流的完整流程：筛选资产 -> 处理图片 -> 打包导出 -> 创建批次
    """
    ctx = runtime.context
    
    # 参数验证
    export_preset_id = state.export_preset_id if state.export_preset_id else 1  # 默认使用预设ID=1
    batch_name = state.batch_name if state.batch_name else f"批次_{int(time.time())}"
    
    logger.info(f"[批量导出] 开始批量导出，预设ID: {export_preset_id}, 批次名: {batch_name}")
    
    try:
        # Step 1: 筛选资产
        logger.info("[批量导出] Step 1: 筛选已定稿资产")
        filter_result = filter_assets_node(
            FilterAssetsInput(export_preset_id=export_preset_id),
            config,
            runtime
        )
        
        # Step 2: 处理图片
        logger.info("[批量导出] Step 2: 处理图片（去白底、调整尺寸）")
        process_result = process_images_node(
            ProcessImagesInput(
                export_preset_id=export_preset_id,
                filtered_assets=filter_result.filtered_assets
            ),
            config,
            runtime
        )
        
        # Step 3: 打包导出
        logger.info("[批量导出] Step 3: 打包导出ZIP文件")
        package_result = package_export_node(
            PackageExportInput(
                processed_assets=process_result.processed_assets,
                batch_name=batch_name
            ),
            config,
            runtime
        )
        
        # Step 4: 创建导出批次记录
        logger.info("[批量导出] Step 4: 创建导出批次记录")
        batch_result = create_export_batch_node(
            CreateExportBatchInput(
                batch_name=batch_name,
                export_preset_id=export_preset_id,
                asset_request_ids=[asset.get("request_id") for asset in filter_result.filtered_assets],
                manifest=package_result.manifest,
                export_path=package_result.export_path
            ),
            config,
            runtime
        )
        
        logger.info(f"[批量导出] 完成：导出 {len(filter_result.filtered_assets)} 个文件")
        
        return BatchExportWrapperOutput(
            export_batch_id=batch_result.export_batch_id,
            file_count=len(filter_result.filtered_assets),
            manifest=package_result.manifest,
            export_path=package_result.export_path
        )
        
    except Exception as e:
        logger.error(f"[批量导出] 执行失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return BatchExportWrapperOutput(
            export_batch_id=0,
            file_count=0,
            manifest={},
            export_path=""
        )


def workflow_path_router(state: WorkflowRouterOutput) -> str:
    """
    title: 工作流路径决策
    desc: 根据workflow_type返回分支名
    """
    workflow_type = state.workflow_type
    if workflow_type == "image_generation":
        return "执行AI生图工作流"
    elif workflow_type == "batch_generation":
        return "执行批量生成工作流"
    elif workflow_type == "batch_export":
        return "执行批量导出工作流"
    else:
        return "执行AI生图工作流"  # 默认执行生图工作流


# 创建主图
main_builder = StateGraph(
    GlobalState,
    input_schema=GraphInput,
    output_schema=GraphOutput
)

# 添加路由节点（初始化全局状态）
main_builder.add_node("workflow_router", workflow_router_node)

# 添加AI生图工作流节点
main_builder.add_node("create_task", create_task_node)
main_builder.add_node("call_model", call_model_node)
main_builder.add_node("save_results", save_results_node)
main_builder.add_node("quality_assessment", quality_assessment_node)
main_builder.add_node("update_status", update_status_node)

# 添加批量导出工作流节点（包装节点）
main_builder.add_node("batch_export", batch_export_wrapper_node)

# 添加批量生成工作流节点（包装节点）
main_builder.add_node("batch_generation", batch_generation_wrapper_node)

# 设置入口点为路由节点
main_builder.set_entry_point("workflow_router")

# 添加条件分支（从路由节点到第一个工作流节点）
main_builder.add_conditional_edges(
    source="workflow_router",
    path=workflow_path_router,
    path_map={
        "执行AI生图工作流": "create_task",
        "执行批量导出工作流": "batch_export",
        "执行批量生成工作流": "batch_generation"
    }
)

# AI生图工作流的边
main_builder.add_edge("create_task", "call_model")
main_builder.add_edge("call_model", "save_results")
main_builder.add_edge("save_results", "quality_assessment")
main_builder.add_edge("quality_assessment", "update_status")
main_builder.add_edge("update_status", END)

# 批量导出工作流的边
main_builder.add_edge("batch_export", END)

# 批量生成工作流的边
main_builder.add_edge("batch_generation", END)

# 编译主图
main_graph = main_builder.compile()

# 导出主图
__all__ = ['main_graph']