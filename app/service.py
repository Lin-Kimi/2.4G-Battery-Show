# -*- coding: utf-8 -*-
"""后台轮询服务：查询 HID 会阻塞 0.4~1.5 秒，全部放到线程池里跑。"""
from __future__ import annotations

import datetime

from PySide6.QtCore import QObject, QRunnable, QThreadPool, QTimer, Signal

from . import devices, theme


class _Signals(QObject):
    done = Signal(list)


class _QueryTask(QRunnable):
    def __init__(self):
        super().__init__()
        self.signals = _Signals()

    def run(self):
        try:
            result = devices.query_all()
        except Exception:
            result = []
        self.signals.done.emit(result)


class BatteryService(QObject):
    """定期查询电量，并通过信号把结果推给界面"""

    updated = Signal(list)      # list[Reading]
    busy_changed = Signal(bool)
    failed = Signal(str)

    def __init__(self, interval: int = theme.REFRESH_INTERVAL, parent=None):
        super().__init__(parent)
        self.interval = interval
        self._busy = False
        self._pool = QThreadPool.globalInstance()
        self._pool.setMaxThreadCount(2)
        self.last_time: datetime.datetime | None = None

        self._timer = QTimer(self)
        self._timer.setInterval(interval * 1000)
        self._timer.timeout.connect(self.refresh)

    # ---------------- public ----------------
    def start(self, immediate: bool = True):
        self._timer.start()
        if immediate:
            self.refresh()

    def stop(self):
        self._timer.stop()

    def is_busy(self) -> bool:
        return self._busy

    def set_interval(self, seconds: int):
        self.interval = seconds
        self._timer.setInterval(seconds * 1000)

    def refresh(self):
        if self._busy:
            return
        self._busy = True
        self.busy_changed.emit(True)

        task = _QueryTask()
        task.signals.done.connect(self._on_done)
        self._pool.start(task)

    # ---------------- private ----------------
    def _on_done(self, readings: list):
        self._busy = False
        self.last_time = datetime.datetime.now()
        self.busy_changed.emit(False)
        self.updated.emit(readings)
