"""CRUD API 路由 - 资产、节点、模板等的增删改查"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func

from storage.database.db import get_session
from storage.database.shared.model import (
    Project, Node, AssetRequest, ImageAsset,
    PromptTemplate, GenerationTask, ExportPreset, ExportBatch
)

router = APIRouter(prefix="/api", tags=["crud"])

# ============ Pydantic Models ============

class AssetCreate(BaseModel):
    name: str
    asset_type: str
    node_id: int
    description: Optional[str] = ""
    priority: Optional[str] = "普通"

class AssetUpdate(BaseModel):
    name: Optional[str] = None
    asset_type: Optional[str] = None
    node_id: Optional[int] = None
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None

class NodeCreate(BaseModel):
    name: str
    project_id: int = 1
    parent_id: Optional[int] = None

class NodeUpdate(BaseModel):
    name: Optional[str] = None
    parent_id: Optional[int] = None

class ImageAssetUpdate(BaseModel):
    status: Optional[str] = None
    is_final: Optional[bool] = None

# ============ 节点 API ============

@router.get("/nodes")
def get_nodes(project_id: int = 1):
    """获取节点树"""
    db = get_session()
    try:
        nodes = db.query(Node).filter(Node.project_id == project_id).order_by(Node.sort_order).all()
        
        # 构建树形结构
        node_map = {}
        roots = []
        
        for n in nodes:
            node_dict = {
                "id": n.id,
                "name": n.name,
                "parent_id": n.parent_id,
                "node_type": n.node_type,
                "children": []
            }
            node_map[n.id] = node_dict
        
        for n in nodes:
            if n.parent_id and n.parent_id in node_map:
                node_map[n.parent_id]["children"].append(node_map[n.id])
            else:
                roots.append(node_map[n.id])
        
        return {"nodes": roots}
    finally:
        db.close()

@router.post("/nodes")
def create_node(data: NodeCreate):
    """创建节点"""
    db = get_session()
    try:
        node = Node(
            project_id=data.project_id,
            parent_id=data.parent_id,
            name=data.name,
            node_type="category"
        )
        db.add(node)
        db.commit()
        db.refresh(node)
        return {"id": node.id, "name": node.name, "message": "创建成功"}
    finally:
        db.close()

@router.put("/nodes/{node_id}")
def update_node(node_id: int, data: NodeUpdate):
    """更新节点"""
    db = get_session()
    try:
        node = db.query(Node).filter(Node.id == node_id).first()
        if not node:
            raise HTTPException(status_code=404, detail="节点不存在")
        if data.name is not None:
            node.name = data.name
        if data.parent_id is not None:
            node.parent_id = data.parent_id
        db.commit()
        return {"message": "更新成功"}
    finally:
        db.close()

@router.delete("/nodes/{node_id}")
def delete_node(node_id: int):
    """删除节点"""
    db = get_session()
    try:
        node = db.query(Node).filter(Node.id == node_id).first()
        if not node:
            raise HTTPException(status_code=404, detail="节点不存在")
        db.delete(node)
        db.commit()
        return {"message": "删除成功"}
    finally:
        db.close()

# ============ 资产需求 API ============

@router.get("/assets")
def get_assets(
    node_id: Optional[int] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100)
):
    """获取资产列表"""
    db = get_session()
    try:
        query = db.query(AssetRequest)
        
        if node_id:
            # 获取该节点及其子节点下的所有资产
            child_ids = db.query(Node.id).filter(Node.parent_id == node_id).all()
            node_ids = [node_id] + [c[0] for c in child_ids]
            query = query.filter(AssetRequest.node_id.in_(node_ids))
        
        if status:
            query = query.filter(AssetRequest.status == status)
        
        if search:
            query = query.filter(AssetRequest.name.contains(search))
        
        total = query.count()
        assets = query.order_by(AssetRequest.created_at.desc()).offset((page-1)*page_size).limit(page_size).all()
        
        result = []
        for a in assets:
            # 获取候选图
            candidates = db.query(ImageAsset).filter(ImageAsset.asset_request_id == a.id).all()
            
            # 获取节点名称
            node = db.query(Node).filter(Node.id == a.node_id).first()
            
            result.append({
                "id": a.id,
                "name": a.name,
                "type": a.asset_type,
                "rarity": a.priority,
                "status": a.status,
                "description": a.description or "",
                "node_id": a.node_id,
                "node_name": node.name if node else "",
                "candidates": [
                    {
                        "id": c.id,
                        "url": c.file_url,
                        "finalized": c.is_final,
                        "quality_score": c.quality_score,
                        "version": c.version
                    }
                    for c in candidates
                ],
                "created_at": a.created_at.strftime("%Y-%m-%d") if a.created_at else "",
            })
        
        return {"assets": result, "total": total, "page": page, "page_size": page_size}
    finally:
        db.close()

@router.get("/assets/{asset_id}")
def get_asset(asset_id: int):
    """获取单个资产详情"""
    db = get_session()
    try:
        a = db.query(AssetRequest).filter(AssetRequest.id == asset_id).first()
        if not a:
            raise HTTPException(status_code=404, detail="资产不存在")
        
        candidates = db.query(ImageAsset).filter(ImageAsset.asset_request_id == a.id).all()
        node = db.query(Node).filter(Node.id == a.node_id).first()
        
        return {
            "id": a.id,
            "name": a.name,
            "type": a.asset_type,
            "rarity": a.priority,
            "status": a.status,
            "description": a.description or "",
            "node_id": a.node_id,
            "node_name": node.name if node else "",
            "candidates": [
                {
                    "id": c.id,
                    "url": c.file_url,
                    "finalized": c.is_final,
                    "quality_score": c.quality_score,
                    "version": c.version
                }
                for c in candidates
            ],
            "created_at": a.created_at.strftime("%Y-%m-%d") if a.created_at else "",
        }
    finally:
        db.close()

@router.post("/assets")
def create_asset(data: AssetCreate):
    """创建资产"""
    db = get_session()
    try:
        asset = AssetRequest(
            node_id=data.node_id,
            name=data.name,
            asset_type=data.asset_type,
            description=data.description,
            priority=data.priority,
            status="待生成"
        )
        db.add(asset)
        db.commit()
        db.refresh(asset)
        return {"id": asset.id, "name": asset.name, "message": "创建成功"}
    finally:
        db.close()

@router.put("/assets/{asset_id}")
def update_asset(asset_id: int, data: AssetUpdate):
    """更新资产"""
    db = get_session()
    try:
        asset = db.query(AssetRequest).filter(AssetRequest.id == asset_id).first()
        if not asset:
            raise HTTPException(status_code=404, detail="资产不存在")
        
        if data.name is not None:
            asset.name = data.name
        if data.asset_type is not None:
            asset.asset_type = data.asset_type
        if data.node_id is not None:
            asset.node_id = data.node_id
        if data.description is not None:
            asset.description = data.description
        if data.status is not None:
            asset.status = data.status
        if data.priority is not None:
            asset.priority = data.priority
        
        db.commit()
        return {"message": "更新成功"}
    finally:
        db.close()

@router.delete("/assets/{asset_id}")
def delete_asset(asset_id: int):
    """删除资产"""
    db = get_session()
    try:
        asset = db.query(AssetRequest).filter(AssetRequest.id == asset_id).first()
        if not asset:
            raise HTTPException(status_code=404, detail="资产不存在")
        db.delete(asset)
        db.commit()
        return {"message": "删除成功"}
    finally:
        db.close()

# ============ 图片资产 API ============

@router.put("/images/{image_id}/finalize")
def toggle_finalize(image_id: int):
    """切换图片定稿状态"""
    db = get_session()
    try:
        img = db.query(ImageAsset).filter(ImageAsset.id == image_id).first()
        if not img:
            raise HTTPException(status_code=404, detail="图片不存在")
        
        img.is_final = not img.is_final
        img.status = "最终" if img.is_final else "候选"
        db.commit()
        
        return {"is_final": img.is_final, "status": img.status}
    finally:
        db.close()

# ============ 模板 API ============

@router.get("/templates")
def get_templates():
    """获取提示词模板"""
    db = get_session()
    try:
        templates = db.query(PromptTemplate).all()
        return {
            "templates": [
                {
                    "id": t.id,
                    "name": t.name,
                    "positive_prompt": t.positive_prompt,
                    "negative_prompt": t.negative_prompt,
                }
                for t in templates
            ]
        }
    finally:
        db.close()

# ============ 导出预设 API ============

@router.get("/presets")
def get_presets():
    """获取导出预设"""
    db = get_session()
    try:
        presets = db.query(ExportPreset).all()
        return {
            "presets": [
                {
                    "id": p.id,
                    "name": p.name,
                    "width": p.final_width,
                    "height": p.final_height,
                    "padding": p.padding,
                    "remove_background": p.remove_background,
                }
                for p in presets
            ]
        }
    finally:
        db.close()

# ============ 统计 API ============

@router.get("/stats")
def get_stats():
    """获取统计数据"""
    db = get_session()
    try:
        total = db.query(AssetRequest).count()
        by_status = dict(
            db.query(AssetRequest.status, func.count(AssetRequest.id))
            .group_by(AssetRequest.status)
            .all()
        )
        by_type = dict(
            db.query(AssetRequest.asset_type, func.count(AssetRequest.id))
            .group_by(AssetRequest.asset_type)
            .all()
        )
        
        return {
            "total": total,
            "by_status": by_status,
            "by_type": by_type,
        }
    finally:
        db.close()


# ============ 版本管理 API ============

@router.get("/assets/{asset_id}/versions")
def get_asset_versions(asset_id: int):
    """获取资产的版本历史"""
    db = get_session()
    try:
        asset = db.query(AssetRequest).filter(AssetRequest.id == asset_id).first()
        if not asset:
            raise HTTPException(status_code=404, detail="资产不存在")

        # 获取所有版本的任务
        tasks = db.query(GenerationTask).filter(
            GenerationTask.asset_request_id == asset_id
        ).order_by(GenerationTask.version.desc()).all()

        versions = []
        for task in tasks:
            # 获取该任务生成的图片
            images = db.query(ImageAsset).filter(
                ImageAsset.generation_task_id == task.id
            ).all()

            versions.append({
                "version": task.version,
                "task_id": task.id,
                "model": task.model,
                "size": task.size,
                "prompt": task.positive_prompt,
                "status": task.status,
                "created_at": task.created_at.strftime("%Y-%m-%d %H:%M") if task.created_at else "",
                "images": [
                    {
                        "id": img.id,
                        "url": img.file_url,
                        "is_final": img.is_final,
                        "quality_score": img.quality_score
                    }
                    for img in images
                ],
                "image_count": len(images)
            })

        return {
            "asset_id": asset_id,
            "asset_name": asset.name,
            "versions": versions,
            "total_versions": len(versions)
        }
    finally:
        db.close()


@router.post("/assets/{asset_id}/regenerate")
def regenerate_asset(asset_id: int):
    """重新生成资产（创建新版本）"""
    db = get_session()
    try:
        asset = db.query(AssetRequest).filter(AssetRequest.id == asset_id).first()
        if not asset:
            raise HTTPException(status_code=404, detail="资产不存在")

        # 获取当前最大版本号
        max_version = db.query(func.max(GenerationTask.version)).filter(
            GenerationTask.asset_request_id == asset_id
        ).scalar() or 0

        new_version = max_version + 1

        # 创建新版本的任务
        task = GenerationTask(
            asset_request_id=asset_id,
            model="doubao-seedream-5-0-260128",
            size="2K",
            positive_prompt=f"重新生成: {asset.name}",
            quantity=1,
            status="排队中",
            version=new_version
        )
        db.add(task)
        db.commit()
        db.refresh(task)

        # 更新资产状态
        asset.status = "生成中"
        db.commit()

        return {
            "message": f"已创建版本 {new_version} 的生成任务",
            "task_id": task.id,
            "version": new_version
        }
    finally:
        db.close()


@router.get("/assets/{asset_id}/versions/{version}")
def get_asset_version_detail(asset_id: int, version: int):
    """获取指定版本详情"""
    db = get_session()
    try:
        task = db.query(GenerationTask).filter(
            GenerationTask.asset_request_id == asset_id,
            GenerationTask.version == version
        ).first()

        if not task:
            raise HTTPException(status_code=404, detail="版本不存在")

        images = db.query(ImageAsset).filter(
            ImageAsset.generation_task_id == task.id
        ).all()

        return {
            "version": task.version,
            "task_id": task.id,
            "model": task.model,
            "size": task.size,
            "prompt": task.positive_prompt,
            "status": task.status,
            "created_at": task.created_at.strftime("%Y-%m-%d %H:%M") if task.created_at else "",
            "images": [
                {
                    "id": img.id,
                    "url": img.file_url,
                    "is_final": img.is_final,
                    "quality_score": img.quality_score,
                    "edge_clarity": img.edge_clarity,
                    "color_saturation": img.color_saturation
                }
                for img in images
            ]
        }
    finally:
        db.close()


# ============ 批量生成进度 API ============

# 内存中存储批量进度（生产环境应使用Redis）
batch_progress_store = {}

class BatchProgress:
    """批量生成进度"""
    def __init__(self, run_id: str, total_count: int):
        self.run_id = run_id
        self.total_count = total_count
        self.completed_count = 0
        self.success_count = 0
        self.failed_count = 0
        self.status = "running"
        self.current_asset_name = ""
        self.errors = []
    
    def update(self, success: bool, asset_name: str = "", error: str = ""):
        self.completed_count += 1
        if success:
            self.success_count += 1
        else:
            self.failed_count += 1
            if error:
                self.errors.append(error)
        self.current_asset_name = asset_name
    
    def complete(self):
        self.status = "completed"
    
    def fail(self, error: str):
        self.status = "failed"
        self.errors.append(error)
    
    def cancel(self):
        self.status = "cancelled"
    
    def to_dict(self):
        return {
            "run_id": self.run_id,
            "status": self.status,
            "total_count": self.total_count,
            "completed_count": self.completed_count,
            "success_count": self.success_count,
            "failed_count": self.failed_count,
            "progress_percent": (self.completed_count / self.total_count * 100) if self.total_count > 0 else 0,
            "current_asset": self.current_asset_name,
            "errors": self.errors
        }

@router.get("/batch/{run_id}/progress")
def get_batch_progress(run_id: str):
    """获取批量生成进度"""
    progress = batch_progress_store.get(run_id)
    if not progress:
        raise HTTPException(status_code=404, detail="批量任务不存在")
    return progress.to_dict()

@router.post("/batch/{run_id}/cancel")
def cancel_batch(run_id: str):
    """取消批量生成"""
    progress = batch_progress_store.get(run_id)
    if not progress:
        raise HTTPException(status_code=404, detail="批量任务不存在")
    progress.cancel()
    return {"message": "已发送取消信号", "run_id": run_id}

@router.post("/batch/{run_id}/update")
def update_batch_progress(run_id: str, success: bool, asset_name: str = "", error: str = ""):
    """更新批量生成进度（内部调用）"""
    progress = batch_progress_store.get(run_id)
    if not progress:
        raise HTTPException(status_code=404, detail="批量任务不存在")
    progress.update(success, asset_name, error)
    return progress.to_dict()


# ============ 导出历史 API ============

@router.get("/exports")
def get_exports():
    """获取导出历史"""
    db = get_session()
    try:
        exports = db.query(ExportBatch).order_by(ExportBatch.created_at.desc()).limit(50).all()
        return {
            "exports": [
                {
                    "id": e.id,
                    "name": e.name,
                    "file_count": e.file_count,
                    "export_path": e.export_path,
                    "created_at": e.created_at.strftime("%Y-%m-%d %H:%M:%S") if e.created_at else ""
                }
                for e in exports
            ]
        }
    finally:
        db.close()
