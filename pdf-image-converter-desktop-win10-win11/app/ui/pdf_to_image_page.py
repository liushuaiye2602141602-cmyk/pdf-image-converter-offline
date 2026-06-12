# -*- coding: utf-8 -*-
"""
PDF 转图片功能页面
支持批量 PDF 转 PNG/JPG/WebP，支持拖拽、页码范围、DPI 设置。
"""

import subprocess
import platform
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QLineEdit, QRadioButton, QButtonGroup,
    QFileDialog, QListWidget, QProgressBar, QTextEdit,
    QGroupBox, QSpinBox, QMessageBox, QAbstractItemView,
)
from PySide6.QtCore import Qt, QMimeData
from PySide6.QtGui import QDragEnterEvent, QDropEvent

from app.config.settings import Settings
from app.workers.task_worker import TaskWorker
from app.services.pdf_to_image import convert_pdf_to_images
from app.services.file_utils import get_default_input_dir


class DragDropListWidget(QListWidget):
    """支持拖拽文件的列表控件"""

    def __init__(self, accept_extensions=None, parent=None):
        super().__init__(parent)
        self.accept_extensions = accept_extensions or {".pdf"}
        self.setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DropOnly)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event: QDropEvent):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                file_path = Path(url.toLocalFile())
                if file_path.suffix.lower() in self.accept_extensions:
                    # 避免重复添加
                    existing = [
                        self.item(i).data(Qt.ItemDataRole.UserRole)
                        for i in range(self.count())
                    ]
                    if str(file_path) not in existing:
                        self.addItem(file_path.name)
                        self.item(self.count() - 1).setData(
                            Qt.ItemDataRole.UserRole, str(file_path)
                        )
            event.acceptProposedAction()
        else:
            super().dropEvent(event)


