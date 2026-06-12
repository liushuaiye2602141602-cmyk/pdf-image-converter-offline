# -*- coding: utf-8 -*-
"""
图片格式转换/压缩服务模块
支持 PNG、JPG、WebP、BMP、TIFF 之间的相互转换。
"""

from pathlib import Path
from PIL import Image
from app.services.file_utils import resolve_file_conflict, ensure_output_dir, rgba_to_rgb, format_file_size
from app.config.settings import Settings

SUPPORTED_INPUT_FORMATS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff", ".tif"}


def _resize_image(img, resize_mode, width, height, keep_aspect):
    """根据模式调整图片尺寸"""
    if resize_mode == "none":
        return img
    orig_w, orig_h = img.size
    if resize_mode == "by_width":
        if width <= 0:
            return img
        if keep_aspect:
            ratio = width / orig_w
            return img.resize((width, int(orig_h * ratio)), Image.LANCZOS)
        return img.resize((width, orig_h), Image.LANCZOS)
    elif resize_mode == "by_height":
        if height <= 0:
            return img
        if keep_aspect:
            ratio = height / orig_h
            return img.resize((int(orig_w * ratio), height), Image.LANCZOS)
        return img.resize((orig_w, height), Image.LANCZOS)
    elif resize_mode == "custom":
        if width <= 0 or height <= 0:
            return img
        if keep_aspect:
            ratio = min(width / orig_w, height / orig_h)
            return img.resize((int(orig_w * ratio), int(orig_h * ratio)), Image.LANCZOS)
        return img.resize((width, height), Image.LANCZOS)
    return img


def convert_images(
    image_paths,
    output_dir,
    output_format="jpg",
    quality=90,
    resize_mode="none",
    resize_width=0,
    resize_height=0,
    keep_aspect_ratio=True,
    on_progress=None,
    on_log=None,
):
    """
    批量转换图片格式。

    返回: 转换结果列表，每项含 input_path, output_path, input_size, output_size, success, error
    """
    if not image_paths:
        raise ValueError("没有选择任何图片文件")

    output_dir = ensure_output_dir(output_dir)
    settings = Settings()
    results = []
    total = len(image_paths)

    for idx, img_path in enumerate(image_paths):
        if on_progress:
            on_progress(idx + 1, total, img_path.name)

        result = {"input_path": img_path, "output_path": None, "input_size": 0, "output_size": 0, "success": False, "error": ""}
        try:
            result["input_size"] = img_path.stat().st_size
            img = Image.open(str(img_path))
            if output_format in ("jpg", "jpeg"):
                img = rgba_to_rgb(img)
            img = _resize_image(img, resize_mode, resize_width, resize_height, keep_aspect_ratio)

            ext_map = {"jpg": ".jpg", "jpeg": ".jpg", "png": ".png", "webp": ".webp"}
            ext = ext_map.get(output_format, f".{output_format}")
            out_path = output_dir / f"{img_path.stem}{ext}"
            if settings.get("file_conflict_mode") == "rename":
                out_path = resolve_file_conflict(out_path)

            save_kwargs = {}
            if output_format in ("jpg", "jpeg"):
                save_kwargs = {"format": "JPEG", "quality": quality, "optimize": True}
            elif output_format == "png":
                save_kwargs = {"format": "PNG", "optimize": True}
            elif output_format == "webp":
                save_kwargs = {"format": "WEBP", "quality": quality}

            img.save(str(out_path), **save_kwargs)
            result["output_path"] = out_path
            result["output_size"] = out_path.stat().st_size
            result["success"] = True

            if on_log:
                on_log(f"已转换：{img_path.name} ({format_file_size(result['input_size'])}) -> {out_path.name} ({format_file_size(result['output_size'])})")
        except Exception as e:
            result["error"] = str(e)
            if on_log:
                on_log(f"转换失败 {img_path.name}：{str(e)}")
        results.append(result)

    return results
