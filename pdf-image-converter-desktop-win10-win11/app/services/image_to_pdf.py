# -*- coding: utf-8 -*-
"""
图片转 PDF 服务模块
使用 Pillow 将图片转换为 PDF，支持多图合并、页面尺寸设置、透明背景处理。
"""

from pathlib import Path
from PIL import Image
from app.services.file_utils import resolve_file_conflict, ensure_output_dir, rgba_to_rgb
from app.config.settings import Settings

# A4 尺寸（像素，300 DPI）
A4_WIDTH_PX = 2480
A4_HEIGHT_PX = 3508


def _get_page_size(page_size_mode, image_size):
    """根据页面尺寸模式返回实际页面尺寸"""
    if page_size_mode == "a4_portrait":
        return (A4_WIDTH_PX, A4_HEIGHT_PX)
    elif page_size_mode == "a4_landscape":
        return (A4_HEIGHT_PX, A4_WIDTH_PX)
    return image_size


def _fit_image_to_page(image, page_size, placement="fit"):
    """将图片适配到页面尺寸"""
    page_w, page_h = page_size
    img_w, img_h = image.size

    if placement == "fit":
        ratio = min(page_w / img_w, page_h / img_h)
        new_w = int(img_w * ratio)
        new_h = int(img_h * ratio)
        resized = image.resize((new_w, new_h), Image.LANCZOS)
        page_img = Image.new("RGB", (page_w, page_h), (255, 255, 255))
        page_img.paste(resized, ((page_w - new_w) // 2, (page_h - new_h) // 2))
        return page_img
    elif placement == "center":
        page_img = Image.new("RGB", (page_w, page_h), (255, 255, 255))
        page_img.paste(image, ((page_w - img_w) // 2, (page_h - img_h) // 2))
        return page_img
    else:  # no_crop
        ratio = min(page_w / img_w, page_h / img_h)
        new_w = int(img_w * ratio)
        new_h = int(img_h * ratio)
        resized = image.resize((new_w, new_h), Image.LANCZOS)
        page_img = Image.new("RGB", (page_w, page_h), (255, 255, 255))
        page_img.paste(resized, ((page_w - new_w) // 2, (page_h - new_h) // 2))
        return page_img


def convert_images_to_pdf(
    image_paths,
    output_path,
    page_size_mode="original",
    placement="fit",
    quality=90,
    merge=True,
    on_progress=None,
    on_log=None,
):
    """
    将图片转换为 PDF。

    参数:
        image_paths: 图片文件路径列表
        output_path: 输出路径（合并模式为文件路径，单独模式为目录路径）
        page_size_mode: 页面尺寸 original/a4_portrait/a4_landscape
        placement: 放置方式 fit/center/no_crop
        quality: 图片质量，默认 90
        merge: True 合并为一个 PDF，False 每张单独转
        on_progress/on_log: 回调函数

    返回:
        生成的 PDF 文件路径列表
    """
    if not image_paths:
        raise ValueError("没有选择任何图片文件")

    settings = Settings()
    result_files = []

    if merge:
        pdf_images = []
        total = len(image_paths)
        for idx, img_path in enumerate(image_paths):
            if on_progress:
                on_progress(idx + 1, total, img_path.name)
            try:
                img = Image.open(str(img_path))
                img = rgba_to_rgb(img)
                page_size = _get_page_size(page_size_mode, img.size) if page_size_mode != "original" else img.size
                page_img = _fit_image_to_page(img, page_size, placement)
                pdf_images.append(page_img)
                if on_log:
                    on_log(f"已添加：{img_path.name}")
            except Exception as e:
                if on_log:
                    on_log(f"处理图片失败 {img_path.name}：{str(e)}")
                continue

        if not pdf_images:
            raise ValueError("没有成功处理任何图片")

        out_path = Path(output_path)
        if settings.get("file_conflict_mode") == "rename":
            out_path = resolve_file_conflict(out_path)

        first_image = pdf_images[0]
        rest_images = pdf_images[1:] if len(pdf_images) > 1 else []
        first_image.save(str(out_path), "PDF", save_all=True, append_images=rest_images, quality=quality)
        result_files.append(out_path)
        if on_log:
            on_log(f"合并完成：{out_path.name}，共 {len(pdf_images)} 页")
    else:
        output_dir = ensure_output_dir(Path(output_path))
        total = len(image_paths)
        for idx, img_path in enumerate(image_paths):
            if on_progress:
                on_progress(idx + 1, total, img_path.name)
            try:
                img = Image.open(str(img_path))
                img = rgba_to_rgb(img)
                page_size = _get_page_size(page_size_mode, img.size) if page_size_mode != "original" else img.size
                page_img = _fit_image_to_page(img, page_size, placement)
                out_name = f"{img_path.stem}.pdf"
                out_path = output_dir / out_name
                if settings.get("file_conflict_mode") == "rename":
                    out_path = resolve_file_conflict(out_path)
                page_img.save(str(out_path), "PDF", quality=quality)
                result_files.append(out_path)
                if on_log:
                    on_log(f"已转换：{img_path.name} -> {out_path.name}")
            except Exception as e:
                if on_log:
                    on_log(f"转换失败 {img_path.name}：{str(e)}")
                continue

    return result_files
