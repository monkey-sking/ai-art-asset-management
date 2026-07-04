"""
AI美术资产生产管理系统 - 工作流状态定义
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from utils.file.file import File


# ============ AI生图工作流状态 ============

class ImageGenerationInput(BaseModel):
    """AI生图工作流的输入"""
    asset_request_id: int = Field(..., description="资产需求ID")
    prompt_template_id: Optional[int] = Field(default=None, description="提示词模板ID（可选）")
    custom_prompt: Optional[str] = Field(default=None, description="自定义提示词（可选）")
    model: str = Field(default="doubao-seedream-5-0-260128", description="模型名称")
    size: str = Field(default="2K", description="图片尺寸")
    quantity: int = Field(default=1, description="生成数量")


class ImageGenerationOutput(BaseModel):
    """AI生图工作流的输出"""
    task_id: int = Field(..., description="生成任务ID")
    image_urls: List[str] = Field(default=[], description="生成的图片URL列表")
    asset_request_status: str = Field(..., description="资产需求状态")


class CreateTaskInput(BaseModel):
    """创建任务节点的输入"""
    asset_request_id: Optional[int] = Field(default=None, description="资产需求ID")
    prompt_template_id: Optional[int] = Field(default=None, description="提示词模板ID")
    custom_prompt: Optional[str] = Field(default=None, description="自定义提示词")
    model: Optional[str] = Field(default=None, description="模型名称")
    size: Optional[str] = Field(default=None, description="图片尺寸")
    quantity: Optional[int] = Field(default=None, description="生成数量")


class CreateTaskOutput(BaseModel):
    """创建任务节点的输出"""
    task_id: int = Field(..., description="生成任务ID")
    positive_prompt: str = Field(..., description="正向提示词")
    negative_prompt: Optional[str] = Field(default=None, description="负向提示词")
    model: str = Field(..., description="模型名称")
    size: str = Field(..., description="图片尺寸")
    quantity: int = Field(..., description="生成数量")


class CallModelInput(BaseModel):
    """调用模型节点的输入"""
    task_id: Optional[int] = Field(default=None, description="生成任务ID")
    positive_prompt: Optional[str] = Field(default=None, description="正向提示词")
    negative_prompt: Optional[str] = Field(default=None, description="负向提示词")
    model: Optional[str] = Field(default=None, description="模型名称")
    size: Optional[str] = Field(default=None, description="图片尺寸")
    quantity: Optional[int] = Field(default=None, description="生成数量")


class CallModelOutput(BaseModel):
    """调用模型节点的输出"""
    task_id: int = Field(..., description="生成任务ID")
    image_urls: List[str] = Field(default=[], description="生成的图片URL列表")
    status: str = Field(..., description="任务状态：成功/失败")


class SaveResultsInput(BaseModel):
    """保存结果节点的输入"""
    task_id: Optional[int] = Field(default=None, description="生成任务ID")
    asset_request_id: Optional[int] = Field(default=None, description="资产需求ID")
    image_urls: List[str] = Field(default=[], description="图片URL列表")


class SaveResultsOutput(BaseModel):
    """保存结果节点的输出"""
    task_id: int = Field(..., description="生成任务ID")
    saved_count: int = Field(..., description="保存的图片数量")
    image_urls: List[str] = Field(default=[], description="图片URL列表")
    image_asset_ids: List[int] = Field(default=[], description="保存的图片资产ID列表")


class UpdateStatusInput(BaseModel):
    """更新状态节点的输入"""
    asset_request_id: Optional[int] = Field(default=None, description="资产需求ID")
    task_id: Optional[int] = Field(default=None, description="生成任务ID")
    saved_count: Optional[int] = Field(default=None, description="保存的图片数量")


class UpdateStatusOutput(BaseModel):
    """更新状态节点的输出"""
    asset_request_status: str = Field(..., description="资产需求状态")
    task_status: str = Field(..., description="任务状态")


# ============ 批量导出工作流状态 ============

class BatchExportInput(BaseModel):
    """批量导出工作流的输入"""
    export_preset_id: int = Field(..., description="导出预设ID")
    asset_request_ids: List[int] = Field(..., description="资产需求ID列表")
    batch_name: str = Field(..., description="批次名称")


class BatchExportOutput(BaseModel):
    """批量导出工作流的输出"""
    export_batch_id: int = Field(..., description="导出批次ID")
    file_count: int = Field(..., description="导出文件数量")
    manifest: Dict[str, Any] = Field(default={}, description="manifest JSON")
    export_path: str = Field(..., description="导出包路径")


class BatchExportWrapperInput(BaseModel):
    """批量导出包装节点的输入"""
    export_preset_id: Optional[int] = Field(default=None, description="导出预设ID")
    asset_request_ids: Optional[List[int]] = Field(default=None, description="资产需求ID列表")
    batch_name: Optional[str] = Field(default=None, description="批次名称")


class BatchExportWrapperOutput(BaseModel):
    """批量导出包装节点的输出"""
    export_batch_id: int = Field(..., description="导出批次ID")
    file_count: int = Field(..., description="导出文件数量")
    manifest: Dict[str, Any] = Field(default={}, description="manifest JSON")
    export_path: str = Field(..., description="导出包路径")


class FilterAssetsInput(BaseModel):
    """筛选资产节点的输入"""
    export_preset_id: Optional[int] = Field(default=None, description="导出预设ID")


class FilterAssetsOutput(BaseModel):
    """筛选资产节点的输出"""
    filtered_assets: List[Dict[str, Any]] = Field(default=[], description="筛选后的资产列表")


class ProcessImagesInput(BaseModel):
    """图片处理节点的输入"""
    export_preset_id: Optional[int] = Field(default=None, description="导出预设ID")
    filtered_assets: List[Dict[str, Any]] = Field(default=[], description="筛选后的资产列表")


class ProcessImagesOutput(BaseModel):
    """图片处理节点的输出"""
    processed_assets: List[Dict[str, Any]] = Field(default=[], description="处理后的资产列表")


class PackageExportInput(BaseModel):
    """打包导出节点的输入"""
    processed_assets: List[Dict[str, Any]] = Field(default=[], description="处理后的资产列表")
    batch_name: Optional[str] = Field(default=None, description="批次名称")


class PackageExportOutput(BaseModel):
    """打包导出节点的输出"""
    export_path: str = Field(..., description="导出包路径")
    manifest: Dict[str, Any] = Field(default={}, description="manifest JSON")


class CreateExportBatchInput(BaseModel):
    """创建导出批次节点的输入"""
    batch_name: Optional[str] = Field(default=None, description="批次名称")
    export_preset_id: Optional[int] = Field(default=None, description="导出预设ID")
    asset_request_ids: List[int] = Field(default=[], description="资产需求ID列表")
    manifest: Dict[str, Any] = Field(default={}, description="manifest JSON")
    export_path: Optional[str] = Field(default=None, description="导出包路径")


class CreateExportBatchOutput(BaseModel):
    """创建导出批次节点的输出"""
    export_batch_id: int = Field(..., description="导出批次ID")
    file_count: int = Field(..., description="文件数量")


# ============ 提示词优化节点状态 ============

class PromptOptimizerInput(BaseModel):
    """提示词优化节点的输入"""
    original_prompt: str = Field(..., description="原始提示词")
    asset_name: Optional[str] = Field(default=None, description="资产名称")
    asset_type: Optional[str] = Field(default=None, description="资产类型")


class PromptOptimizerOutput(BaseModel):
    """提示词优化节点的输出"""
    optimized_prompt: str = Field(..., description="优化后的提示词")
    optimization_details: Dict[str, Any] = Field(default={}, description="优化细节")


# ============ 批量生成工作流状态 ============

class BatchGenerationInput(BaseModel):
    """批量生成工作流的输入"""
    asset_request_ids: List[int] = Field(..., description="资产需求ID列表")
    prompt_template_id: Optional[int] = Field(default=None, description="提示词模板ID")
    model: str = Field(default="doubao-seedream-5-0-260128", description="模型名称")
    size: str = Field(default="2K", description="图片尺寸")
    quantity_per_asset: int = Field(default=1, description="每个资产生成数量")


class BatchGenerationOutput(BaseModel):
    """批量生成工作流的输出"""
    task_ids: List[int] = Field(default=[], description="生成的任务ID列表")
    total_images: int = Field(..., description="总共生成的图片数量")
    success_count: int = Field(..., description="成功数量")
    failed_count: int = Field(..., description="失败数量")


class CreateTasksInput(BaseModel):
    """批量创建任务节点的输入"""
    asset_request_ids: List[int] = Field(..., description="资产需求ID列表")
    prompt_template_id: Optional[int] = Field(default=None, description="提示词模板ID")
    model: str = Field(default="doubao-seedream-5-0-260128", description="模型名称")
    size: str = Field(default="2K", description="图片尺寸")
    quantity_per_asset: int = Field(default=1, description="每个资产生成数量")


class CreateTasksOutput(BaseModel):
    """批量创建任务节点的输出"""
    tasks: List[Dict[str, Any]] = Field(default=[], description="创建的任务列表")


class ParallelGenerateInput(BaseModel):
    """并行生成节点的输入"""
    tasks: List[Dict[str, Any]] = Field(default=[], description="任务列表")


class ParallelGenerateOutput(BaseModel):
    """并行生成节点的输出"""
    results: List[Dict[str, Any]] = Field(default=[], description="生成结果列表")


class SummarizeResultsInput(BaseModel):
    """结果汇总节点的输入"""
    results: List[Dict[str, Any]] = Field(default=[], description="生成结果列表")


class SummarizeResultsOutput(BaseModel):
    """结果汇总节点的输出"""
    total_images: int = Field(..., description="总共生成的图片数量")
    success_count: int = Field(..., description="成功数量")
    failed_count: int = Field(..., description="失败数量")


# ============ 全局状态定义 ============

class GlobalState(BaseModel):
    """全局状态定义"""
    # 工作流类型标识
    workflow_type: Optional[str] = Field(default=None, description="工作流类型")
    
    # AI生图工作流状态
    asset_request_id: Optional[int] = Field(default=None, description="资产需求ID")
    prompt_template_id: Optional[int] = Field(default=None, description="提示词模板ID")
    custom_prompt: Optional[str] = Field(default=None, description="自定义提示词")
    model: Optional[str] = Field(default=None, description="模型名称")
    size: Optional[str] = Field(default=None, description="图片尺寸")
    quantity: Optional[int] = Field(default=None, description="生成数量")
    task_id: Optional[int] = Field(default=None, description="生成任务ID")
    positive_prompt: Optional[str] = Field(default=None, description="正向提示词")
    negative_prompt: Optional[str] = Field(default=None, description="负向提示词")
    image_urls: List[str] = Field(default=[], description="生成的图片URL列表")
    saved_count: Optional[int] = Field(default=None, description="保存的图片数量")
    image_asset_ids: List[int] = Field(default=[], description="图片资产ID列表")

    # 批量导出工作流状态
    export_preset_id: Optional[int] = Field(default=None, description="导出预设ID")
    asset_request_ids: List[int] = Field(default=[], description="资产需求ID列表")
    batch_name: Optional[str] = Field(default=None, description="批次名称")
    filtered_assets: List[Dict[str, Any]] = Field(default=[], description="筛选后的资产列表")
    processed_assets: List[Dict[str, Any]] = Field(default=[], description="处理后的资产列表")
    export_batch_id: Optional[int] = Field(default=None, description="导出批次ID")
    manifest: Dict[str, Any] = Field(default={}, description="manifest JSON")
    export_path: Optional[str] = Field(default=None, description="导出包路径")

    # 批量生成工作流状态
    tasks: List[Dict[str, Any]] = Field(default=[], description="任务列表")
    results: List[Dict[str, Any]] = Field(default=[], description="生成结果列表")
    total_images: Optional[int] = Field(default=None, description="总共生成的图片数量")
    success_count: Optional[int] = Field(default=None, description="成功数量")
    failed_count: Optional[int] = Field(default=None, description="失败数量")


class WorkflowRouterOutput(BaseModel):
    """工作流路由节点的输出"""
    workflow_type: str = Field(default="", description="工作流类型")
    asset_request_id: Optional[int] = Field(default=None, description="资产需求ID")
    prompt_template_id: Optional[int] = Field(default=None, description="提示词模板ID")
    custom_prompt: Optional[str] = Field(default=None, description="自定义提示词")
    model: Optional[str] = Field(default=None, description="模型名称")
    size: Optional[str] = Field(default=None, description="图片尺寸")
    quantity: Optional[int] = Field(default=None, description="生成数量")
    export_preset_id: Optional[int] = Field(default=None, description="导出预设ID")
    asset_request_ids: Optional[List[int]] = Field(default=None, description="资产需求ID列表")
    batch_name: Optional[str] = Field(default=None, description="批次名称")


# ============ 图输入输出定义 ============

class GraphInput(BaseModel):
    """工作流的输入"""
    workflow_type: str = Field(..., description="工作流类型：image_generation/batch_export/batch_generation")
    asset_request_id: Optional[int] = Field(default=None, description="资产需求ID（生图工作流）")
    prompt_template_id: Optional[int] = Field(default=None, description="提示词模板ID")
    custom_prompt: Optional[str] = Field(default=None, description="自定义提示词")
    model: str = Field(default="doubao-seedream-5-0-260128", description="模型名称")
    size: str = Field(default="2K", description="图片尺寸")
    quantity: int = Field(default=1, description="生成数量")
    export_preset_id: Optional[int] = Field(default=None, description="导出预设ID")
    asset_request_ids: List[int] = Field(default=[], description="资产需求ID列表")
    batch_name: Optional[str] = Field(default=None, description="批次名称")


class GraphOutput(BaseModel):
    """工作流的输出"""
    workflow_type: str = Field(..., description="工作流类型")
    task_id: Optional[int] = Field(default=None, description="任务ID")
    image_urls: List[str] = Field(default=[], description="图片URL列表")
    export_batch_id: Optional[int] = Field(default=None, description="导出批次ID")
    manifest: Dict[str, Any] = Field(default={}, description="manifest JSON")
    export_path: Optional[str] = Field(default=None, description="导出包路径")
    total_images: Optional[int] = Field(default=None, description="总共生成的图片数量")
    success_count: Optional[int] = Field(default=None, description="成功数量")
    failed_count: Optional[int] = Field(default=None, description="失败数量")
    task_ids: List[int] = Field(default=[], description="批量生成的任务ID列表")


# ========== 批量生成循环状态 ==========

class BatchGenerationLoopInput(BaseModel):
    """批量生成循环子图的输入"""
    asset_request_ids: List[int] = Field(default=[], description="待生成的资产需求ID列表")
    prompt_template_id: Optional[int] = Field(default=None, description="提示词模板ID")
    model: str = Field(default="doubao-seedream-5-0-260128", description="模型名称")
    size: str = Field(default="1024x1024", description="图片尺寸")
    quantity: int = Field(default=1, description="每个资产生成的图片数量")


class BatchGenerationLoopState(BaseModel):
    """批量生成循环的全局状态"""
    asset_request_ids: List[int] = Field(default=[], description="待生成的资产需求ID列表")
    prompt_template_id: Optional[int] = Field(default=None, description="提示词模板ID")
    model: str = Field(default="doubao-seedream-5-0-260128", description="模型名称")
    size: str = Field(default="1024x1024", description="图片尺寸")
    quantity: int = Field(default=1, description="每个资产生成的图片数量")
    current_index: int = Field(default=0, description="当前处理的索引")
    current_task_id: Optional[int] = Field(default=None, description="当前任务ID")
    current_prompt: str = Field(default="", description="当前提示词")
    current_image_urls: List[str] = Field(default=[], description="当前图片URL列表")
    task_ids: List[int] = Field(default=[], description="已生成的任务ID列表")
    image_urls: List[str] = Field(default=[], description="已生成的图片URL列表")
    success_count: int = Field(default=0, description="成功数量")
    failed_count: int = Field(default=0, description="失败数量")
    error_messages: List[str] = Field(default=[], description="错误信息列表")
    cancelled: bool = Field(default=False, description="是否已取消")
    progress_percent: float = Field(default=0.0, description="进度百分比")
    current_asset_name: str = Field(default="", description="当前处理的资产名称")


class BatchGenerationLoopOutput(BaseModel):
    """批量生成循环子图的输出"""
    task_ids: List[int] = Field(default=[], description="所有任务ID列表")
    image_urls: List[str] = Field(default=[], description="所有图片URL列表")
    total_count: int = Field(default=0, description="总数量")
    success_count: int = Field(default=0, description="成功数量")
    failed_count: int = Field(default=0, description="失败数量")


# ========== 批量生成包装节点状态 ==========

class BatchGenerationWrapperInput(BaseModel):
    """批量生成包装节点的输入"""
    asset_request_ids: List[int] = Field(..., description="待生成的资产需求ID列表")
    prompt_template_id: Optional[int] = Field(default=None, description="提示词模板ID")
    model: Optional[str] = Field(default=None, description="模型名称")
    size: Optional[str] = Field(default=None, description="图片尺寸")
    quantity: Optional[int] = Field(default=None, description="每个资产生成的图片数量")


class BatchGenerationWrapperOutput(BaseModel):
    """批量生成包装节点的输出"""
    task_ids: List[int] = Field(default=[], description="所有任务ID列表")
    image_urls: List[str] = Field(default=[], description="所有图片URL列表")
    total_images: int = Field(default=0, description="总数量")
    success_count: int = Field(default=0, description="成功数量")
    failed_count: int = Field(default=0, description="失败数量")
    error_messages: List[str] = Field(default=[], description="错误信息列表")
    progress_percent: float = Field(default=0.0, description="进度百分比")
    current_asset_name: str = Field(default="", description="当前处理的资产名称")


class QualityAssessmentInput(BaseModel):
    """图片质量评估节点的输入"""
    image_url: str = Field(..., description="待评估的图片URL")
    task_id: int = Field(..., description="生成任务ID")
    request_id: int = Field(..., description="资产需求ID")


class QualityAssessmentOutput(BaseModel):
    """图片质量评估节点的输出"""
    image_url: str = Field(..., description="评估的图片URL")
    task_id: int = Field(..., description="生成任务ID")
    request_id: int = Field(..., description="资产需求ID")
    quality_score: float = Field(default=0.0, description="综合质量评分（0-100）")
    edge_clarity: float = Field(default=0.0, description="边缘清晰度评分（0-100）")
    color_saturation: float = Field(default=0.0, description="色彩饱和度评分（0-100）")
    aesthetic_score: float = Field(default=0.0, description="整体美观度评分（0-100）")
    quality_issues: List[str] = Field(default=[], description="检测到的质量问题列表")
    is_qualified: bool = Field(default=False, description="是否合格（综合评分>=70）")
    assessment_report: Dict[str, Any] = Field(default={}, description="完整评估报告JSON")