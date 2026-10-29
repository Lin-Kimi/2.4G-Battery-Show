# -*- coding: utf-8 -*-
"""应用组装：托盘 + 面板 + 后台轮询 + 单实例"""
from __future__ import annotations

import sys

from PySide6.QtCore import QObject
from PySide6.QtGui import QIcon
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtWidgets import QApplication

from . import autostart, config, theme
from .flyout import Flyout
from .service import BatteryService
from .tray import TrayController

SERVER_NAME = "mchose-battery-2.4g-flyout"
HIDDEN_FLAGS = ("--tray", "--hidden", "--autostart", "-t")


def launch_hidden() -> bool:
    """带 --tray 等参数启动 = 只驻留托盘，不弹面板"""
    return any(flag in sys.argv for flag in HIDDEN_FLAGS)


def notify_existing(show: bool) -> bool:
    """已有实例在跑：接管给它的消息后自己退出。

    show=False 用于「开机自启 / 重复点图标」的场景——只告诉老实例一声，
    绝不能把面板顶出来。
    """
    sock = QLocalSocket()
    sock.connectToServer(SERVER_NAME)
    if not sock.waitForConnected(200):
        return False
    sock.write(b"show" if show else b"ping")
    sock.flush()
    sock.waitForBytesWritten(200)
    sock.disconnectFromServer()
    return True


class Application(QObject):
    def __init__(self, app: QApplication):
        super().__init__()
        self.app = app
        self._notified: dict[str, bool] = {}

        self.service = BatteryService(theme.REFRESH_INTERVAL)
        self.flyout = Flyout(self.service)
        self.tray = TrayController(self.service)

        self.flyout._menu_open = self.tray.is_menu_visible

        self.tray.open_requested.connect(self.toggle_flyout)
        self.tray.refresh_requested.connect(self.service.refresh)
        self.tray.quit_requested.connect(self.quit)
        self.flyout.refresh_requested.connect(self.service.refresh)
        self.flyout.autostart_toggled.connect(self.set_autostart)
        self.tray.autostart_changed.connect(self.flyout.set_autostart_state)
        self.service.updated.connect(self.on_updated)

        self._listen()

    # ---------------- 单实例 ----------------
    def _listen(self):
        self.server = QLocalServer(self)
        QLocalServer.removeServer(SERVER_NAME)
        self.server.listen(SERVER_NAME)
        self.server.newConnection.connect(self._on_connection)

    def _on_connection(self):
        while self.server.hasPendingConnections():
            conn = self.server.nextPendingConnection()
            conn.readyRead.connect(lambda c=conn: self._on_message(c))
            conn.disconnected.connect(conn.deleteLater)

    def _on_message(self, conn):
        data = bytes(conn.readAll())
        # 只有显式要面板（用户双击 exe）才弹；开机自启的重复实例只发 ping
        if b"show" in data:
            self.toggle_flyout(force_show=True)

    # ---------------- 交互 ----------------
    def toggle_flyout(self, force_show: bool = False):
        anchor = self.tray.anchor_rect()
        if force_show:
            self.flyout.show_near(anchor)
        else:
            self.flyout.toggle_near(anchor)

    def on_updated(self, readings: list):
        self.flyout.apply_readings(readings)

        online = [r for r in readings if r.online]
        if online:
            summary = " · ".join(f"{r.title.split()[0]} {r.battery}%" for r in online)
            self.tray.set_tooltip(f"2.4G 设备电量\n{summary}")
        else:
            self.tray.set_tooltip("2.4G 设备电量\n未检测到设备")

        for reading in online:
            self._check_low_battery(reading)

    def set_autostart(self, enabled: bool):
        """面板里的开关：写注册表失败就回滚显示"""
        if not autostart.set_autostart(enabled):
            enabled = not enabled
        self.tray.set_autostart_checked(enabled)
        self.flyout.set_autostart_state(enabled)

    def _check_low_battery(self, reading):
        key = reading.key
        if reading.battery is None:
            return
        if reading.battery < theme.LOW_THRESHOLD:
            if not self._notified.get(key):
                self._notified[key] = True
                self.tray.notify("电量低，需要充电",
                                 f"{reading.title} 剩余 {reading.battery}%，请及时充电。")
        else:
            self._notified[key] = False

    def quit(self):
        self.service.stop()
        self.tray.hide()
        self.server.close()
        self.app.quit()

    def start(self, start_hidden: bool = False):
        autostart.ensure_autostart()
        self.flyout.set_autostart_state(autostart.is_autostart())
        self.service.start()
        if not start_hidden:
            self.flyout.show_near(self.tray.anchor_rect())


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("2.4G 设备电量助手")
    app.setApplicationDisplayName("2.4G 设备电量助手")
    app.setQuitOnLastWindowClosed(False)
    app.setWindowIcon(QIcon(autostart.asset("app.ico")))

    hidden = launch_hidden()
    config.log_start(hidden)

    if notify_existing(show=not hidden):
        return 0

    controller = Application(app)
    controller.start(start_hidden=hidden)

    return app.exec()
