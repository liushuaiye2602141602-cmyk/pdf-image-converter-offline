# -*- coding: utf-8 -*-
"""
主窗口：左侧导航 + 右侧页面切换
"""

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QListWidget, QStackedWidget, QLabel, QAbstractItemView,
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon

# 页面导入，失败时用占位 Widget
try:
    from app.ui.pdf_to_image_page import PDFToImagePage
except ImportError:
    PDFToImagePage = None

try:
    from app.ui.image_to_pdf_page import ImageToPDFPage
except ImportError:
    ImageToPDFPage = None

try:
    from app.ui.image_convert_page import ImageConvertPage
except ImportError:
    ImageConvertPage = None

try:
    from app.ui.pdf_tools_page import PDFToolsPage
except ImportError:
    PDFToolsPage = None

try:
    from app.ui.settings_page import SettingsPage
except ImportError:
    SettingsPage = None


def _placeholder(name):
    """创建占位页面"""
    w = QWidget()
    lay = QVBoxLayout(w)
    lay.addWidget(QLabel(f"页面加载失败：{name}"))
    return w


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PDF Image Converter")
        self.setMinimumSize(QSize(900, 600))
        self._init_ui()

    def _init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ===== 左侧导航 =====
        nav_widget = QWidget()
        nav_widget.setFixedWidth(160)
        nav_widget.setStyleSheet("""
            QWidget { background-color: #2c3e50; }
            QListWidget { background-color: #2c3e50; color: white; border: none;
                          font-size: 13px; padding: 5px; }
            QListWidget::item { padding: 10px 8px; border-radius: 4px; }
            QListWidget::item:selected { background-color: #3498db; }
            QListWidget::item:hover { background-color: #34495e; }
        """)
        nav_layout = QVBoxLayout(nav_widget)
        nav_layout.setContentsMargins(0, 10, 0, 0)

        title = QLabel("PDF Image Converter")
        title.setStyleSheet("color: white; font-size: 12px; font-weight: bold; padding: 8px;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        nav_layout.addWidget(title)

        self.nav_list = QListWidget()
        self.nav_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.nav_list.itemClicked.connect(self._on_nav_clicked)
        nav_layout.addWidget(self.nav_list)
        nav_layout.addStretch()

        layout.addWidget(nav_widget)

        # ===== 右侧页面 =====
        self.stack = QStackedWidget()
        self.stack.setStyleSheet("QStackedWidget { background-color: #f5f5f5; }")
        layout.addWidget(self.stack)

        # 注册页面
        self._pages = []
        nav_items = [
            ("图片转 PDF", ImageToPDFPage),
            ("PDF 转图片", PDFToImagePage),
            ("图片格式转换", ImageConvertPage),
            ("PDF 合并拆分", PDFToolsPage),
            ("设置", SettingsPage),
        ]

        for name, cls in nav_items:
            self.nav_list.addItem(name)
            if cls is not None:
                page = cls()
            else:
                page = _placeholder(name)
            self.stack.addWidget(page)
            self._pages.append(page)

        # 默认选中第一个
        self.nav_list.setCurrentRow(0)

    def _on_nav_clicked(self, item):
        row = self.nav_list.row(item)
        self.stack.setCurrentIndex(row)
