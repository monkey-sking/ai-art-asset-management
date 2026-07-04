from coze_coding_dev_sdk.database import Base

from typing import Optional
import datetime

from sqlalchemy import BigInteger, Boolean, Column, DateTime, Double, Integer, Numeric, PrimaryKeyConstraint, Table, Text, text, String, ForeignKey, Index, JSON, func
from sqlalchemy.dialects.postgresql import OID
from sqlalchemy.orm import Mapped, mapped_column


class HealthCheck(Base):
    __tablename__ = 'health_check'
    __table_args__ = (
        PrimaryKeyConstraint('id', name='health_check_pkey'),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    updated_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(True), server_default=text('now()'))


# ============ AI美术资产生产管理系统数据表 ============

class Project(Base):
    """项目工作区表"""
    __tablename__ = 'projects'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, comment="项目名称")
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="项目描述")
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    __table_args__ = (
        Index("ix_projects_name", "name"),
    )


class Node(Base):
    """节点树结构表"""
    __tablename__ = 'nodes'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(Integer, ForeignKey("projects.id"), nullable=False, comment="所属项目")
    parent_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("nodes.id"), nullable=True, comment="父节点ID")
    name: Mapped[str] = mapped_column(String(255), nullable=False, comment="节点名称")
    node_type: Mapped[str] = mapped_column(String(50), nullable=False, server_default="category", comment="节点类型：category/asset")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0", comment="排序序号")
    prompt_template_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="默认提示词模板ID")
    export_preset_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="默认导出预设ID")
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    __table_args__ = (
        Index("ix_nodes_project_id", "project_id"),
        Index("ix_nodes_parent_id", "parent_id"),
        Index("ix_nodes_name", "name"),
    )


class AssetRequest(Base):
    """资产需求表"""
    __tablename__ = 'asset_requests'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    node_id: Mapped[int] = mapped_column(Integer, ForeignKey("nodes.id"), nullable=False, comment="所属节点")
    name: Mapped[str] = mapped_column(String(255), nullable=False, comment="资产名称")
    asset_type: Mapped[str] = mapped_column(String(50), nullable=False, comment="资产类型：道具/技能/装备/UI")
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="资产描述")
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="待生成", comment="状态：待生成/生成中/待筛选/已定稿/已导出/废弃")
    priority: Mapped[str] = mapped_column(String(20), nullable=False, server_default="普通", comment="优先级：普通/高/紧急")
    asset_code: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, comment="资产编码")
    tags: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="标签")
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="备注")
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    __table_args__ = (
        Index("ix_asset_requests_node_id", "node_id"),
        Index("ix_asset_requests_status", "status"),
        Index("ix_asset_requests_name", "name"),
    )


class ImageAsset(Base):
    """图片资产表"""
    __tablename__ = 'image_assets'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    asset_request_id: Mapped[int] = mapped_column(Integer, ForeignKey("asset_requests.id"), nullable=False, comment="来源需求")
    file_key: Mapped[str] = mapped_column(String(500), nullable=False, comment="对象存储文件key")
    file_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True, comment="临时访问URL")
    generation_task_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("generation_tasks.id"), nullable=True, comment="生成任务ID")
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="候选", comment="状态：候选/最终/废弃")
    is_final: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="False", comment="是否为最终图")
    version: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1", comment="版本号")
    quality_score: Mapped[Optional[float]] = mapped_column(Integer, nullable=True, comment="综合质量评分(0-100)")
    edge_clarity: Mapped[Optional[float]] = mapped_column(Integer, nullable=True, comment="边缘清晰度(0-100)")
    color_saturation: Mapped[Optional[float]] = mapped_column(Integer, nullable=True, comment="色彩饱和度(0-100)")
    aesthetic_score: Mapped[Optional[float]] = mapped_column(Integer, nullable=True, comment="整体美观度(0-100)")
    quality_issues: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="质量问题列表(JSON)")
    width: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="图片宽度")
    height: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="图片高度")
    file_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="文件大小(字节)")
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    __table_args__ = (
        Index("ix_image_assets_asset_request_id", "asset_request_id"),
        Index("ix_image_assets_status", "status"),
        Index("ix_image_assets_generation_task_id", "generation_task_id"),
    )


