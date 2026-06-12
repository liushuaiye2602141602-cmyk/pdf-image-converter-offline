# -*- coding: utf-8 -*-
"""
文件工具函数模块
提供页码解析、文件名冲突处理、文件大小格式化、目录创建等通用功能。
"""

from pathlib import Path
from PIL import Image


def parse_page_range(input_str, max_page):
    """
    解析页码范围字符串，返回 0-based 页码列表。
    输入例如 "1-3,5,8-10"，用户输入从 1 开始。
    """
    if not input_str or not input_str.strip():
        raise ValueError("页码范围不能为空")

    pages = set()
    parts = input_str.replace("，", ",").replace(" ", "").split(",")

    for part in parts:
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            range_parts = part.split("-", 1)
            if len(range_parts) != 2 or not range_parts[0].strip() or not range_parts[1].strip():
                raise ValueError(f"页码范围格式错误：'{part}'，正确格式如 '1-5'")
            try:
                start = int(range_parts[0].strip())
                end = int(range_parts[1].strip())
            except ValueError:
                raise ValueError(f"页码必须是数字：'{part}'")
            if start < 1:
                raise ValueError(f"页码不能小于 1：'{part}'")
            if end < start:
                raise ValueError(f"页码范围结束值不能小于起始值：'{part}'")
            if end > max_page:
                raise ValueError(f"页码 {end} 超出范围，最大页数为 {max_page}")
            for p in range(start, end + 1):
                pages.add(p - 1)
        else:
            try:
                p = int(part)
            except ValueError:
                raise ValueError(f"页码必须是数字：'{part}'")
            if p < 1:
                raise ValueError(f"页码不能小于 1：{p}")
            if p > max_page:
                raise ValueError(f"页码 {p} 超出范围，最大页数为 {max_page}")
            pages.add(p - 1)

    if not pages:
        raise ValueError("未解析到有效的页码")
    return sorted(pages)


def resolve_file_conflict(file_path):
    """
    处理文件名冲突：如果文件已存在，自动追加 _1、_2 等编号。
    """
    file_path = Path(file_path)
    if not file_path.exists():
        return file_path
    stem = file_path.stem
    suffix = file_path.suffix
    parent = file_path.parent
    counter = 1
    while True:
        new_name = f"{stem}_{counter}{suffix}"
        new_path = parent / new_name
        if not new_path.exists():
            return new_path
        counter += 1


def format_file_size(size_bytes):
    """将字节数格式化为人类可读的文件大小"""
    if size_bytes < 0:
        return "0 B"
    units = ["B", "KB", "MB", "GB"]
    unit_index = 0
    size = float(size_bytes)
    while size >= 1024.0 and unit_index < len(units) - 1:
        size /= 1024.0
        unit_index += 1
    if unit_index == 0:
        return f"{int(size)} B"
    return f"{size:.1f} {units[unit_index]}"


def ensure_output_dir(output_dir):
    """确保输出目录存在，不存在则自动创建"""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def rgba_to_rgb(image, background_color=(255, 255, 255)):
    """
    将 RGBA 图片的透明背景转为指定颜色（默认白色）。
    适用于 PNG 转 JPG/PDF 时透明区域变黑的问题。
    """
    if image.mode in ("RGBA", "LA"):
        background = Image.new("RGB", image.size, background_color)
        if image.mode == "RGBA":
            background.paste(image, mask=image.split()[3])
        else:
            background.paste(image, mask=image.split()[1])
        return background
    elif image.mode != "RGB":
        return image.convert("RGB")
    return image


def get_default_input_dir():
    """
    获取默认输入目录（用于文件选择对话框的初始路径）。
    优先使用 Windows 桌面，桌面不存在则使用用户主目录。
    """
    desktop = Path.home() / "Desktop"
    if desktop.exists():
        return desktop
    return Path.home()
