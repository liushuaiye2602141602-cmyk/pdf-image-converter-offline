# -*- coding: utf-8 -*-
"""
设置页面：默认输出目录、图片质量、DPI、文件重名处理、完成后打开文件夹
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QLineEdit, QGroupBox, QSpinBox, QMessageBox,
    QRadioButton, QButtonGroup, QCheckBox, QFileDialog,
)
from PySide6.QtCore import Qt
from app.config.settings import Settings


class SettingsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings = Settings()
        self._init_ui()
        self._load_settings()

    def _init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(12)

        # ========== 输出目录 ==========
        dir_group = QGroupBox("输出目录")
        dir_lay = QVBoxLayout(dir_group)

        self.radio_source = QRadioButton("使用原文件所在目录")
        self.radio_custom = QRadioButton("使用自定义目录")
        self.radio_source.toggled.connect(self._on_dir_mode_changed)

        self.edit_custom_dir = QLineEdit()
        self.edit_custom_dir.setPlaceholderText("请选择默认输出目录")
        self.edit_custom_dir.setEnabled(False)
        self.btn_browse = QPushButton("浏览...")
        self.btn_browse.setEnabled(False)
        self.btn_browse.clicked.connect(self._browse_dir)

        dir_lay.addWidget(self.radio_source)
        dir_lay.addWidget(self.radio_custom)
        dir_row = QHBoxLayout()
        dir_row.addWidget(self.edit_custom_dir)
        dir_row.addWidget(self.btn_browse)
        dir_lay.addLayout(dir_row)

        root.addWidget(dir_group)

        # ========== 图片质量 ==========
        quality_group = QGroupBox("图片质量")
        q_lay = QHBoxLayout(quality_group)
        q_lay.addWidget(QLabel("默认质量："))
        self.spin_quality = QSpinBox()
        self.spin_quality.setRange(1, 100)
        self.spin_quality.setValue(90)
        self.spin_quality.setSuffix(" %")
        q_lay.addWidget(self.spin_quality)
        q_lay.addWidget(QLabel("（建议 90，值越高图片越清晰，文件越大）"))
        q_lay.addStretch()
        root.addWidget(quality_group)

        # ========== DPI ==========
        dpi_group = QGroupBox("PDF 转图片 DPI")
        d_lay = QHBoxLayout(dpi_group)
        d_lay.addWidget(QLabel("默认 DPI："))
        self.combo_dpi = QComboBox()
        self.combo_dpi.addItems(["150", "200", "300", "600"])
        self.combo_dpi.setCurrentText("300")
        d_lay.addWidget(self.combo_dpi)
        d_lay.addWidget(QLabel("（值越高越清晰，300 适合打印，150 适合屏幕显示）"))
        d_lay.addStretch()
        root.addWidget(dpi_group)

        # ========== 文件重名处理 ==========
        conflict_group = QGroupBox("文件重名处理")
        c_lay = QVBoxLayout(conflict_group)
        self.radio_rename = QRadioButton("自动重命名（追加 _1、_2 等编号）")
        self.radio_overwrite = QRadioButton("直接覆盖原文件")
        self.radio_rename.setChecked(True)

        c_group = QButtonGroup(self)
        c_group.addButton(self.radio_rename)
        c_group.addButton(self.radio_overwrite)

        c_lay.addWidget(self.radio_rename)
        c_lay.addWidget(self.radio_overwrite)
        root.addWidget(conflict_group)

        # ========== 完成后行为 ==========
        behavior_group = QGroupBox("转换完成后")
        b_lay = QVBoxLayout(behavior_group)
        self.check_auto_open = QCheckBox("自动打开输出文件夹")
        self.check_auto_open.setChecked(True)
        b_lay.addWidget(self.check_auto_open)
        root.addWidget(behavior_group)

        # ========== 按钮 ==========
        btn_row = QHBoxLayout()
        btn_reset = QPushButton("恢复默认设置")
        btn_reset.clicked.connect(self._reset)
        btn_save = QPushButton("保存设置")
        btn_save.setStyleSheet("QPushButton{background:#4CAF50;color:#fff;padding:8px 20px;border-radius:4px}QPushButton:hover{background:#45a049}")
        btn_save.clicked.connect(self._save)
        btn_row.addWidget(btn_reset)
        btn_row.addStretch()
        btn_row.addWidget(btn_save)
        root.addLayout(btn_row)

        root.addStretch()

    def _on_dir_mode_changed(self):
        custom = self.radio_custom.isChecked()
        self.edit_custom_dir.setEnabled(custom)
        self.btn_browse.setEnabled(custom)

    def _browse_dir(self):
        d = QFileDialog.getExistingDirectory(self, "选择默认输出目录")
        if d:
            self.edit_custom_dir.setText(d)

    def _load_settings(self):
        """从配置加载当前设置"""
        mode = self.settings.get("output_dir_mode", "source")
        if mode == "custom":
            self.radio_custom.setChecked(True)
        else:
            self.radio_source.setChecked(True)
        self.edit_custom_dir.setText(self.settings.get("default_output_dir", ""))
        self.spin_quality.setValue(self.settings.get("default_image_quality", 90))
        self.combo_dpi.setCurrentText(str(self.settings.get("default_dpi", 300)))

        conflict = self.settings.get("file_conflict_mode", "rename")
        if conflict == "overwrite":
            self.radio_overwrite.setChecked(True)
        else:
            self.radio_rename.setChecked(True)

        self.check_auto_open.setChecked(self.settings.get("auto_open_output_dir", True))

    def _save(self):
        """保存设置"""
        mode = "custom" if self.radio_custom.isChecked() else "source"
        self.settings.set("output_dir_mode", mode)
        self.settings.set("default_output_dir", self.edit_custom_dir.text().strip())
        self.settings.set("default_image_quality", self.spin_quality.value())
        self.settings.set("default_dpi", int(self.combo_dpi.currentText()))
        self.settings.set("file_conflict_mode", "overwrite" if self.radio_overwrite.isChecked() else "rename")
        self.settings.set("auto_open_output_dir", self.check_auto_open.isChecked())
        QMessageBox.information(self, "提示", "设置已保存！")

    def _reset(self):
        self.settings.reset()
        self._load_settings()
        QMessageBox.information(self, "提示", "已恢复默认设置！")
