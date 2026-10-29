# -*- coding: utf-8 -*-
"""冒烟测试：真实启动整个应用，截图并检查托盘/弹窗/菜单是否正常"""
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "third_party"))

from PySide6.QtCore import QPoint, QTimer  # noqa: E402
from PySide6.QtGui import QGuiApplication  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from app.main import Application  # noqa: E402


def main():
    app = QApplication(sys.argv[:1])
    app.setQuitOnLastWindowClosed(False)

    ctl = Application(app)
    ctl.start()

    def shot(name):
        screen = QGuiApplication.primaryScreen()
        pm = screen.grabWindow(0)
        path = os.path.join(ROOT, name)
        pm.save(path)
        print("shot ->", path, pm.width(), pm.height())

    def stage1():
        print("last_time:", ctl.service.last_time, "busy:", ctl.service.is_busy())
        print("flyout visible:", ctl.flyout.isVisible(), "size:", ctl.flyout.size())
        print("cards:", {k: c.isVisible() for k, c in ctl.flyout.cards.items()})
        print("subtitle:", ctl.flyout.subtitle.text(), "| footer:", ctl.flyout.footer.text())
        print("tray visible:", ctl.tray.tray.isVisible(), "anchor:", ctl.tray.anchor_rect())
        shot("smoke_flyout.png")

    def stage2():
        ctl.tray.popup_menu()
        QTimer.singleShot(700, stage3)

    def stage3():
        print("menu visible:", ctl.tray.menu.isVisible(), "size:", ctl.tray.menu.size())
        shot("smoke_menu.png")
        ctl.tray.menu.close()
        QTimer.singleShot(300, app.quit)

    QTimer.singleShot(2000, stage1)
    QTimer.singleShot(2600, stage2)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
