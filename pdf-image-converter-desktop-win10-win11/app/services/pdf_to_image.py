# -*- coding: utf-8 -*-
"""
PDF 转图片服务模块
使用 PyMuPDF (fitz) 将 PDF 页面导出为 PNG、JPG、WebP 图片。
"""

import fitz  # PyMuPDF
from pathlib import Path
from app.services.file_utils import parse_page_range, resolve_file_conflict, ensure_output_dir
from app.config.settings import Settings


def convert_pdf_to_images(
    pdf_path,
    output_dir,
    output_format="png",
    dpi=300,
    quality=90,
    page_range_str="",
    on_progress=None,
    on_log=None,
):
    """
    将 PDF 转换为图片。

    参数:
        pdf_path: PDF 文件路径
        output_dir: 输出目录
        output_format: 输出格式 (png/jpg/webp)
        dpi: 输出分辨率，默认 300
        quality: 图片质量 (1-100)，默认 90
        page_range_str: 页码范围，空字符串表示全部页面
        on_progress: 进度回调 (当前页, 总页数, 文件名)
        on_log: 日志回调

    返回:
        生成的图片文件路径列表
    """
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF 文件不存在：{pdf_path}")

    # 每个 PDF 创建单独的输出子文件夹
    pdf_stem = pdf_path.stem
    sub_output_dir = ensure_output_dir(output_dir / pdf_stem)

    doc = None
    try:
        doc = fitz.open(str(pdf_path))
        if doc.is_encrypted:
            raise ValueError(f"PDF 文件已加密，无法读取：{pdf_path.name}")

        total_pages = doc.page_count
        if total_pages == 0:
            raise ValueError(f"PDF 文件没有页面：{pdf_path.name}")

        # 解析页码范围
        if page_range_str and page_range_str.strip():
            pages = parse_page_range(page_range_str, total_pages)
        else:
            pages = list(range(total_pages))

        if not pages:
            raise ValueError("没有有效的页码可转换")

        zoom = dpi / 72.0
        matrix = fitz.Matrix(zoom, zoom)
        settings = Settings()
        output_files = []
        total = len(pages)

        for idx, page_num in enumerate(pages):
            if on_progress:
                on_progress(idx + 1, total, pdf_path.name)
            try:
                page = doc.load_page(page_num)
                pixmap = page.get_pixmap(matrix=matrix)
                output_name = f"{pdf_stem}_page_{page_num + 1:03d}.{output_format}"
                output_path = sub_output_dir / output_name
                if settings.get("file_conflict_mode") == "rename":
                    output_path = resolve_file_conflict(output_path)
                pixmap.save(str(output_path))
                output_files.append(output_path)
                if on_log:
                    on_log(f"已转换：{pdf_path.name} 第 {page_num + 1} 页 -> {output_path.name}")
            except Exception as e:
                if on_log:
                    on_log(f"转换第 {page_num + 1} 页失败：{str(e)}")
                continue

        return output_files

    except ValueError:
        raise
    except Exception as e:
        raise RuntimeError(f"打开 PDF 文件失败：{str(e)}")
    finally:
        if doc:
            doc.close()
