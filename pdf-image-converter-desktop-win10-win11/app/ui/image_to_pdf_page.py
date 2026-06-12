# -*- coding: utf-8 -*-
"""
图片转 PDF 功能页面
支持多图合并为 PDF、单图转 PDF、拖拽、排序、页面尺寸设置。
"""

import subprocess
import platform
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QLineEdit, QRadioButton, QButtonGroup,
    QFileDialog, QListWidget, QProgressBar, QTextEdit,
    QGroupBox, QSpinBox, QMessageBox, QAbstractItemView,
    QCheckBox,
)
from PySide6.QtCore import Qt, QMimeData
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QDragMoveEvent

from app.config.settings import Settings
from app.workers.task_worker import TaskWorker
from app.services.image_to_pdf import convert_images_to_pdf
from app.services.file_utils import get_default_input_dir

# 支持的图片格式
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff", ".tif"}


class ImageDropListWidget(QListWidget):
    """
    支持从外部拖入图片文件的列表控件。
    拖拽事件由本控件直接接收和处理。
    """

    def __init__(self, parent_page=None):
        super().__init__()
        self._parent_page = parent_page
        self.setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DropOnly)
        self.setDefaultDropAction(Qt.DropAction.CopyAction)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            if self._parent_page:
                self._parent_page._log("[debug] dragEnterEvent triggered")
        else:
            event.ignore()

    def dragMoveEvent(self, event: QDragMoveEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent):
        if not event.mimeData().hasUrls():
            event.ignore()
            return

        urls = event.mimeData().urls()
        if self._parent_page:
            self._parent_page._log(f"[debug] dropEvent triggered, received {len(urls)} file(s)")

        added_count = 0
        ignored_count = 0

        for url in urls():
            file_path = Path(url.toLocalFile())

            # 忽略文件夹
            if file_path.is_dir():
                ignored_count += 1
                continue

            # 检查格式
            if file_path.suffix.lower() not in IMAGE_EXTENSIONS:
                ignored_count += 1
                if self._parent_page:
                    self._parent_page._log(f"已忽略不支持的文件：{file_path.name}")
                continue

            # 添加到列表
            if self._parent_page:
                self._parent_page.add_image_paths([file_path])
                added_count += 1

        event.acceptProposedAction()

        if self._parent_page and added_count > 0:
            self._parent_page._log(f"拖拽添加了 {added_count} 张图片")


