# -*- coding: utf-8 -*-
"""
PDF 工具页面：合并、拆分、提取页面、删除页面
"""

import subprocess
import platform
from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QLineEdit, QListWidget, QProgressBar, QTextEdit,
    QGroupBox, QMessageBox, QAbstractItemView, QTabWidget, QFileDialog,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from app.config.settings import Settings
from app.workers.task_worker import TaskWorker
from app.services.pdf_tools import merge_pdfs, split_pdf, extract_pages, delete_pages
from app.services.file_utils import get_default_input_dir


class _DragDropList(QListWidget):
    """支持拖拽 PDF 的列表"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DropOnly)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                p = Path(url.toLocalFile())
                if p.suffix.lower() == ".pdf":
                    existing = [self.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self.count())]
                    if str(p) not in existing:
                        self.addItem(p.name)
                        self.item(self.count() - 1).setData(Qt.ItemDataRole.UserRole, str(p))
            event.acceptProposedAction()


class PDFToolsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings = Settings()
        self.worker = None
        self._init_ui()

    def _init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(8)

        tabs = QTabWidget()
        tabs.addTab(self._build_merge_tab(), "合并")
        tabs.addTab(self._build_split_tab(), "拆分")
        tabs.addTab(self._build_extract_tab(), "提取页面")
        tabs.addTab(self._build_delete_tab(), "删除页面")
        root.addWidget(tabs)

        # 公共：进度 + 日志
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        root.addWidget(self.progress_bar)

        log_group = QGroupBox("运行日志")
        lg = QVBoxLayout(log_group)
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(120)
        lg.addWidget(self.log_text)
        btn_clear = QPushButton("清空日志")
        btn_clear.clicked.connect(self.log_text.clear)
        lg.addWidget(btn_clear)
        root.addWidget(log_group)

    # ------------------------------------------------------------------
    # 合并
    # ------------------------------------------------------------------
    def _build_merge_tab(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(6, 6, 6, 6)

        btn_layout = QHBoxLayout()
        self.merge_btn_add = QPushButton("添加文件")
        self.merge_btn_add.clicked.connect(self._merge_add)
        btn_layout.addWidget(self.merge_btn_add)
        btn_layout.addWidget(self._btn("上移", self._merge_up))
        btn_layout.addWidget(self._btn("下移", self._merge_down))
        btn_layout.addWidget(self._btn("删除选中", self._merge_remove))
        btn_layout.addStretch()
        lay.addLayout(btn_layout)

        self.merge_list = _DragDropList()
        btn_clear = QPushButton("清空")
        btn_clear.clicked.connect(self.merge_list.clear)
        lay.addWidget(btn_clear)
        self.merge_list.setMinimumHeight(100)
        lay.addWidget(self.merge_list)

        out = QHBoxLayout()
        out.addWidget(QLabel("输出文件名："))
        self.merge_out_name = QLineEdit()
        self.merge_out_name.setPlaceholderText("默认为 合并结果.pdf")
        out.addWidget(self.merge_out_name)
        lay.addLayout(out)

        out2 = QHBoxLayout()
        out2.addWidget(QLabel("输出目录："))
        self.merge_out_dir = QLineEdit()
        self.merge_out_dir.setPlaceholderText("请选择输出目录")
        out2.addWidget(self.merge_out_dir)
        btn_browse = QPushButton("浏览...")
        btn_browse.clicked.connect(lambda: self._browse_dir(self.merge_out_dir))
        out2.addWidget(btn_browse)
        lay.addLayout(out2)

        self.merge_btn_start = QPushButton("开始合并")
        self.merge_btn_start.setStyleSheet("QPushButton{background:#4CAF50;color:#fff;padding:8px 16px;border-radius:4px}QPushButton:hover{background:#45a049}QPushButton:disabled{background:#ccc}")
        self.merge_btn_start.clicked.connect(self._merge_start)
        lay.addWidget(self.merge_btn_start)
        lay.addStretch()
        return w

    def _merge_files(self):
        return [Path(self.merge_list.item(i).data(Qt.ItemDataRole.UserRole)) for i in range(self.merge_list.count())]

    def _merge_add(self):
        files, _ = QFileDialog.getOpenFileNames(self, "选择 PDF", str(get_default_input_dir()), "PDF (*.pdf)")
        for f in files:
            if f not in [self.merge_list.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self.merge_list.count())]:
                self.merge_list.addItem(Path(f).name)
                self.merge_list.item(self.merge_list.count() - 1).setData(Qt.ItemDataRole.UserRole, f)

    def _merge_up(self):
        r = self.merge_list.currentRow()
        if r > 0:
            item = self.merge_list.takeItem(r)
            self.merge_list.insertItem(r - 1, item)
            self.merge_list.setCurrentRow(r - 1)

    def _merge_down(self):
        r = self.merge_list.currentRow()
        if 0 <= r < self.merge_list.count() - 1:
            item = self.merge_list.takeItem(r)
            self.merge_list.insertItem(r + 1, item)
            self.merge_list.setCurrentRow(r + 1)

    def _merge_remove(self):
        for item in reversed(self.merge_list.selectedItems()):
            self.merge_list.takeItem(self.merge_list.row(item))

    def _merge_start(self):
        files = self._merge_files()
        if not files:
            QMessageBox.warning(self, "提示", "请先添加 PDF 文件！"); return
        out_dir = self.merge_out_dir.text().strip()
        if not out_dir:
            QMessageBox.warning(self, "提示", "请选择输出目录！"); return
        out_name = self.merge_out_name.text().strip() or "合并结果.pdf"
        if not out_name.endswith(".pdf"):
            out_name += ".pdf"

        self.merge_btn_start.setEnabled(False)
        self.progress_bar.setValue(0)
        self._last_output_dir = Path(out_dir)

        def task(on_progress=None, on_log=None):
            return merge_pdfs(files, Path(out_dir) / out_name, on_progress=on_progress, on_log=on_log)

        self._run(task, self.merge_btn_start)

    # ------------------------------------------------------------------
    # 拆分
    # ------------------------------------------------------------------
    def _build_split_tab(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(6, 6, 6, 6)

        btn = QHBoxLayout()
        self.split_btn_add = QPushButton("添加 PDF")
        self.split_btn_add.clicked.connect(self._split_add)
        btn.addWidget(self.split_btn_add)
        btn.addWidget(self._btn("删除选中", self._split_remove))
        btn.addStretch()
        lay.addLayout(btn)

        self.split_list = _DragDropList()
        btn_clear = QPushButton("清空")
        btn_clear.clicked.connect(self.split_list.clear)
        lay.addWidget(btn_clear)
        self.split_list.setMinimumHeight(80)
        lay.addWidget(self.split_list)

        out = QHBoxLayout()
        out.addWidget(QLabel("输出目录："))
        self.split_out_dir = QLineEdit()
        self.split_out_dir.setPlaceholderText("请选择输出目录")
        out.addWidget(self.split_out_dir)
        btn2 = QPushButton("浏览...")
        btn2.clicked.connect(lambda: self._browse_dir(self.split_out_dir))
        out.addWidget(btn2)
        lay.addLayout(out)

        self.split_btn_start = QPushButton("开始拆分")
        self.split_btn_start.setStyleSheet("QPushButton{background:#2196F3;color:#fff;padding:8px 16px;border-radius:4px}QPushButton:hover{background:#1976D2}QPushButton:disabled{background:#ccc}")
        self.split_btn_start.clicked.connect(self._split_start)
        lay.addWidget(self.split_btn_start)
        lay.addStretch()
        return w

    def _split_files(self):
        return [Path(self.split_list.item(i).data(Qt.ItemDataRole.UserRole)) for i in range(self.split_list.count())]

    def _split_add(self):
        files, _ = __import__("PySide6.QtWidgets", fromlist=["QFileDialog"]).QFileDialog.getOpenFileNames(self, "选择 PDF", "", "PDF (*.pdf)")
        for f in files:
            if f not in [self.split_list.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self.split_list.count())]:
                self.split_list.addItem(Path(f).name)
                self.split_list.item(self.split_list.count() - 1).setData(Qt.ItemDataRole.UserRole, f)

    def _split_remove(self):
        for item in reversed(self.split_list.selectedItems()):
            self.split_list.takeItem(self.split_list.row(item))

    def _split_start(self):
        files = self._split_files()
        if not files:
            QMessageBox.warning(self, "提示", "请先添加 PDF 文件！"); return
        out_dir = self.split_out_dir.text().strip()
        if not out_dir:
            QMessageBox.warning(self, "提示", "请选择输出目录！"); return

        self.split_btn_start.setEnabled(False)
        self.progress_bar.setValue(0)
        self._last_output_dir = Path(out_dir)

        def task(on_progress=None, on_log=None):
            results = []
            for f in files:
                results.extend(split_pdf(f, Path(out_dir), on_progress=on_progress, on_log=on_log))
            return results

        self._run(task, self.split_btn_start)

    # ------------------------------------------------------------------
    # 提取页面
    # ------------------------------------------------------------------
    def _build_extract_tab(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(6, 6, 6, 6)

        btn = QHBoxLayout()
        self.extract_btn_add = QPushButton("添加 PDF")
        self.extract_btn_add.clicked.connect(self._extract_add)
        btn.addWidget(self.extract_btn_add)
        btn.addWidget(self._btn("删除选中", self._extract_remove))
        btn.addStretch()
        lay.addLayout(btn)

        self.extract_list = _DragDropList()
        btn_clear = QPushButton("清空")
        btn_clear.clicked.connect(self.extract_list.clear)
        lay.addWidget(btn_clear)
        self.extract_list.setMinimumHeight(80)
        lay.addWidget(self.extract_list)

        range_layout = QHBoxLayout()
        range_layout.addWidget(QLabel("提取页码："))
        self.extract_range = QLineEdit()
        self.extract_range.setPlaceholderText("例如：1-3,5,8-10")
        range_layout.addWidget(self.extract_range)
        lay.addLayout(range_layout)

        out = QHBoxLayout()
        out.addWidget(QLabel("输出目录："))
        self.extract_out_dir = QLineEdit()
        self.extract_out_dir.setPlaceholderText("请选择输出目录")
        out.addWidget(self.extract_out_dir)
        btn2 = QPushButton("浏览...")
        btn2.clicked.connect(lambda: self._browse_dir(self.extract_out_dir))
        out.addWidget(btn2)
        lay.addLayout(out)

        self.extract_btn_start = QPushButton("开始提取")
        self.extract_btn_start.setStyleSheet("QPushButton{background:#FF9800;color:#fff;padding:8px 16px;border-radius:4px}QPushButton:hover{background:#F57C00}QPushButton:disabled{background:#ccc}")
        self.extract_btn_start.clicked.connect(self._extract_start)
        lay.addWidget(self.extract_btn_start)
        lay.addStretch()
        return w

    def _extract_files(self):
        return [Path(self.extract_list.item(i).data(Qt.ItemDataRole.UserRole)) for i in range(self.extract_list.count())]

    def _extract_add(self):
        files, _ = __import__("PySide6.QtWidgets", fromlist=["QFileDialog"]).QFileDialog.getOpenFileNames(self, "选择 PDF", "", "PDF (*.pdf)")
        for f in files:
            if f not in [self.extract_list.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self.extract_list.count())]:
                self.extract_list.addItem(Path(f).name)
                self.extract_list.item(self.extract_list.count() - 1).setData(Qt.ItemDataRole.UserRole, f)

    def _extract_remove(self):
        for item in reversed(self.extract_list.selectedItems()):
            self.extract_list.takeItem(self.extract_list.row(item))

    def _extract_start(self):
        files = self._extract_files()
        if not files:
            QMessageBox.warning(self, "提示", "请先添加 PDF 文件！"); return
        pr = self.extract_range.text().strip()
        if not pr:
            QMessageBox.warning(self, "提示", "请输入页码范围！"); return
        out_dir = self.extract_out_dir.text().strip()
        if not out_dir:
            QMessageBox.warning(self, "提示", "请选择输出目录！"); return

        self.extract_btn_start.setEnabled(False)
        self.progress_bar.setValue(0)
        self._last_output_dir = Path(out_dir)

        def task(on_progress=None, on_log=None):
            results = []
            for f in files:
                out_name = f"{f.stem}_提取.pdf"
                results.append(extract_pages(f, Path(out_dir) / out_name, pr, on_log=on_log))
            return results

        self._run(task, self.extract_btn_start)

    # ------------------------------------------------------------------
    # 删除页面
    # ------------------------------------------------------------------
    def _build_delete_tab(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(6, 6, 6, 6)

        btn = QHBoxLayout()
        self.delete_btn_add = QPushButton("添加 PDF")
        self.delete_btn_add.clicked.connect(self._delete_add)
        btn.addWidget(self.delete_btn_add)
        btn.addWidget(self._btn("删除选中", self._delete_remove))
        btn.addStretch()
        lay.addLayout(btn)

        self.delete_list = _DragDropList()
        btn_clear = QPushButton("清空")
        btn_clear.clicked.connect(self.delete_list.clear)
        lay.addWidget(btn_clear)
        self.delete_list.setMinimumHeight(80)
        lay.addWidget(self.delete_list)

        range_layout = QHBoxLayout()
        range_layout.addWidget(QLabel("要删除的页码："))
        self.delete_range = QLineEdit()
        self.delete_range.setPlaceholderText("例如：2,4,7-9")
        range_layout.addWidget(self.delete_range)
        lay.addLayout(range_layout)

        out = QHBoxLayout()
        out.addWidget(QLabel("输出目录："))
        self.delete_out_dir = QLineEdit()
        self.delete_out_dir.setPlaceholderText("请选择输出目录")
        out.addWidget(self.delete_out_dir)
        btn2 = QPushButton("浏览...")
        btn2.clicked.connect(lambda: self._browse_dir(self.delete_out_dir))
        out.addWidget(btn2)
        lay.addLayout(out)

        self.delete_btn_start = QPushButton("开始删除页面")
        self.delete_btn_start.setStyleSheet("QPushButton{background:#e53935;color:#fff;padding:8px 16px;border-radius:4px}QPushButton:hover{background:#c62828}QPushButton:disabled{background:#ccc}")
        self.delete_btn_start.clicked.connect(self._delete_start)
        lay.addWidget(self.delete_btn_start)
        lay.addStretch()
        return w

    def _delete_files(self):
        return [Path(self.delete_list.item(i).data(Qt.ItemDataRole.UserRole)) for i in range(self.delete_list.count())]

    def _delete_add(self):
        files, _ = __import__("PySide6.QtWidgets", fromlist=["QFileDialog"]).QFileDialog.getOpenFileNames(self, "选择 PDF", "", "PDF (*.pdf)")
        for f in files:
            if f not in [self.delete_list.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self.delete_list.count())]:
                self.delete_list.addItem(Path(f).name)
                self.delete_list.item(self.delete_list.count() - 1).setData(Qt.ItemDataRole.UserRole, f)

    def _delete_remove(self):
        for item in reversed(self.delete_list.selectedItems()):
            self.delete_list.takeItem(self.delete_list.row(item))

    def _delete_start(self):
        files = self._delete_files()
        if not files:
            QMessageBox.warning(self, "提示", "请先添加 PDF 文件！"); return
        pr = self.delete_range.text().strip()
        if not pr:
            QMessageBox.warning(self, "提示", "请输入要删除的页码范围！"); return
        out_dir = self.delete_out_dir.text().strip()
        if not out_dir:
            QMessageBox.warning(self, "提示", "请选择输出目录！"); return

        self.delete_btn_start.setEnabled(False)
        self.progress_bar.setValue(0)
        self._last_output_dir = Path(out_dir)

        def task(on_progress=None, on_log=None):
            results = []
            for f in files:
                out_name = f"{f.stem}_删除后.pdf"
                results.append(delete_pages(f, Path(out_dir) / out_name, pr, on_log=on_log))
            return results

        self._run(task, self.delete_btn_start)

    # ------------------------------------------------------------------
    # 公共工具
    # ------------------------------------------------------------------
    @staticmethod
    def _btn(text, callback):
        btn = QPushButton(text)
        btn.clicked.connect(callback)
        return btn

    def _browse_dir(self, target_edit):
        d = QFileDialog.getExistingDirectory(self, "选择输出目录")
        if d:
            target_edit.setText(d)

    def _run(self, task_func, btn):
        """启动后台任务"""
        self.worker = TaskWorker(task_func)
        self.worker.progress.connect(self._on_progress)
        self.worker.log.connect(self._on_log)
        self.worker.finished.connect(lambda ok, msg: self._on_done(ok, msg, btn))
        self.worker.error.connect(self._on_error)
        self.worker.start()

    def _on_progress(self, cur, total, _name):
        if total > 0:
            self.progress_bar.setValue(int(cur / total * 100))

    def _on_log(self, msg):
        self.log_text.append(msg)

    def _on_error(self, msg):
        self.log_text.append(f"[错误] {msg}")

    def _on_done(self, success, msg, btn):
        btn.setEnabled(True)
        self.progress_bar.setValue(100 if success else 0)
        self.log_text.append(f"{'='*40}")
        self.log_text.append(f"[{'完成' if success else '失败'}] {msg}")
        if success and hasattr(self, "_last_output_dir") and self.settings.get("auto_open_output_dir", True):
            d = self._last_output_dir
            if d and d.exists():
                if platform.system() == "Windows":
                    subprocess.Popen(["explorer", str(d)])
