"""
批量导出工作流包装节点
整合筛选、处理、打包、创建批次四个步骤
"""
import logging
from langchain_core.runnables import RunnableConfig
from langgraph.runtime import Runtime
from coze_coding_utils.runtime_ctx.context import Context
from graphs.state import (
    BatchExportWrapperInput,
    BatchExportWrapperOutput,
    FilterAssetsInput,
    ProcessImagesInput,
    PackageExportInput,
    CreateExportBatchInput
)
from graphs.nodes.filter_assets_node import filter_assets_node
from graphs.nodes.process_images_node import process_images_node
from graphs.nodes.package_export_node import package_export_node
from graphs.nodes.create_export_batch_node import create_export_batch_node

logger = logging.getLogger(__name__)

def batch_export_wrapper_node(
    state: BatchExportWrapperInput,
    config: RunnableConfig,
    runtime: Runtime[Context]
) -> BatchExportWrapperOutput:
    """
    title: 批量导出工作流
    desc: 整合筛选、处理、打包、创建批次四个步骤，完成批量导出功能
    integrations: Supabase数据库、对象存储
    """
    export_preset_id = state.export_preset_id
    batch_name = state.batch_name or "未命名批次"
    
    logger.info(f"[批量导出] 开始批量导出，预设ID: {export_preset_id}, 批次名: {batch_name}")
    
    try:
        # 1. 筛选资产
        logger.info("[批量导出] 步骤1: 筛选已定稿资产")
        filter_input = FilterAssetsInput(export_preset_id=export_preset_id)
        filter_output = filter_assets_node(filter_input, config, runtime)
        
        if not filter_output.filtered_assets:
            logger.warning("[批量导出] 没有找到已定稿的资产，返回空结果")
            return BatchExportWrapperOutput(
                export_batch_id=0,
                manifest={},
                export_path=""
            )
        
        logger.info(f"[批量导出] 筛选到 {len(filter_output.filtered_assets)} 个已定稿资产")
        
        # 2. 处理图片
        logger.info("[批量导出] 步骤2: 批量处理图片")
        process_input = ProcessImagesInput(
            filtered_assets=filter_output.filtered_assets,
            export_preset_id=export_preset_id
        )
        process_output = process_images_node(process_input, config, runtime)
        
        logger.info(f"[批量导出] 处理完成 {len(process_output.processed_assets)} 张图片")
        
        # 3. 打包导出
        logger.info("[批量导出] 步骤3: 打包导出ZIP文件")
        package_input = PackageExportInput(
            processed_assets=process_output.processed_assets,
            batch_name=batch_name,
            export_preset_id=export_preset_id
        )
        package_output = package_export_node(package_input, config, runtime)
        
        logger.info(f"[批量导出] 打包完成: {package_output.export_path}")
        
        # 4. 创建导出批次记录
        logger.info("[批量导出] 步骤4: 创建导出批次记录")
        batch_input = CreateExportBatchInput(
            batch_name=batch_name,
            export_preset_id=export_preset_id,
            manifest=package_output.manifest,
            export_path=package_output.export_path
        )
        batch_output = create_export_batch_node(batch_input, config, runtime)
        
        logger.info(f"[批量导出] 批次记录创建成功，ID: {batch_output.export_batch_id}")
        
        # 返回最终结果
        return BatchExportWrapperOutput(
            export_batch_id=batch_output.export_batch_id,
            manifest=package_output.manifest,
            export_path=package_output.export_path
        )
        
    except Exception as e:
        logger.error(f"[批量导出] 执行失败: {e}")
        return BatchExportWrapperOutput(
            export_batch_id=0,
            manifest={},
            export_path=""
        )