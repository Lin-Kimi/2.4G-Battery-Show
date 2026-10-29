# -*- coding: utf-8 -*-
"""离线预览工具：用假数据渲染面板并截图，方便核对设计稿（不碰真实硬件）

用法：python tools/preview.py [输出路径]
"""
from __future__ import annotations

import datetime
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "third_party"))

from PySide6.QtCore import QObject, QPoint, Qt, Signal  # noqa: E402
from PySide6.QtGui import QGuiApplication  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from app import devices  # noqa: E402
from app.flyout import Flyout  # noqa: E402


class DummyService(QObject):
    busy_changed = Signal(bool)

    def __init__(self):
        super().__init__()
        self.last_time = datetime.datetime(2026, 10, 28, 16, 53)
        self.interval = 600


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "preview.png")
    app = QApplication(sys.argv[:1])
    app.setQuitOnLastWindowClosed(False)

    service = DummyService()
    flyout = Flyout(service)
    flyout.apply_readings([
        devices.Reading("mouse", "2.4G 无线鼠标", "mouse", "CompX 接收器 · 电量查询",
                        battery=80, status="使用中", online=True),
        devices.Reading("headset", "V9 Pro 耳机", "headset", "2.4G 接收器 · 自动上报",
                        battery=86, status="使用中", online=True),
    ])
    flyout.move(40, 40)
    flyout.show()

    QApplication.processEvents()

    # 以 2 倍 DPR 原生渲染，文字锐利，便于和 2x 设计稿逐像素对比
    from PySide6.QtGui import QImage, QPainter, QPixmap

    dpr = 2
    pm = QPixmap(flyout.size() * dpr)
    pm.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pm)
    painter.scale(dpr, dpr)
    flyout.render(painter, QPoint(0, 0))
    painter.end()

    img = pm.toImage()
    canvas = QImage(img.width(), img.height(), QImage.Format.Format_ARGB32)
    canvas.fill(0xFF333333)
    painter = QPainter(canvas)
    painter.drawImage(0, 0, img)
    painter.end()

    canvas.save(out)
    print("saved", out, canvas.width(), canvas.height())
    return 0


if __name__ == "__main__":
    sys.exit(main())
