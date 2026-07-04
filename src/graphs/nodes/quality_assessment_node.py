"""
图片质量评估节点
使用OpenCV进行图像分析，评估清晰度、色彩、构图等维度
"""
import logging
import json
import os
import tempfile
from typing import Any, Dict, List
from langchain_core.runnables import RunnableConfig
from langgraph.runtime import Runtime
from coze_coding_utils.runtime_ctx.context import Context
from graphs.state import QualityAssessmentInput, QualityAssessmentOutput

logger = logging.getLogger(__name__)


def calculate_edge_clarity(image_path: str) -> float:
    """
    计算边缘清晰度（使用Laplacian方差）
    方差越大表示越清晰
    """
    try:
        import cv2
        import numpy as np

        img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
        if img is None:
            return 50.0  # 默认中等分数

        # Laplacian方差
        laplacian = cv2.Laplacian(img, cv2.CV_64F)
        variance = laplacian.var()

        # 归一化到0-100（经验值：>500为清晰，<100为模糊）
        score = min(100, max(0, variance / 10))
        return round(score, 1)
    except Exception as e:
        logger.warning(f"边缘清晰度计算失败: {e}")
        return 50.0


def calculate_color_saturation(image_path: str) -> float:
    """
    计算色彩饱和度
    使用HSV色彩空间的饱和度通道
    """
    try:
        import cv2
        import numpy as np

        img = cv2.imread(image_path)
        if img is None:
            return 50.0

        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        saturation = hsv[:, :, 1]

        # 平均饱和度，归一化到0-100
        mean_sat = np.mean(saturation)
        score = min(100, max(0, mean_sat / 2.55))
        return round(score, 1)
    except Exception as e:
        logger.warning(f"色彩饱和度计算失败: {e}")
        return 50.0


def calculate_contrast(image_path: str) -> float:
    """
    计算对比度
    使用灰度图的标准差
    """
    try:
        import cv2
        import numpy as np

        img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
        if img is None:
            return 50.0

        std_dev = np.std(img)
        # 归一化到0-100（经验值：>50为高对比度）
        score = min(100, max(0, std_dev / 1.28))
        return round(score, 1)
    except Exception as e:
        logger.warning(f"对比度计算失败: {e}")
        return 50.0


def calculate_aesthetic_score(edge_clarity: float, color_saturation: float, contrast: float) -> float:
    """
    计算综合美观度评分
    加权平均：清晰度40% + 色彩30% + 对比度30%
    """
    score = edge_clarity * 0.4 + color_saturation * 0.3 + contrast * 0.3
    return round(score, 1)


def detect_quality_issues(image_path: str, edge_clarity: float, color_saturation: float, contrast: float) -> List[str]:
    """
    检测质量问题
    """
    issues = []

    if edge_clarity < 30:
        issues.append("图片模糊，边缘不清晰")
    elif edge_clarity < 50:
        issues.append("图片清晰度偏低")

    if color_saturation < 20:
        issues.append("色彩过于平淡")
    elif color_saturation > 90:
        issues.append("色彩过于饱和")

    if contrast < 25:
        issues.append("对比度不足")
    elif contrast > 85:
        issues.append("对比度过高")

    # 检查图片尺寸
    try:
        import cv2
        img = cv2.imread(image_path)
        if img is not None:
            h, w = img.shape[:2]
            if w < 256 or h < 256:
                issues.append(f"图片分辨率过低 ({w}x{h})")
            # 检查是否纯色
            import numpy as np
            std = np.std(img)
            if std < 10:
                issues.append("图片可能为纯色或接近纯色")
    except Exception:
        pass

    return issues


def quality_assessment_node(
    state: QualityAssessmentInput,
    config: RunnableConfig,
    runtime: Runtime[Context]
) -> QualityAssessmentOutput:
    """
    title: 图片质量评估
    desc: 使用OpenCV分析图片质量，计算清晰度、色彩饱和度、对比度等指标
    integrations: OpenCV
    """
    ctx = runtime.context
    image_url = state.image_url

    logger.info(f"[质量评估] 开始评估图片: {image_url}")

    # 默认评分（用于无法下载图片的情况）
    default_score = 70.0
    quality_issues = []

    # 尝试下载图片到临时文件进行分析
    temp_path = None
    try:
        import requests

        # 如果是本地文件路径
        if os.path.exists(image_url):
            temp_path = image_url
        else:
            # 下载远程图片
            response = requests.get(image_url, timeout=30)
            response.raise_for_status()

            # 保存到临时文件
            suffix = '.png'
            if '.jpg' in image_url or '.jpeg' in image_url:
                suffix = '.jpg'
            temp_fd, temp_path = tempfile.mkstemp(suffix=suffix)
            os.write(temp_fd, response.content)
            os.close(temp_fd)

        # 计算各项指标
        edge_clarity = calculate_edge_clarity(temp_path)
        color_saturation = calculate_color_saturation(temp_path)
        contrast = calculate_contrast(temp_path)
        aesthetic_score = calculate_aesthetic_score(edge_clarity, color_saturation, contrast)

        # 检测质量问题
        quality_issues = detect_quality_issues(temp_path, edge_clarity, color_saturation, contrast)

        # 综合评分 = 美观度
        quality_score = aesthetic_score

        # 判断是否合格（>=70分）
        is_qualified = quality_score >= 70

        logger.info(f"[质量评估] 评估完成: 综合={quality_score}, 清晰度={edge_clarity}, 色彩={color_saturation}, 对比度={contrast}")
        if quality_issues:
            logger.warning(f"[质量评估] 发现问题: {quality_issues}")

        return QualityAssessmentOutput(
            image_url=image_url,
            task_id=state.task_id,
            request_id=state.request_id,
            quality_score=quality_score,
            edge_clarity=edge_clarity,
            color_saturation=color_saturation,
            aesthetic_score=aesthetic_score,
            quality_issues=quality_issues,
            is_qualified=is_qualified,
            assessment_report={
                "edge_clarity": edge_clarity,
                "color_saturation": color_saturation,
                "contrast": contrast,
                "aesthetic_score": aesthetic_score,
                "quality_issues": quality_issues,
                "is_qualified": is_qualified
            }
        )

    except ImportError:
        logger.warning("[质量评估] OpenCV未安装，使用默认评分")
        return QualityAssessmentOutput(
            image_url=image_url,
            task_id=state.task_id,
            request_id=state.request_id,
            quality_score=default_score,
            edge_clarity=default_score,
            color_saturation=default_score,
            aesthetic_score=default_score,
            quality_issues=["OpenCV未安装，无法进行质量评估"],
            is_qualified=True,
            assessment_report={"note": "OpenCV未安装，使用默认评分"}
        )

    except Exception as e:
        logger.error(f"[质量评估] 评估失败: {str(e)}")
        return QualityAssessmentOutput(
            image_url=image_url,
            task_id=state.task_id,
            request_id=state.request_id,
            quality_score=default_score,
            edge_clarity=default_score,
            color_saturation=default_score,
            aesthetic_score=default_score,
            quality_issues=[f"评估失败: {str(e)}"],
            is_qualified=True,
            assessment_report={"error": str(e)}
        )

    finally:
        # 清理临时文件
        if temp_path and temp_path != image_url and os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
            except Exception:
                pass
