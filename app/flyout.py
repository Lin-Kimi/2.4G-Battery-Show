# -*- coding: utf-8 -*-
"""主面板：无边框圆角弹窗，锚定在托盘图标旁"""
from __future__ import annotations

import datetime

from PySide6.QtCore import QRectF, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QGuiApplication, QPainterPath, QPen
from PySide6.QtWidgets import QLabel, QWidget
from siui.core import createPainter

from . import autostart as autostart_reg
from . import devices, theme
from .widgets import AutoStartToggle, DeviceCard, RefreshButton

S = theme.SHADOW


class Flyout(QWidget):
    refresh_requested = Signal()
    autostart_toggled = Signal(bool)

    def __init__(self, service, parent=None):
        super().__init__(None, Qt.WindowType.Tool
                         | Qt.WindowType.FramelessWindowHint
                         | Qt.WindowType.NoDropShadowWindowHint
                         | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowTitle("2.4G 设备电量")
        self.setCursor(Qt.CursorShape.ArrowCursor)

        self._service = service
        self._panel_h = 0
        self._readings: list = []
        self._last_hide = 0.0
        self._anchor = None
        self._hide_guard_ms = 260

        self.panel = QWidget(self)
        self._build()
        self._resize_for(0)
        service.busy_changed.connect(self.set_busy)

    # ---------------- 构建 ----------------
    def _build(self):
        p = self.panel

        self.title = QLabel("电池", p)
        self.title.setFont(theme.font(20, theme.QFontWeight.Medium))
        self.title.setStyleSheet(f"color: {theme.TEXT_STRONG.name()}; background: transparent;")
        self.title.setGeometry(theme.PAD, 12, 200, 30)

        self.subtitle = QLabel("正在读取…", p)
        self.subtitle.setFont(theme.font(12))
        self.subtitle.setStyleSheet(f"color: {theme.TEXT_SUB.name()}; background: transparent;")
        self.subtitle.setGeometry(theme.PAD, 43, 240, 18)

        self.refresh_button = RefreshButton(p)
        self.refresh_button.move(theme.PANEL_W - theme.PAD - 32 + 2, 23)
        self.refresh_button.clicked.connect(self.refresh_requested.emit)

        self.empty = QLabel("接入 2.4G 接收器后会自动显示", p)
        self.empty.setFont(theme.font(12))
        self.empty.setStyleSheet(f"color: {theme.TEXT_FAINT.name()}; background: transparent;")
        self.empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty.setGeometry(theme.PAD, theme.CARDS_TOP, theme.CARD_W, theme.CARD_H)
        self.empty.hide()

        self.cards: dict[str, DeviceCard] = {}
        for spec in devices.SPECS:
            card = DeviceCard(None, p)
            card.hide()
            self.cards[spec.key] = card

        self.footer = QLabel(f"等待首次读取 · {self._refresh_hint()}", p)
        self.footer.setFont(theme.font(11))
        self.footer.setStyleSheet(f"color: {theme.TEXT_FAINT.name()}; background: transparent;")
        self.footer.setGeometry(theme.PAD, 0, theme.CARD_W, 18)

        # 页脚右下角：开机自启
        self.autostart = AutoStartToggle("开机自启", p)
        self.autostart.setChecked(autostart_reg.is_autostart())
        self.autostart.toggled.connect(self.autostart_toggled.emit)

    # ---------------- 尺寸 ----------------
    def _content_height(self, n: int) -> int:
        if n == 0:
            return theme.CARD_H
        return n * theme.CARD_H + (n - 1) * theme.CARD_GAP

    def _resize_for(self, n: int):
        content = self._content_height(n)
        footer_y = theme.CARDS_TOP + content + 23
        panel_h = footer_y + 18 + theme.BOTTOM_PAD

        self._panel_h = panel_h
        self.panel.setGeometry(S, S, theme.PANEL_W, panel_h)
        self.footer.move(theme.PAD, footer_y)
        # 与卡片右边缘对齐
        self.autostart.move(theme.PAD + theme.CARD_W - self.autostart.width(), footer_y)
        self.setFixedSize(QSize(theme.PANEL_W + 2 * S, panel_h + 2 * S))
        if self.isVisible():
            self._place()
        self.update()

    # ---------------- 外观 ----------------
    def paintEvent(self, event):
        panel = QRectF(S, S, theme.PANEL_W, self._panel_h)

        with createPainter(self) as p:
            # 柔和投影：多层圆角矩形叠加
            p.setPen(Qt.PenStyle.NoPen)
            for i in range(S, 0, -1):
                p.setBrush(QColor(0, 0, 0, 7))
                r = theme.PANEL_RADIUS + i
                rect = panel.adjusted(-i, -i + 1, i, i + 1)
                path = QPainterPath()
                path.addRoundedRect(rect, r, r)
                p.drawPath(path)

            # 面板
            path = QPainterPath()
            path.addRoundedRect(panel.adjusted(0.5, 0.5, -0.5, -0.5),
                                theme.PANEL_RADIUS, theme.PANEL_RADIUS)
            p.setPen(QPen(theme.PANEL_BORDER, 1))
            p.setBrush(theme.PANEL_BG)
            p.drawPath(path)

    # ---------------- 数据 ----------------
    def apply_readings(self, readings: list):
        self._readings = readings
        online = [r for r in readings if r.online]

        self.subtitle.setText(f"{len(online)} 台 2.4G 设备" if online else "未检测到 2.4G 设备")

        visible = 0
        for key, card in self.cards.items():
            reading = next((r for r in readings if r.key == key), None)
            if reading is not None and reading.online:
                card.setReading(reading)
                card.move(theme.PAD, theme.CARDS_TOP + visible * (theme.CARD_H + theme.CARD_GAP))
                card.show()
                visible += 1
            else:
                card.hide()

        self.empty.setVisible(visible == 0)
        self._resize_for(visible)

        stamp = (self._service.last_time or datetime.datetime.now()).strftime("%H:%M")
        self.footer.setText(f"{stamp} 更新 · {self._refresh_hint()}")

    def _refresh_hint(self) -> str:
        """把刷新间隔写成人话：600 -> 每 10 分钟自动刷新"""
        seconds = int(getattr(self._service, "interval", theme.REFRESH_INTERVAL))
        if seconds >= 60 and seconds % 60 == 0:
            span = f"{seconds // 60} 分钟"
        else:
            span = f"{seconds} 秒"
        return f"每 {span}自动刷新"

    def set_autostart_state(self, enabled: bool):
        self.autostart.setChecked(enabled)

    def set_busy(self, busy: bool):
        self.refresh_button.setBusy(busy)

    def refresh(self):
        self.refresh_requested.emit()

    # ---------------- 显示/隐藏 ----------------
    def toggle_near(self, anchor: QRectF | None = None):
        if self.isVisible():
            self.hide()
            return
        if self._just_hidden():
            return
        self.show_near(anchor)

    def _just_hidden(self) -> bool:
        import time

        return (time.monotonic() - self._last_hide) * 1000 < self._hide_guard_ms

    def show_near(self, anchor: QRectF | None = None):
        self._anchor = anchor
        self._place()
        self.show()
        self.raise_()
        self.activateWindow()

    def _place(self):
        """按锚点（托盘图标矩形）摆放，保证整窗不超出可用区域"""
        anchor = getattr(self, "_anchor", None)
        screen = QGuiApplication.screenAt(anchor.center().toPoint()) if anchor else None
        screen = screen or QGuiApplication.primaryScreen()
        area = screen.availableGeometry()

        w, h = self.width(), self.height()
        pad = S  # 窗口比可见面板大一圈（阴影），所以边界要让出 pad

        if anchor is not None:
            x = int(anchor.center().x()) - w // 2
            y = int(anchor.top()) - h - 2
            if y < area.top() - pad:          # 上方放不下就翻到下面
                y = int(anchor.bottom()) - pad + 2
        else:
            x = area.right() - w - pad
            y = area.bottom() - h - pad

        x = max(area.left() - pad, min(x, area.right() + pad - w))
        y = max(area.top() - pad, min(y, area.bottom() + pad - h))
        self.move(x, y)

    def hideEvent(self, event):
        import time

        self._last_hide = time.monotonic()
        self.set_busy(False)
        super().hideEvent(event)

    def changeEvent(self, event):
        if event.type() == event.Type.ActivationChange and not self.isActiveWindow():
            QTimer.singleShot(120, self._maybe_hide)
        super().changeEvent(event)

    def _maybe_hide(self):
        if self.isVisible() and not self.isActiveWindow():
            menu = getattr(self, "_menu_open", None)
            if callable(menu) and menu():
                return
            self.hide()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.hide()
            return
        super().keyPressEvent(event)
