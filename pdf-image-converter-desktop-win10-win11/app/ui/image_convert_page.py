# -*- coding: utf-8 -*-
"""
图片格式转换/压缩功能页面
支持批量图片格式转换、质量压缩、尺寸调整。
"""

import subprocess
import platform
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QLineEdit, QRadioButton, QButtonGroup,
    QFileDialog, QListWidget, QProgressBar, QTextEdit,
    QGroupBox, QSpinBox, QMessageBox, QAbstractItemView,
    QCheckBox, QTableWidget, QTableWidgetItem, QHeaderView,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QDragEnterEvent, QDropEvent

from app.config.settings import Settings
from app.workers.task_worker import TaskWorker
from app.services.image_converter import convert_images, SUPPORTED_INPUT_FORMATS
from app.services.file_utils import format_file_size, get_default_input_dir

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff", ".tif"}


class ImageDragDropList(QListWidget):
    """支持拖拽图片的列表"""

    def __init__(self, parent=None):
        super().__init__(parent)
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
                if file_path.suffix.lower() in IMAGE_EXTENSIONS:
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


class ImageConvertPage(QWidget):
    """图片格式转换页面"""

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
        file_group = QGroupBox("图片文件")
        file_layout = QVBoxLayout(file_group)

        btn_layout = QHBoxLayout()
        self.btn_add = QPushButton("添加图片")
        self.btn_add.clicked.connect(self._add_files)
        self.btn_remove = QPushButton("删除选中")
        self.btn_remove.clicked.connect(self._remove_selected)
        self.btn_clear = QPushButton("清空列表")
        self.btn_clear.clicked.connect(self._clear_list)
        btn_layout.addWidget(self.btn_add)
        btn_layout.addWidget(self.btn_remove)
        btn_layout.addWidget(self.btn_clear)
        btn_layout.addStretch()
        file_layout.addLayout(btn_layout)

        self.file_list = ImageDragDropList()
        self.file_list.setMinimumHeight(80)
        file_layout.addWidget(self.file_list)

        tip = QLabel("提示：支持 JPG/PNG/WebP/BMP/TIFF，可直接拖拽")
        tip.setStyleSheet("color: gray; font-size: 11px;")
        file_layout.addWidget(tip)

        layout.addWidget(file_group)

        # === 转换设置 ===
        settings_group = QGroupBox("转换设置")
        settings_layout = QVBoxLayout(settings_group)

        # 输出格式和质量
        fmt_layout = QHBoxLayout()
        fmt_layout.addWidget(QLabel("输出格式："))
        self.combo_format = QComboBox()
        self.combo_format.addItems(["JPG", "PNG", "WebP"])
        fmt_layout.addWidget(self.combo_format)

        fmt_layout.addWidget(QLabel("图片质量："))
        self.spin_quality = QSpinBox()
        self.spin_quality.setRange(1, 100)
        self.spin_quality.setValue(self.settings.get("default_image_quality", 90))
        self.spin_quality.setSuffix("%")
        fmt_layout.addWidget(self.spin_quality)
        fmt_layout.addStretch()
        settings_layout.addLayout(fmt_layout)

        # 尺寸调整
        resize_layout = QHBoxLayout()
        resize_layout.addWidget(QLabel("调整尺寸："))
        self.combo_resize = QComboBox()
        self.combo_resize.addItems(["不调整", "按宽度等比例缩放", "按高度等比例缩放", "自定义宽高"])
        self.combo_resize.currentTextChanged.connect(self._on_resize_changed)
        resize_layout.addWidget(self.combo_resize)
        resize_layout.addStretch()
        settings_layout.addLayout(resize_layout)

        # 宽高输入
        self.size_layout = QHBoxLayout()
        self.label_width = QLabel("宽度：")
        self.spin_width = QSpinBox()
        self.spin_width.setRange(1, 10000)
        self.spin_width.setValue(800)
        self.spin_width.setSuffix(" px")
        self.label_height = QLabel("高度：")
        self.spin_height = QSpinBox()
        self.spin_height.setRange(1, 10000)
        self.spin_height.setValue(600)
        self.spin_height.setSuffix(" px")
        self.check_aspect = QCheckBox("保持宽高比")
        self.check_aspect.setChecked(True)
        self.size_layout.addWidget(self.label_width)
        self.size_layout.addWidget(self.spin_width)
        self.size_layout.addWidget(self.label_height)
        self.size_layout.addWidget(self.spin_height)
        self.size_layout.addWidget(self.check_aspect)
        self.size_layout.addStretch()
        settings_layout.addLayout(self.size_layout)

        self._on_resize_changed()

        layout.addWidget(settings_group)

        # === 输出目录 ===
        output_layout = QHBoxLayout()
        output_layout.addWidget(QLabel("输出目录："))
        self.edit_output_dir = QLineEdit()
        self.edit_output_dir.setPlaceholderText("请选择输出目录")
        self.btn_browse = QPushButton("浏览...")
        self.btn_browse.clicked.connect(self._browse_output_dir)
        output_layout.addWidget(self.edit_output_dir)
        output_layout.addWidget(self.btn_browse)
        layout.addLayout(output_layout)

        # === 操作按钮 ===
        action_layout = QHBoxLayout()
        self.btn_start = QPushButton("开始转换")
        self.btn_start.setStyleSheet(
            "QPushButton { background-color: #FF9800; color: white; "
            "padding: 8px 20px; font-size: 14px; border-radius: 4px; }"
            "QPushButton:hover { background-color: #F57C00; }"
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

        # === 结果表格 ===
        result_group = QGroupBox("转换结果")
        result_layout = QVBoxLayout(result_group)
        self.result_table = QTableWidget()
        self.result_table.setColumnCount(5)
        self.result_table.setHorizontalHeaderLabels(["文件名", "原始大小", "转换后大小", "状态", "说明"])
        self.result_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.result_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        result_layout.addWidget(self.result_table)
        layout.addWidget(result_group)

        # === 日志 ===
        log_group = QGroupBox("运行日志")
        log_layout = QVBoxLayout(log_group)
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(100)
        log_layout.addWidget(self.log_text)
        btn_clear_log = QPushButton("清空日志")
        btn_clear_log.clicked.connect(self.log_text.clear)
        log_layout.addWidget(btn_clear_log)
        layout.addWidget(log_group)

    def _on_resize_changed(self):
        mode = self.combo_resize.currentText()
        show_size = mode != "不调整"
        show_width = mode in ("按宽度等比例缩放", "自定义宽高")
        show_height = mode in ("按高度等比例缩放", "自定义宽高")
        show_aspect = mode == "自定义宽高"

        self.label_width.setVisible(show_width)
        self.spin_width.setVisible(show_width)
        self.label_height.setVisible(show_height)
        self.spin_height.setVisible(show_height)
        self.check_aspect.setVisible(show_aspect)

    def _add_files(self):
        filter_str = "图片文件 (*.jpg *.jpeg *.png *.webp *.bmp *.tiff *.tif)"
        files, _ = QFileDialog.getOpenFileNames(self, "选择图片文件", str(get_default_input_dir()), filter_str)
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
        for item in reversed(self.file_list.selectedItems()):
            self.file_list.takeItem(self.file_list.row(item))

    def _clear_list(self):
        self.file_list.clear()

    def _browse_output_dir(self):
        dir_path = QFileDialog.getExistingDirectory(self, "选择输出目录")
        if dir_path:
            self.edit_output_dir.setText(dir_path)

    def _start_convert(self):
        image_paths = []
        for i in range(self.file_list.count()):
            path_str = self.file_list.item(i).data(Qt.ItemDataRole.UserRole)
            image_paths.append(Path(path_str))

        if not image_paths:
            QMessageBox.warning(self, "提示", "请先添加图片文件！")
            return

        output_dir_str = self.edit_output_dir.text().strip()
        if not output_dir_str:
            QMessageBox.warning(self, "提示", "请选择输出目录！")
            return
        output_dir = Path(output_dir_str)

        # 参数
        output_format = self.combo_format.currentText().lower()
        quality = self.spin_quality.value()

        resize_mode_map = {
            "不调整": "none",
            "按宽度等比例缩放": "by_width",
            "按高度等比例缩放": "by_height",
            "自定义宽高": "custom",
        }
        resize_mode = resize_mode_map.get(self.combo_resize.currentText(), "none")
        resize_width = self.spin_width.value()
        resize_height = self.spin_height.value()
        keep_aspect = self.check_aspect.isChecked()

        self.btn_start.setEnabled(False)
        self.btn_open_dir.setEnabled(False)
        self.progress_bar.setValue(0)
        self.result_table.setRowCount(0)
        self._last_output_dir = output_dir

        def task_func(on_progress=None, on_log=None):
            return convert_images(
                image_paths=image_paths,
                output_dir=output_dir,
                output_format=output_format,
                quality=quality,
                resize_mode=resize_mode,
                resize_width=resize_width,
                resize_height=resize_height,
                keep_aspect_ratio=keep_aspect,
                on_progress=on_progress,
                on_log=on_log,
            )

        self.worker = TaskWorker(task_func)
        self.worker.progress.connect(self._on_progress)
        self.worker.log.connect(self._on_log)
        self.worker.finished.connect(self._on_finished)
        self.worker.error.connect(self._on_error)
        self.worker.start()

    def _on_progress(self, current, total, filename):
        if total > 0:
            self.progress_bar.setValue(int(current / total * 100))

    def _on_log(self, message):
        self.log_text.append(message)

    def _on_error(self, message):
        self.log_text.append(f"[错误] {message}")

    def _on_finished(self, success, message):
        self.btn_start.setEnabled(True)
        self.progress_bar.setValue(100 if success else 0)
        self.log_text.append(f"{'='*40}")
        if success:
            self.btn_open_dir.setEnabled(True)
            self.log_text.append(f"[完成] {message}")
            if self.settings.get("auto_open_output_dir", True):
                self._open_output_dir()
        else:
            self.log_text.append(f"[失败] {message}")

    def _open_output_dir(self):
        output_dir = getattr(self, "_last_output_dir", None)
        if output_dir and output_dir.exists():
            if platform.system() == "Windows":
                subprocess.Popen(["explorer", str(output_dir)])
