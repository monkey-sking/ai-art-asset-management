"""
保存生成结果节点
将生成的图片记录到数据库，支持版本管理
使用SQLAlchemy（兼容本地SQLite）
"""
import json
import logging
from typing import Any, Dict
from langchain_core.runnables import RunnableConfig
from langgraph.runtime import Runtime
from coze_coding_utils.runtime_ctx.context import Context
from storage.database.db import get_session
from storage.database.shared.model import GenerationTask, ImageAsset, AssetRequest
from graphs.state import SaveResultsInput, SaveResultsOutput

logger = logging.getLogger(__name__)


def save_results_node(state: SaveResultsInput, config: RunnableConfig, runtime: Runtime[Context]) -> SaveResultsOutput:
    """
    title: 保存生成结果
    desc: 将生成的图片记录到数据库，支持版本管理
    """
    ctx = runtime.context

    # 参数验证
    task_id = state.task_id
    asset_request_id = state.asset_request_id
    image_urls = state.image_urls

    if task_id is None:
        raise Exception("task_id 参数缺失")
    if asset_request_id is None:
        raise Exception("asset_request_id 参数缺失")

    db = get_session()

    try:
        # 获取当前任务
        task = db.query(GenerationTask).filter(GenerationTask.id == task_id).first()
        if not task:
            raise Exception(f"任务不存在: task_id={task_id}")

        # 获取当前资产的最大版本号
        max_version = db.query(GenerationTask.version).filter(
            GenerationTask.asset_request_id == asset_request_id
        ).order_by(GenerationTask.version.desc()).first()
        current_version = max_version if max_version else 1

        saved_count = 0
        image_asset_ids: list[int] = []

        # 遍历所有图片URL，创建图片资产记录
        for idx, image_url in enumerate(image_urls):
            try:
                # 创建图片资产记录
                image_asset = ImageAsset(
                    asset_request_id=asset_request_id,
                    generation_task_id=task_id,
                    file_key=f"assets/{asset_request_id}_{task_id}_{idx + 1}.png",
                    file_url=image_url,
                    status="候选",
                    is_final=False,
                    version=current_version
                )
                db.add(image_asset)
                db.commit()
                db.refresh(image_asset)

                image_asset_ids.append(image_asset.id)
                saved_count += 1

                logger.info(f"保存图片成功: image_asset_id={image_asset.id}")

            except Exception as e:
                logger.error(f"保存图片失败: {image_url}, {str(e)}")
                db.rollback()
                continue

        # 更新任务状态
        task.result_urls = json.dumps(image_urls)
        task.status = "成功"
        task.version = current_version
        db.commit()

        logger.info(f"保存生成结果完成: task_id={task_id}, saved_count={saved_count}, version={current_version}")

        return SaveResultsOutput(
            task_id=task_id,
            saved_count=saved_count,
            image_urls=image_urls,
            image_asset_ids=image_asset_ids
        )

    except Exception as e:
        logger.error(f"保存生成结果失败: {str(e)}")
        db.rollback()
        # 更新任务状态为失败
        task = db.query(GenerationTask).filter(GenerationTask.id == task_id).first()
        if task:
            task.status = "失败"
            task.error_message = str(e)
            db.commit()
        raise e
    finally:
        db.close()
