# -*- coding: utf-8 -*-
"""托盘图标 + SiliconUI 圆角菜单"""
from __future__ import annotations

from PySide6.QtCore import QObject, QPoint, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QGuiApplication, QCursor, QIcon
from PySide6.QtWidgets import QSystemTrayIcon
from siui.components.menu_ import (
    ActionItemsWidgetStyleData,
    MenuStyleData,
    SeperatorItemsWidgetStyleData,
    SiRoundedMenu,
)

from . import autostart, theme


def _style_menu_light():
    """把 SiliconUI 的深色菜单改成浅色（设计稿是浅色面板）"""
    MenuStyleData.background_color = QColor("#FBFBFB")
    MenuStyleData.border_color = QColor("#E3E3E3")
    ActionItemsWidgetStyleData.label_text_color_enabled = QColor("#1A1A1A")
    ActionItemsWidgetStyleData.label_text_color_disabled = QColor("#A0A0A0")
    ActionItemsWidgetStyleData.hover_overlay_color_idle = QColor(0, 0, 0, 0)
    ActionItemsWidgetStyleData.hover_overlay_color_hovered = QColor(0, 0, 0, 14)
    ActionItemsWidgetStyleData.checked_indicator_color_checked = theme.ACCENT
    ActionItemsWidgetStyleData.checked_indicator_color_unchecked = QColor(0, 0, 0, 0)
    SeperatorItemsWidgetStyleData.seperator_color = QColor("#E8E8E8")


class TrayController(QObject):
    quit_requested = Signal()
    open_requested = Signal()
    refresh_requested = Signal()
    autostart_changed = Signal(bool)

    def __init__(self, service, parent=None):
        super().__init__(parent)
        self._service = service

        self.tray = QSystemTrayIcon(QIcon(autostart.asset("app.ico")), self)
        self.tray.setToolTip("2.4G 设备电量")
        self.tray.activated.connect(self._on_activated)

        _style_menu_light()
        self.menu = SiRoundedMenu()
        self._build_menu()

        self.tray.show()

        # 登录初期 Explorer 的托盘区可能还没准备好，图标会“吞掉”，
        # 开机自启尤其容易碰上，这里重试几次直到图标真的挂上去
        self._tray_retries = 15
        self._tray_timer = QTimer(self)
        self._tray_timer.setInterval(2000)
        self._tray_timer.timeout.connect(self._ensure_tray_visible)
        self._tray_timer.start()

    def _ensure_tray_visible(self):
        if self.tray.isVisible():
            self._tray_timer.stop()
            return
        self.tray.show()
        self._tray_retries -= 1
        if self._tray_retries <= 0:
            self._tray_timer.stop()

    # ---------------- 菜单 ----------------
    def _build_menu(self):
        self.act_open = self.menu.addAction("打开面板")
        self.act_open.triggered.connect(self.open_requested.emit)

        self.act_refresh = self.menu.addAction("立即刷新")
        self.act_refresh.triggered.connect(self.refresh_requested.emit)

        self.menu.addSeparator()

        self.act_autostart = self.menu.addAction("开机自启动")
        self.act_autostart.setCheckable(True)
        self.act_autostart.setChecked(autostart.is_autostart())
        self.act_autostart.triggered.connect(self._toggle_autostart)

        self.menu.addSeparator()

        self.act_quit = self.menu.addAction("退出")
        self.act_quit.triggered.connect(self.quit_requested.emit)

    def _toggle_autostart(self, checked: bool):
        if not autostart.set_autostart(checked):
            self.act_autostart.setChecked(not checked)
            return
        self.autostart_changed.emit(checked)

    def set_autostart_checked(self, enabled: bool):
        """只同步勾选状态，不触发 triggered"""
        self.act_autostart.setChecked(enabled)

    def popup_menu(self):
        self.act_autostart.setChecked(autostart.is_autostart())
        self.menu.popup(self._menu_pos())

    def _menu_pos(self) -> QPoint:
        """算出菜单左上角（按“看得见的那块”对齐）

        菜单窗口四周有 32px 的阴影留白，真正画出来的背景是内缩的，
        而 popup() 会自己把窗口按这个留白挪开、让滚动区落在传入点上，
        所以这里传的是可见区域的坐标。

        托盘图标永远贴着屏幕底边，若向下展开会掉到任务栏后面被裁掉，
        因此整块摆在光标上方，再夹进屏幕可用区域。
        """
        cursor = QCursor.pos()
        screen = QGuiApplication.screenAt(cursor) or QGuiApplication.primaryScreen()
        area = screen.availableGeometry()

        # 先量尺寸（popup 内部也会再算一次，结果一致）
        self.menu._prepareToPopup()
        self.menu._ensureProperSizing()
        frame = self.menu.size()
        m = self.menu._margins
        vis_w = max(80, frame.width() - m.left() - m.right())
        vis_h = max(60, frame.height() - m.top() - m.bottom())

        x = cursor.x() - vis_w + 6          # 右边大致齐光标
        y = cursor.y() - 6 - vis_h          # 整块放在光标上方

        x = max(area.left() + 4, min(x, area.right() - vis_w - 4))
        if y + vis_h > area.bottom() - 4:   # 托盘高度落在任务栏里，抬到任务栏上方
            y = area.bottom() - 4 - vis_h
        y = max(area.top() + 4, y)
        return QPoint(x, y)

    def is_menu_visible(self) -> bool:
        return self.menu.isVisible()

    # ---------------- 托盘事件 ----------------
    def _on_activated(self, reason):
        if reason in (QSystemTrayIcon.ActivationReason.Trigger,
                      QSystemTrayIcon.ActivationReason.DoubleClick):
            self.open_requested.emit()
        elif reason == QSystemTrayIcon.ActivationReason.Context:
            self.popup_menu()
        elif reason == QSystemTrayIcon.ActivationReason.MiddleClick:
            self.refresh_requested.emit()

    def anchor_rect(self) -> QRectF | None:
        """托盘图标在屏幕上的矩形，用于把面板贴在它旁边"""
        try:
            geo = self.tray.geometry()
            if geo.isValid() and not geo.isNull():
                return QRectF(geo)
        except Exception:
            pass
        screen = QGuiApplication.screenAt(QCursor.pos()) or QGuiApplication.primaryScreen()
        area = screen.availableGeometry()
        pos = QCursor.pos()
        return QRectF(pos.x() - 12, area.bottom() - 40, 24, 24)

    # ---------------- 状态 ----------------
    def set_tooltip(self, text: str):
        self.tray.setToolTip(text)

    def notify(self, title: str, message: str):
        self.tray.showMessage(title, message, QSystemTrayIcon.MessageIcon.Information, 6000)

    def hide(self):
        self.tray.hide()
