"""
处理图片节点
根据导出预设，处理图片：去白底、调整尺寸、补边距
"""
import json
import logging
import os
import requests
from io import BytesIO
from typing import Any, Dict, List
from PIL import Image
from langchain_core.runnables import RunnableConfig
from langgraph.runtime import Runtime
from coze_coding_utils.runtime_ctx.context import Context
from coze_coding_dev_sdk.s3 import S3SyncStorage
from storage.database.supabase_client import get_supabase_client
from postgrest.exceptions import APIError
from graphs.state import ProcessImagesInput, ProcessImagesOutput

logger = logging.getLogger(__name__)


def process_images_node(state: ProcessImagesInput, config: RunnableConfig, runtime: Runtime[Context]) -> ProcessImagesOutput:
    """
    title: 处理图片
    desc: 根据导出预设，处理图片：去白底、调整尺寸、补边距
    integrations: 对象存储、Supabase、PIL
    """
    ctx = runtime.context
    
    # 参数验证
    export_preset_id = state.export_preset_id
    filtered_assets = state.filtered_assets
    
    if export_preset_id is None:
        raise Exception("export_preset_id 参数缺失")
    if not filtered_assets:
        raise Exception("filtered_assets 参数缺失或为空列表")
    
    storage = S3SyncStorage(
        endpoint_url=os.getenv("COZE_BUCKET_ENDPOINT_URL"),
        access_key="",
        secret_key="",
        bucket_name=os.getenv("COZE_BUCKET_NAME"),
        region="cn-beijing",
    )
    db_client = get_supabase_client()

    try:
        # 1. 查询导出预设
        preset_response = db_client.table('export_presets').select('*').eq('id', export_preset_id).maybe_single().execute()
        if preset_response is None or preset_response.data is None:
            raise Exception(f"导出预设ID {export_preset_id} 不存在")
        
        preset: Dict[str, Any] = preset_response.data

        # 显式类型声明和转换
        final_width: int = int(preset.get('final_width', 256))
        final_height: int = int(preset.get('final_height', 256))
        padding: int = int(preset.get('padding', 0))
        remove_background: bool = bool(preset.get('remove_background', False))
        white_threshold: int = int(preset.get('white_threshold', 240))

        processed_assets: List[Dict[str, Any]] = []

        # 2. 遍历资产，处理图片
        for asset in filtered_assets:
            try:
                # 下载图片
                file_url = asset.get('file_url', '')
                response = requests.get(file_url, timeout=30)
                if response.status_code != 200:
                    logger.error(f"下载图片失败: {file_url}")
                    continue

                image_data = response.content
                image = Image.open(BytesIO(image_data))

                # 去白底
                if remove_background:
                    image = image.convert('RGBA')
                    datas = image.getdata()
                    newData: List[tuple] = []
                    # 使用 iter() 显式迭代
                    for item in iter(datas):
                        # 判断是否接近白色（阈值范围内）
                        if isinstance(item, tuple) and len(item) >= 3:
                            if item[0] > white_threshold and item[1] > white_threshold and item[2] > white_threshold:
                                # 将白色变为透明
                                newData.append((255, 255, 255, 0))
                            else:
                                newData.append(item)
                    image.putdata(newData)

                # 调整尺寸（保持比例）
                original_width, original_height = image.size
                target_width = final_width - padding * 2
                target_height = final_height - padding * 2

                # 计算缩放比例
                scale = min(target_width / original_width, target_height / original_height)
                new_width = int(original_width * scale)
                new_height = int(original_height * scale)

                # 缩放图片（使用 Image.Resampling.LANCZOS）
                resized_image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)

                # 创建新图片（带padding）
                final_image = Image.new('RGBA', (final_width, final_height), (0, 0, 0, 0))
                # 计算居中位置
                x = (final_width - new_width) // 2
                y = (final_height - new_height) // 2
                final_image.paste(resized_image, (x, y))

                # 保存处理后的图片到内存
                output_buffer = BytesIO()
                final_image.save(output_buffer, format='PNG')
                processed_data = output_buffer.getvalue()

                # 上传到对象存储
                asset_request_id = asset.get('asset_request_id', 0)
                image_asset_id = asset.get('image_asset_id', 0)
                processed_file_name = f"exports/{asset_request_id}_{image_asset_id}_processed.png"
                processed_file_key = storage.upload_file(
                    file_content=processed_data,
                    file_name=processed_file_name,
                    content_type="image/png"
                )

                # 更新资产信息
                processed_asset = asset.copy()
                processed_asset['processed_file_key'] = processed_file_key
                processed_asset['processed_width'] = final_width
                processed_asset['processed_height'] = final_height

                processed_assets.append(processed_asset)

                logger.info(f"处理图片成功: {asset.get('asset_name', '')}")

            except Exception as e:
                logger.error(f"处理图片失败: {asset.get('asset_name', '')}, {str(e)}")
                continue

        logger.info(f"处理图片完成: 共处理{len(processed_assets)}个资产")

        return ProcessImagesOutput(processed_assets=processed_assets)

    except APIError as e:
        logger.error(f"处理图片失败: {e.message}")
        raise Exception(f"处理图片失败: {e.message}")
    except Exception as e:
        logger.error(f"处理图片失败: {str(e)}")
        raise e