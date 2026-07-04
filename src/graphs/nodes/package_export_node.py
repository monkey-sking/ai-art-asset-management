"""
打包导出节点
将处理后的图片打包成ZIP文件，并生成manifest JSON
"""
import json
import logging
import os
import zipfile
from io import BytesIO
import tempfile
from datetime import datetime
from typing import Any, Dict, List
from langchain_core.runnables import RunnableConfig
from langgraph.runtime import Runtime
from coze_coding_utils.runtime_ctx.context import Context
from coze_coding_dev_sdk.s3 import S3SyncStorage
from graphs.state import PackageExportInput, PackageExportOutput

logger = logging.getLogger(__name__)


def package_export_node(state: PackageExportInput, config: RunnableConfig, runtime: Runtime[Context]) -> PackageExportOutput:
    """
    title: 打包导出
    desc: 将处理后的图片打包成ZIP文件，并生成manifest JSON
    integrations: 对象存储
    """
    ctx = runtime.context
    
    # 参数验证
    batch_name = state.batch_name
    processed_assets = state.processed_assets
    
    if batch_name is None:
        raise Exception("batch_name 参数缺失")
    if not processed_assets:
        raise Exception("processed_assets 参数缺失或为空列表")
    
    storage = S3SyncStorage(
        endpoint_url=os.getenv("COZE_BUCKET_ENDPOINT_URL"),
        access_key="",
        secret_key="",
        bucket_name=os.getenv("COZE_BUCKET_NAME"),
        region="cn-beijing",
    )

    try:
        # 1. 生成manifest JSON
        manifest: Dict[str, Any] = {
            'batch_name': batch_name,
            'created_at': datetime.now().isoformat(),
            'file_count': len(processed_assets),
            'files': []
        }

        # 2. 创建临时ZIP文件
        temp_zip_path = tempfile.mktemp(suffix='.zip')

        with zipfile.ZipFile(temp_zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for asset in processed_assets:
                # 生成文件名（根据命名规则）
                asset_code = asset.get('asset_code', '')
                asset_name = asset.get('asset_name', '未命名')
                if asset_code:
                    file_name = f"{asset_code}.png"
                else:
                    file_name = f"{asset_name}.png"

                # 下载处理后的图片
                processed_file_key = asset.get('processed_file_key', '')
                processed_data = storage.read_file(file_key=processed_file_key)

                # 添加到ZIP文件
                zipf.writestr(file_name, processed_data)

                # 添加到manifest
                manifest['files'].append({
                    'file_name': file_name,
                    'asset_name': asset_name,
                    'asset_code': asset_code,
                    'asset_type': asset.get('asset_type', ''),
                    'width': asset.get('processed_width', 0),
                    'height': asset.get('processed_height', 0),
                    'status': '最终'
                })

        # 3. 上传ZIP文件到对象存储
        with open(temp_zip_path, 'rb') as f:
            zip_data = f.read()

        zip_file_name = f"exports/{batch_name}.zip"
        export_file_key = storage.upload_file(
            file_content=zip_data,
            file_name=zip_file_name,
            content_type="application/zip"
        )

        # 生成访问URL
        export_url = storage.generate_presigned_url(key=export_file_key, expire_time=86400)  # 1天有效期

        # 4. 清理临时文件
        os.remove(temp_zip_path)

        logger.info(f"打包导出成功: {batch_name}, 文件数={len(processed_assets)}")

        return PackageExportOutput(
            export_path=export_url,
            manifest=manifest
        )

    except Exception as e:
        logger.error(f"打包导出失败: {str(e)}")
        raise e