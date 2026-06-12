# -*- coding: utf-8 -*-
"""
PDF 工具服务模块
使用 pypdf 实现 PDF 合并、拆分、提取页面、删除页面。
"""

from pathlib import Path
from pypdf import PdfReader, PdfWriter
from app.services.file_utils import parse_page_range, resolve_file_conflict, ensure_output_dir
from app.config.settings import Settings


def merge_pdfs(pdf_paths, output_path, on_progress=None, on_log=None):
    """将多个 PDF 合并为一个"""
    if not pdf_paths:
        raise ValueError("没有选择任何 PDF 文件")

    settings = Settings()
    writer = PdfWriter()
    total = len(pdf_paths)

    for idx, pdf_path in enumerate(pdf_paths):
        if on_progress:
            on_progress(idx + 1, total, pdf_path.name)
        try:
            reader = PdfReader(str(pdf_path))
            if reader.is_encrypted:
                raise ValueError(f"PDF 已加密：{pdf_path.name}")
            for page in reader.pages:
                writer.add_page(page)
            if on_log:
                on_log(f"已添加：{pdf_path.name}（{len(reader.pages)} 页）")
        except Exception as e:
            if on_log:
                on_log(f"添加失败 {pdf_path.name}：{str(e)}")
            raise

    out_path = Path(output_path)
    if settings.get("file_conflict_mode") == "rename":
        out_path = resolve_file_conflict(out_path)

    with open(str(out_path), "wb") as f:
        writer.write(f)

    if on_log:
        on_log(f"合并完成：{out_path.name}")
    return out_path


def split_pdf(pdf_path, output_dir, on_progress=None, on_log=None):
    """将 PDF 按页拆分成多个 PDF"""
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF 文件不存在：{pdf_path}")

    settings = Settings()
    try:
        reader = PdfReader(str(pdf_path))
        if reader.is_encrypted:
            raise ValueError(f"PDF 已加密：{pdf_path.name}")

        total_pages = len(reader.pages)
        if total_pages == 0:
            raise ValueError(f"PDF 没有页面：{pdf_path.name}")

        sub_dir = ensure_output_dir(output_dir / f"{pdf_path.stem}_split")
        result_files = []

        for page_num in range(total_pages):
            if on_progress:
                on_progress(page_num + 1, total_pages, pdf_path.name)
            try:
                writer = PdfWriter()
                writer.add_page(reader.pages[page_num])
                out_path = sub_dir / f"{pdf_path.stem}_page_{page_num + 1:03d}.pdf"
                if settings.get("file_conflict_mode") == "rename":
                    out_path = resolve_file_conflict(out_path)
                with open(str(out_path), "wb") as f:
                    writer.write(f)
                result_files.append(out_path)
                if on_log:
                    on_log(f"已拆分：第 {page_num + 1} 页 -> {out_path.name}")
            except Exception as e:
                if on_log:
                    on_log(f"拆分第 {page_num + 1} 页失败：{str(e)}")
                continue
        return result_files
    except (ValueError, FileNotFoundError):
        raise
    except Exception as e:
        raise RuntimeError(f"读取 PDF 失败：{str(e)}")


def extract_pages(pdf_path, output_path, page_range_str, on_log=None):
    """从 PDF 中提取指定页面，生成新 PDF"""
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF 文件不存在：{pdf_path}")

    settings = Settings()
    try:
        reader = PdfReader(str(pdf_path))
        if reader.is_encrypted:
            raise ValueError(f"PDF 已加密：{pdf_path.name}")

        total_pages = len(reader.pages)
        pages = parse_page_range(page_range_str, total_pages)

        writer = PdfWriter()
        for page_num in pages:
            writer.add_page(reader.pages[page_num])

        out_path = Path(output_path)
        if settings.get("file_conflict_mode") == "rename":
            out_path = resolve_file_conflict(out_path)
        with open(str(out_path), "wb") as f:
            writer.write(f)

        if on_log:
            on_log(f"已提取 {len(pages)} 页 -> {out_path.name}")
        return out_path
    except (ValueError, FileNotFoundError):
        raise
    except Exception as e:
        raise RuntimeError(f"提取页面失败：{str(e)}")


def delete_pages(pdf_path, output_path, page_range_str, on_log=None):
    """从 PDF 中删除指定页面，生成新 PDF"""
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF 文件不存在：{pdf_path}")

    settings = Settings()
    try:
        reader = PdfReader(str(pdf_path))
        if reader.is_encrypted:
            raise ValueError(f"PDF 已加密：{pdf_path.name}")

        total_pages = len(reader.pages)
        pages_to_delete = set(parse_page_range(page_range_str, total_pages))
        pages_to_keep = [i for i in range(total_pages) if i not in pages_to_delete]

        if not pages_to_keep:
            raise ValueError("删除指定页面后，PDF 将没有任何页面")

        writer = PdfWriter()
        for page_num in pages_to_keep:
            writer.add_page(reader.pages[page_num])

        out_path = Path(output_path)
        if settings.get("file_conflict_mode") == "rename":
            out_path = resolve_file_conflict(out_path)
        with open(str(out_path), "wb") as f:
            writer.write(f)

        if on_log:
            on_log(f"已删除 {len(pages_to_delete)} 页，保留 {len(pages_to_keep)} 页 -> {out_path.name}")
        return out_path
    except (ValueError, FileNotFoundError):
        raise
    except Exception as e:
        raise RuntimeError(f"删除页面失败：{str(e)}")