class PromptTemplate(Base):
    """提示词模板表"""
    __tablename__ = 'prompt_templates'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    node_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="所属节点ID")
    name: Mapped[str] = mapped_column(String(255), nullable=False, comment="模板名称")
    positive_prompt: Mapped[str] = mapped_column(Text, nullable=False, comment="正向提示词")
    negative_prompt: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="负向提示词")
    style_prompt: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="风格提示词")
    variables: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True, comment="变量定义JSON")
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    __table_args__ = (
        Index("ix_prompt_templates_node_id", "node_id"),
        Index("ix_prompt_templates_name", "name"),
    )


class GenerationTask(Base):
    """生成任务表"""
    __tablename__ = 'generation_tasks'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    asset_request_id: Mapped[int] = mapped_column(Integer, ForeignKey("asset_requests.id"), nullable=False, comment="资产需求ID")
    prompt_template_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("prompt_templates.id"), nullable=True, comment="提示词模板ID")
    model: Mapped[str] = mapped_column(String(100), nullable=False, comment="模型名称")
    size: Mapped[str] = mapped_column(String(50), nullable=False, comment="尺寸")
    positive_prompt: Mapped[str] = mapped_column(Text, nullable=False, comment="正向提示词")
    negative_prompt: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="负向提示词")
    quality: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, comment="质量参数")
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1", comment="生成数量")
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="排队中", comment="状态：排队中/生成中/成功/失败/已取消")
    version: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1", comment="版本号")
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="错误信息")
    result_urls: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="生成结果URL列表(JSON)")
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    __table_args__ = (
        Index("ix_generation_tasks_asset_request_id", "asset_request_id"),
        Index("ix_generation_tasks_status", "status"),
        Index("ix_generation_tasks_prompt_template_id", "prompt_template_id"),
    )


class ExportPreset(Base):
    """导出预设表"""
    __tablename__ = 'export_presets'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, comment="预设名称")
    node_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="所属节点ID")
    final_width: Mapped[int] = mapped_column(Integer, nullable=False, comment="最终宽度")
    final_height: Mapped[int] = mapped_column(Integer, nullable=False, comment="最终高度")
    padding: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0", comment="内边距")
    remove_background: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="False", comment="是否去白底")
    white_threshold: Mapped[int] = mapped_column(Integer, nullable=False, server_default="240", comment="白色阈值(0-255)")
    naming_rule: Mapped[str] = mapped_column(String(100), nullable=False, server_default="asset_code", comment="命名规则：asset_code/node_sequence/custom")
    custom_prefix: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, comment="自定义前缀")
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    __table_args__ = (
        Index("ix_export_presets_node_id", "node_id"),
        Index("ix_export_presets_name", "name"),
    )


class ExportBatch(Base):
    """导出批次表"""
    __tablename__ = 'export_batches'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, comment="批次名称")
    project_id: Mapped[int] = mapped_column(Integer, ForeignKey("projects.id"), nullable=False, comment="所属项目")
    export_preset_id: Mapped[int] = mapped_column(Integer, ForeignKey("export_presets.id"), nullable=False, comment="导出预设")
    asset_ids: Mapped[str] = mapped_column(Text, nullable=False, comment="导出的资产ID列表(JSON)")
    file_count: Mapped[int] = mapped_column(Integer, nullable=False, comment="文件数量")
    manifest: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True, comment="manifest JSON")
    export_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True, comment="导出包路径")
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


    __table_args__ = (
        Index("ix_export_batches_project_id", "project_id"),
        Index("ix_export_batches_export_preset_id", "export_preset_id"),
        Index("ix_export_batches_created_at", "created_at"),
    )