class PDFToImagePage(QWidget):
    """PDF 转图片页面"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings = Settings()
        self.worker = None
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        # === 文件选择区 ===
        file_group = QGroupBox("PDF 文件")
        file_layout = QVBoxLayout(file_group)

        # 按钮行
        btn_layout = QHBoxLayout()
        self.btn_add_files = QPushButton("添加文件")
        self.btn_add_files.clicked.connect(self._add_files)
        self.btn_remove_selected = QPushButton("删除选中")
        self.btn_remove_selected.clicked.connect(self._remove_selected)
        self.btn_clear = QPushButton("清空列表")
        self.btn_clear.clicked.connect(self._clear_list)
        btn_layout.addWidget(self.btn_add_files)
        btn_layout.addWidget(self.btn_remove_selected)
        btn_layout.addWidget(self.btn_clear)
        btn_layout.addStretch()
        file_layout.addLayout(btn_layout)

        # 文件列表（支持拖拽）
        self.file_list = DragDropListWidget(accept_extensions={".pdf"})
        self.file_list.setMinimumHeight(80)
        file_layout.addWidget(self.file_list)

        # 拖拽提示
        tip_label = QLabel("提示：可以直接拖拽 PDF 文件到上方列表")
        tip_label.setStyleSheet("color: gray; font-size: 11px;")
        file_layout.addWidget(tip_label)

        layout.addWidget(file_group)

        # === 参数设置区 ===
        settings_group = QGroupBox("转换设置")
        settings_layout = QVBoxLayout(settings_group)

        # 输出格式
        fmt_layout = QHBoxLayout()
        fmt_layout.addWidget(QLabel("输出格式："))
        self.combo_format = QComboBox()
        self.combo_format.addItems(["PNG", "JPG", "WebP"])
        self.combo_format.currentTextChanged.connect(self._on_format_changed)
        fmt_layout.addWidget(self.combo_format)
        fmt_layout.addStretch()

        # DPI
        fmt_layout.addWidget(QLabel("DPI："))
        self.combo_dpi = QComboBox()
        self.combo_dpi.addItems(["150", "200", "300", "600"])
        self.combo_dpi.setCurrentText(str(self.settings.get("default_dpi", 300)))
        fmt_layout.addWidget(self.combo_dpi)
        settings_layout.addLayout(fmt_layout)

        # 质量（JPG/WebP 时显示）
        self.quality_layout = QHBoxLayout()
        self.quality_label = QLabel("图片质量：")
        self.spin_quality = QSpinBox()
        self.spin_quality.setRange(1, 100)
        self.spin_quality.setValue(self.settings.get("default_image_quality", 90))
        self.spin_quality.setSuffix("%")
        self.quality_layout.addWidget(self.quality_label)
        self.quality_layout.addWidget(self.spin_quality)
        self.quality_layout.addStretch()
        settings_layout.addLayout(self.quality_layout)

        # 页码范围
        range_layout = QHBoxLayout()
        range_layout.addWidget(QLabel("页码范围："))
        self.radio_all = QRadioButton("全部页面")
        self.radio_all.setChecked(True)
        self.radio_custom = QRadioButton("自定义：")
        self.edit_page_range = QLineEdit()
        self.edit_page_range.setPlaceholderText("例如：1-3,5,8-10")
        self.edit_page_range.setEnabled(False)

        range_group = QButtonGroup(self)
        range_group.addButton(self.radio_all)
        range_group.addButton(self.radio_custom)
        self.radio_custom.toggled.connect(self.edit_page_range.setEnabled)

        range_layout.addWidget(self.radio_all)
        range_layout.addWidget(self.radio_custom)
        range_layout.addWidget(self.edit_page_range)
        range_layout.addStretch()
        settings_layout.addLayout(range_layout)

        layout.addWidget(settings_group)

        # === 输出目录 ===
        output_layout = QHBoxLayout()
        output_layout.addWidget(QLabel("输出目录："))
        self.edit_output_dir = QLineEdit()
        self.edit_output_dir.setPlaceholderText("默认保存到 PDF 所在目录")
        self.btn_browse = QPushButton("浏览...")
        self.btn_browse.clicked.connect(self._browse_output_dir)
        output_layout.addWidget(self.edit_output_dir)
        output_layout.addWidget(self.btn_browse)
        layout.addLayout(output_layout)

        # === 操作按钮 ===
        action_layout = QHBoxLayout()
        self.btn_start = QPushButton("开始转换")
        self.btn_start.setStyleSheet(
            "QPushButton { background-color: #4CAF50; color: white; "
            "padding: 8px 20px; font-size: 14px; border-radius: 4px; }"
            "QPushButton:hover { background-color: #45a049; }"
            "QPushButton:disabled { background-color: #cccccc; }"
        )
        self.btn_start.clicked.connect(self._start_convert)

        self.btn_open_dir = QPushButton("打开输出目录")
        self.btn_open_dir.setEnabled(False)
        self.btn_open_dir.clicked.connect(self._open_output_dir)

        action_layout.addWidget(self.btn_start)
        action_layout.addWidget(self.btn_open_dir)
        action_layout.addStretch()
        layout.addLayout(action_layout)

        # === 进度条 ===
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        # === 日志窗口 ===
        log_group = QGroupBox("运行日志")
        log_layout = QVBoxLayout(log_group)
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(150)
        log_layout.addWidget(self.log_text)

        btn_clear_log = QPushButton("清空日志")
        btn_clear_log.clicked.connect(self.log_text.clear)
        log_layout.addWidget(btn_clear_log)

        layout.addWidget(log_group)

        # 初始化格式相关显示
        self._on_format_changed(self.combo_format.currentText())

    def _on_format_changed(self, fmt: str):
        """格式改变时，调整质量设置的可见性"""
        is_lossy = fmt in ("JPG", "WebP")
        self.quality_label.setVisible(is_lossy)
        self.spin_quality.setVisible(is_lossy)

    def _add_files(self):
        """添加 PDF 文件"""
        files, _ = QFileDialog.getOpenFileNames(
            self, "选择 PDF 文件", str(get_default_input_dir()), "PDF 文件 (*.pdf)"
        )
        if files:
            existing = [
                self.file_list.item(i).data(Qt.ItemDataRole.UserRole)
                for i in range(self.file_list.count())
            ]
            for f in files:
                if f not in existing:
                    self.file_list.addItem(Path(f).name)
                    self.file_list.item(self.file_list.count() - 1).setData(
                        Qt.ItemDataRole.UserRole, f
                    )

    def _remove_selected(self):
        """删除选中项"""
        for item in reversed(self.file_list.selectedItems()):
            self.file_list.takeItem(self.file_list.row(item))

    def _clear_list(self):
        """清空列表"""
        self.file_list.clear()

    def _browse_output_dir(self):
        """选择输出目录"""
        dir_path = QFileDialog.getExistingDirectory(self, "选择输出目录")
        if dir_path:
            self.edit_output_dir.setText(dir_path)

    def _start_convert(self):
        """开始转换"""
        # 收集文件列表
        file_paths = []
        for i in range(self.file_list.count()):
            path_str = self.file_list.item(i).data(Qt.ItemDataRole.UserRole)
            file_paths.append(Path(path_str))

        if not file_paths:
            QMessageBox.warning(self, "提示", "请先添加 PDF 文件！")
            return

        # 获取参数
        output_format = self.combo_format.currentText().lower()
        dpi = int(self.combo_dpi.currentText())
        quality = self.spin_quality.value()

        # 页码范围
        page_range_str = ""
        if self.radio_custom.isChecked():
            page_range_str = self.edit_page_range.text().strip()
            if not page_range_str:
                QMessageBox.warning(self, "提示", "请输入页码范围！")
                return

        # 输出目录
        output_dir_str = self.edit_output_dir.text().strip()
        if output_dir_str:
            output_dir = Path(output_dir_str)
        else:
            output_dir = file_paths[0].parent  # 默认使用第一个文件的目录

        # 禁用按钮
        self.btn_start.setEnabled(False)
        self.btn_open_dir.setEnabled(False)
        self.progress_bar.setValue(0)
        self._last_output_dir = output_dir

        # 创建任务函数
        def task_func(on_progress=None, on_log=None):
            all_results = []
            total_files = len(file_paths)

            for file_idx, pdf_path in enumerate(file_paths):
                if on_log:
                    on_log(f"--- 开始处理：{pdf_path.name}（{file_idx + 1}/{total_files}）---")

                try:
                    results = convert_pdf_to_images(
                        pdf_path=pdf_path,
                        output_dir=output_dir,
                        output_format=output_format,
                        dpi=dpi,
                        quality=quality,
                        page_range_str=page_range_str,
                        on_progress=on_progress,
                        on_log=on_log,
                    )
                    all_results.extend(results)
                except Exception as e:
                    if on_log:
                        on_log(f"处理失败：{pdf_path.name} - {str(e)}")
                    continue

            return all_results

        # 启动后台线程
        self.worker = TaskWorker(task_func)
        self.worker.progress.connect(self._on_progress)
        self.worker.log.connect(self._on_log)
        self.worker.finished.connect(self._on_finished)
        self.worker.error.connect(self._on_error)
        self.worker.start()

    def _on_progress(self, current, total, filename):
        """更新进度"""
        if total > 0:
            self.progress_bar.setValue(int(current / total * 100))

    def _on_log(self, message):
        """显示日志"""
        self.log_text.append(message)

    def _on_error(self, message):
        """显示错误"""
        self.log_text.append(f"[错误] {message}")

    def _on_finished(self, success, message):
        """任务完成"""
        self.btn_start.setEnabled(True)
        self.progress_bar.setValue(100 if success else 0)
        self.log_text.append(f"{'='*40}")

        if success:
            self.btn_open_dir.setEnabled(True)
            self.log_text.append(f"[完成] {message}")

            # 自动打开输出目录
            if self.settings.get("auto_open_output_dir", True):
                self._open_output_dir()
        else:
            self.log_text.append(f"[失败] {message}")

    def _open_output_dir(self):
        """打开输出目录"""
        output_dir = getattr(self, "_last_output_dir", None)
        if output_dir and output_dir.exists():
            if platform.system() == "Windows":
                subprocess.Popen(["explorer", str(output_dir)])
            elif platform.system() == "Darwin":
                subprocess.Popen(["open", str(output_dir)])
            else:
                subprocess.Popen(["xdg-open", str(output_dir)])
