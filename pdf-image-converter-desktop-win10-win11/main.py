# -*- coding: utf-8 -*-
"""
PDF Image Converter - 主入口
启动 PySide6 桌面应用。
"""

import sys
from pathlib import Path

# 将项目根目录加入 sys.path，确保 import 正常
_root = Path(__file__).resolve().parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from app.ui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("PDF Image Converter")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