class ImageToPDFPage(QWidget):
    """图片转 PDF 页面"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings = Settings()
        self.worker = None
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        # === 图片文件区 ===
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

        # 排序按钮
        sort_layout = QHBoxLayout()
        self.btn_move_up = QPushButton("上移")
        self.btn_move_up.clicked.connect(self._move_up)
        self.btn_move_down = QPushButton("下移")
        self.btn_move_down.clicked.connect(self._move_down)
        self.btn_sort_name = QPushButton("按文件名排序")
        self.btn_sort_name.clicked.connect(self._sort_by_name)
        sort_layout.addWidget(self.btn_move_up)
        sort_layout.addWidget(self.btn_move_down)
        sort_layout.addWidget(self.btn_sort_name)
        sort_layout.addStretch()
        file_layout.addLayout(sort_layout)

        # 图片列表（支持拖拽）
        self.file_list = ImageDropListWidget(parent_page=self)
        self.file_list.setMinimumHeight(100)
        file_layout.addWidget(self.file_list)

        # 拖拽提示
        tip_label = QLabel("提示：可直接拖拽图片文件到上方列表，支持 JPG/PNG/WebP/BMP/TIFF")
        tip_label.setStyleSheet("color: gray; font-size: 11px;")
        tip_label.setAcceptDrops(False)
        file_layout.addWidget(tip_label)

        layout.addWidget(file_group)

        # === 参数设置区 ===
        settings_group = QGroupBox("转换设置")
        settings_layout = QVBoxLayout(settings_group)

        # 转换模式
        mode_layout = QHBoxLayout()
        self.radio_merge = QRadioButton("合并为一个 PDF")
        self.radio_merge.setChecked(True)
        self.radio_single = QRadioButton("每张图片单独转 PDF")
        mode_group = QButtonGroup(self)
        mode_group.addButton(self.radio_merge)
        mode_group.addButton(self.radio_single)
        mode_layout.addWidget(self.radio_merge)
        mode_layout.addWidget(self.radio_single)
        mode_layout.addStretch()
        settings_layout.addLayout(mode_layout)

        # 输出文件名（合并模式）
        self.name_layout = QHBoxLayout()
        self.name_label = QLabel("输出文件名：")
        self.edit_output_name = QLineEdit()
        self.edit_output_name.setPlaceholderText("默认为 合并文档.pdf")
        self.name_layout.addWidget(self.name_label)
        self.name_layout.addWidget(self.edit_output_name)
        settings_layout.addLayout(self.name_layout)

        # 页面尺寸
        size_layout = QHBoxLayout()
        size_layout.addWidget(QLabel("页面尺寸："))
        self.combo_page_size = QComboBox()
        self.combo_page_size.addItems(["使用原图尺寸", "A4 竖版", "A4 横版"])
        size_layout.addWidget(self.combo_page_size)
        size_layout.addStretch()
        settings_layout.addLayout(size_layout)

        # 图片放置方式
        place_layout = QHBoxLayout()
        place_layout.addWidget(QLabel("放置方式："))
        self.combo_placement = QComboBox()
        self.combo_placement.addItems(["等比例适应页面", "居中显示", "不裁切"])
        place_layout.addWidget(self.combo_placement)
        place_layout.addStretch()
        settings_layout.addLayout(place_layout)

        # 图片质量
        quality_layout = QHBoxLayout()
        quality_layout.addWidget(QLabel("图片质量："))
        self.spin_quality = QSpinBox()
        self.spin_quality.setRange(1, 100)
        self.spin_quality.setValue(self.settings.get("default_image_quality", 90))
        self.spin_quality.setSuffix("%")
        quality_layout.addWidget(self.spin_quality)
        quality_layout.addStretch()
        settings_layout.addLayout(quality_layout)

        # 模式切换时更新界面
        self.radio_merge.toggled.connect(self._on_mode_changed)

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
            "QPushButton { background-color: #2196F3; color: white; "
            "padding: 8px 20px; font-size: 14px; border-radius: 4px; }"
            "QPushButton:hover { background-color: #1976D2; }"
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
        self.log_text.setMaximumHeight(120)
        log_layout.addWidget(self.log_text)
        btn_clear_log = QPushButton("清空日志")
        btn_clear_log.clicked.connect(self.log_text.clear)
        log_layout.addWidget(btn_clear_log)
        layout.addWidget(log_group)

        self._on_mode_changed()

    def add_image_paths(self, paths):
        """
        统一添加图片路径到列表。
        按钮添加和拖拽添加都调用此方法。
        """
        existing = [
            self.file_list.item(i).data(Qt.ItemDataRole.UserRole)
            for i in range(self.file_list.count())
        ]
        added = 0
        for p in paths:
            path_str = str(p)
            if path_str not in existing:
                self.file_list.addItem(Path(p).name)
                self.file_list.item(self.file_list.count() - 1).setData(
                    Qt.ItemDataRole.UserRole, path_str
                )
                existing.append(path_str)
                added += 1
        return added

    def _log(self, message):
        """向日志窗口追加消息"""
        self.log_text.append(message)

    def _on_mode_changed(self):
        """转换模式切换"""
        is_merge = self.radio_merge.isChecked()
        self.name_label.setVisible(is_merge)
        self.edit_output_name.setVisible(is_merge)

    def _add_files(self):
        """点击"添加图片"按钮"""
        filter_str = "图片文件 (*.jpg *.jpeg *.png *.webp *.bmp *.tiff *.tif)"
        files, _ = QFileDialog.getOpenFileNames(
            self, "选择图片文件", str(get_default_input_dir()), filter_str
        )
        if files:
            self.add_image_paths([Path(f) for f in files])

    def _remove_selected(self):
        for item in reversed(self.file_list.selectedItems()):
            self.file_list.takeItem(self.file_list.row(item))

    def _clear_list(self):
        self.file_list.clear()

    def _move_up(self):
        row = self.file_list.currentRow()
        if row > 0:
            item = self.file_list.takeItem(row)
            self.file_list.insertItem(row - 1, item)
            self.file_list.setCurrentRow(row - 1)

    def _move_down(self):
        row = self.file_list.currentRow()
        if row < self.file_list.count() - 1:
            item = self.file_list.takeItem(row)
            self.file_list.insertItem(row + 1, item)
            self.file_list.setCurrentRow(row + 1)

    def _sort_by_name(self):
        items = []
        for i in range(self.file_list.count()):
            item = self.file_list.item(i)
            items.append((item.text(), item.data(Qt.ItemDataRole.UserRole)))
        items.sort(key=lambda x: x[0].lower())
        self.file_list.clear()
        for name, data in items:
            self.file_list.addItem(name)
            self.file_list.item(self.file_list.count() - 1).setData(
                Qt.ItemDataRole.UserRole, data
            )

    def _browse_output_dir(self):
        dir_path = QFileDialog.getExistingDirectory(self, "选择输出目录")
        if dir_path:
            self.edit_output_dir.setText(dir_path)

    def _start_convert(self):
        # 收集文件
        image_paths = []
        for i in range(self.file_list.count()):
            path_str = self.file_list.item(i).data(Qt.ItemDataRole.UserRole)
            image_paths.append(Path(path_str))

        if not image_paths:
            QMessageBox.warning(self, "提示", "请先添加图片文件！")
            return

        # 输出目录
        output_dir_str = self.edit_output_dir.text().strip()
        if not output_dir_str:
            QMessageBox.warning(self, "提示", "请选择输出目录！")
            return
        output_dir = Path(output_dir_str)

        # 参数
        merge = self.radio_merge.isChecked()
        page_size_map = {"使用原图尺寸": "original", "A4 竖版": "a4_portrait", "A4 横版": "a4_landscape"}
        page_size_mode = page_size_map.get(self.combo_page_size.currentText(), "original")

        placement_map = {"等比例适应页面": "fit", "居中显示": "center", "不裁切": "no_crop"}
        placement = placement_map.get(self.combo_placement.currentText(), "fit")

        quality = self.spin_quality.value()

        # 输出路径
        if merge:
            out_name = self.edit_output_name.text().strip()
            if not out_name:
                out_name = "合并文档.pdf"
            if not out_name.endswith(".pdf"):
                out_name += ".pdf"
            output_path = output_dir / out_name
        else:
            output_path = output_dir

        # 禁用按钮
        self.btn_start.setEnabled(False)
        self.btn_open_dir.setEnabled(False)
        self.progress_bar.setValue(0)
        self._last_output_dir = output_dir

        def task_func(on_progress=None, on_log=None):
            return convert_images_to_pdf(
                image_paths=image_paths,
                output_path=output_path,
                page_size_mode=page_size_mode,
                placement=placement,
                quality=quality,
                merge=merge,
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
            elif platform.system() == "Darwin":
                subprocess.Popen(["open", str(output_dir)])
            else:
                subprocess.Popen(["xdg-open", str(output_dir)])
