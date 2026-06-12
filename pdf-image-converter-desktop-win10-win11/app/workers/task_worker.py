# -*- coding: utf-8 -*-
"""
后台任务工作线程模块
使用 QThread 在后台执行耗时的转换任务，避免阻塞 GUI 主线程。
"""

from PySide6.QtCore import QThread, Signal


class TaskWorker(QThread):
    """
    通用后台任务工作线程。
    通过信号向 GUI 主线程传递进度、日志、错误和完成状态。
    """

    # 信号定义
    progress = Signal(int, int, str)    # (当前步骤, 总步骤, 当前文件名)
    log = Signal(str)                    # 日志消息
    finished = Signal(bool, str)         # (是否成功, 结果消息)
    error = Signal(str)                  # 错误消息

    def __init__(self, task_func, parent=None):
        """
        参数:
            task_func: 要执行的任务函数，签名为 task_func(on_progress, on_log) -> result
            parent: 父对象
        """
        super().__init__(parent)
        self._task_func = task_func
        self._is_cancelled = False

    def run(self):
        """线程执行入口"""
        try:
            self._is_cancelled = False

            def on_progress(current, total, filename=""):
                if not self._is_cancelled:
                    self.progress.emit(current, total, filename)

            def on_log(message):
                if not self._is_cancelled:
                    self.log.emit(message)

            result = self._task_func(on_progress=on_progress, on_log=on_log)

            if not self._is_cancelled:
                if isinstance(result, str):
                    self.finished.emit(True, result)
                elif isinstance(result, list):
                    self.finished.emit(True, f"完成，共处理 {len(result)} 项")
                else:
                    self.finished.emit(True, "任务完成")

        except Exception as e:
            if not self._is_cancelled:
                self.error.emit(str(e))
                self.finished.emit(False, f"任务失败：{str(e)}")

    def cancel(self):
        """取消任务"""
        self._is_cancelled = True
