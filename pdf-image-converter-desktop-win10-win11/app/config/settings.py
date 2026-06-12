# -*- coding: utf-8 -*-
"""
应用配置管理模块
负责读取和保存用户设置，使用 JSON 格式存储在用户 AppData 目录下。
配置路径: %APPDATA%/PDFImageConverter/config.json
"""

import json
import os
from pathlib import Path


# 默认配置
DEFAULT_SETTINGS = {
    "default_output_dir": "",           # 空字符串表示使用原文件所在目录
    "output_dir_mode": "source",        # "source" 使用原文件目录, "custom" 使用自定义目录
    "default_image_quality": 90,        # 图片压缩质量 1-100
    "default_dpi": 300,                 # PDF 转图片默认 DPI
    "file_conflict_mode": "rename",     # "rename" 自动重命名, "overwrite" 覆盖
    "auto_open_output_dir": True,       # 转换完成后是否自动打开输出目录
    "last_output_dir": "",              # 上次使用的输出目录
    "window_width": 1100,               # 窗口宽度
    "window_height": 700,               # 窗口高度
}


class Settings:
    """应用配置管理器（单例）"""

    _instance = None
    _config_path = None
    _data = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._data is not None:
            return
        # 配置文件放在用户 AppData 目录，兼容只读目录安装
        appdata = os.environ.get("APPDATA", "")
        if appdata:
            config_dir = Path(appdata) / "PDFImageConverter"
        else:
            # fallback：如果 APPDATA 不存在，用用户主目录
            config_dir = Path.home() / ".PDFImageConverter"
        config_dir.mkdir(parents=True, exist_ok=True)
        self._config_path = config_dir / "config.json"
        self._data = dict(DEFAULT_SETTINGS)
        self.load()

    @property
    def config_path(self):
        return self._config_path

    def load(self):
        """从配置文件加载设置"""
        if self._config_path.exists():
            try:
                with open(self._config_path, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                for key in DEFAULT_SETTINGS:
                    if key in saved:
                        self._data[key] = saved[key]
            except (json.JSONDecodeError, IOError):
                self._data = dict(DEFAULT_SETTINGS)

    def save(self):
        """保存设置到配置文件"""
        try:
            with open(self._config_path, "w", encoding="utf-8") as f:
                json.dump(self._data, f, ensure_ascii=False, indent=2)
        except IOError:
            pass

    def get(self, key, default=None):
        """获取配置项"""
        return self._data.get(key, default)

    def set(self, key, value):
        """设置配置项并自动保存"""
        self._data[key] = value
        self.save()

    def get_all(self):
        """获取所有配置"""
        return dict(self._data)

    def reset(self):
        """重置为默认配置"""
        self._data = dict(DEFAULT_SETTINGS)
        self.save()
