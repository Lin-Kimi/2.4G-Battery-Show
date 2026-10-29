# -*- coding: utf-8 -*-
"""界面控件

SiliconUI 在这里承担：
- SiLinearIndicator  电量条的动画/绘制基类（重写 paintEvent 适配设计稿的「粗填充 + 细轨道」）
- SiTransparentButton 刷新按钮的悬停/按下反馈（重写 paintEvent 叠加图标）
"""
from __future__ import annotations

import math

from PySide6.QtCore import QPointF, QRectF, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFontMetrics, QPainterPath, QPen
from PySide6.QtWidgets import QLabel, QWidget
from siui.components.button import SiTransparentButton
from siui.components.label import SiLinearIndicator
from siui.core import createPainter

from . import icons, theme


class IconWidget(QWidget):
    """线条图标"""

    def __init__(self, kind: str, size: int = 26, color: QColor | None = None, parent=None):
        super().__init__(parent)
        self._kind = kind
        self._color = QColor(color or theme.TEXT_STRONG)
        self.setFixedSize(QSize(size, size))
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

    def setKind(self, kind: str):
        self._kind = kind
        self.update()

    def setColor(self, color: QColor):
        self._color = QColor(color)
        self.update()

    def paintEvent(self, event):
        with createPainter(self) as p:
            icons.draw(self._kind, p, QRectF(0, 0, self.width(), self.height()), self._color, 1.55)


class BatteryBar(SiLinearIndicator):
    """电量条：贯穿整行的 1px 细轨道 + 3px 圆角填充"""

    FILL_H = 3.0

    def __init__(self, parent=None):
        super().__init__(parent)
        self._ratio = 0.0
        self.setFixedHeight(6)
        self.setBorderRadius(self.FILL_H / 2)
        self.setColor(theme.ACCENT)

    def ratio(self) -> float:
        return self._ratio

    def setValue(self, ratio: float, color: QColor | None = None, animate: bool = True):
        self._ratio = max(0.0, min(1.0, float(ratio)))
        if color is not None:
            self.setColor(color)
        self._apply(animate)

    def _apply(self, animate: bool):
        self.setVisualWidth(self.width() * self._ratio, ani=animate)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._apply(False)

    def paintEvent(self, event):
        w = float(self.width())
        h = float(self.height())
        fill_w = max(0.0, min(float(self.visualWidth), w))

        with createPainter(self) as p:
            # 轨道
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(theme.TRACK)
            p.drawRect(QRectF(0.0, float((int(h) - 1) // 2), w, 1.0))

            # 已完成部分
            if fill_w > 0.6:
                bar_h = self.FILL_H
                radius = self.borderRadius()
                path = QPainterPath()
                path.addRoundedRect(
                    QRectF(0.0, float((int(h) - int(bar_h)) // 2), max(fill_w, bar_h), bar_h),
                    radius, radius,
                )
                p.setBrush(self.color)
                p.drawPath(path)


class RefreshButton(SiTransparentButton):
    """右上角刷新按钮：悬停底色 + 查询中旋转"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(QSize(32, 32))
        self.setBorderRadius(6)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._angle = 0.0
        self._busy = False

        self._timer = QTimer(self)
        self._timer.setInterval(24)
        self._timer.timeout.connect(self._spin)

    def setBusy(self, busy: bool):
        if busy == self._busy:
            return
        self._busy = busy
        if busy:
            self._timer.start()
        else:
            self._timer.stop()
            self._angle = 0.0
            self.update()

    def _spin(self):
        self._angle = (self._angle + 0.24) % (2 * math.pi)
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        with createPainter(self) as p:
            box = QRectF(0, 0, self.width(), self.height()).adjusted(7.5, 7.5, -7.5, -7.5)
            icons.draw_refresh(p, box, theme.TEXT_STRONG, self._angle)


class AutoStartToggle(QWidget):
    """页脚右下角的「开机自启」勾选：12px 圆角方框 + 文案"""

    BOX = 12
    GAP = 7

    toggled = Signal(bool)

    def __init__(self, text: str, parent=None):
        super().__init__(parent)
        self._text = text
        self._checked = False
        self._hover = False
        self._font = theme.font(11)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover)

        width = self.BOX + self.GAP + QFontMetrics(self._font).horizontalAdvance(text) + 2
        self.setFixedSize(QSize(width, 18))

    # ---------------- 状态 ----------------
    def isChecked(self) -> bool:
        return self._checked

    def setChecked(self, checked: bool, emit: bool = False):
        checked = bool(checked)
        if checked == self._checked:
            return
        self._checked = checked
        self.update()
        if emit:
            self.toggled.emit(checked)

    # ---------------- 交互 ----------------
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.rect().contains(event.position().toPoint()):
            self.setChecked(not self._checked, emit=True)
        super().mouseReleaseEvent(event)

    def enterEvent(self, event):
        self._hover = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hover = False
        self.update()
        super().leaveEvent(event)

    # ---------------- 绘制 ----------------
    def paintEvent(self, event):
        with createPainter(self) as p:
            top = (self.height() - self.BOX) / 2
            rect = QRectF(0.5, top + 0.5, self.BOX - 1, self.BOX - 1)
            path = QPainterPath()
            path.addRoundedRect(rect, 3.5, 3.5)

            if self._checked:
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(theme.ACCENT)
                p.drawPath(path)
                pen = QPen(QColor("#FFFFFF"), 1.5)
                pen.setCapStyle(Qt.PenCapStyle.RoundCap)
                pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
                p.setPen(pen)
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.drawPolyline([
                    QPointF(3.4, top + 6.2),
                    QPointF(5.4, top + 8.4),
                    QPointF(8.9, top + 4.0),
                ])
            else:
                border = QColor("#9E9E9E") if self._hover else QColor("#C4C4C4")
                p.setPen(QPen(border, 1))
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.drawPath(path)

            p.setPen(theme.TEXT_SUB if self._checked else theme.TEXT_FAINT)
            p.setFont(self._font)
            p.drawText(QRectF(self.BOX + self.GAP, 0, self.width() - self.BOX - self.GAP, self.height()),
                       Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, self._text)


class DeviceCard(QWidget):
    """设备卡片：左侧图标 + 名称/电量条/副标题 + 右侧百分比/状态"""

    # 卡片内布局（相对卡片左上角，来自设计稿换算）
    ICON_RECT = (18, 17, 26, 26)
    TITLE_RECT = (61, 14, 170, 23)
    BAR_RECT = (61, 39, 211, 6)
    SUB_RECT = (61, 47, 211, 18)
    PCT_RECT = (239, 11, 80, 27)
    STATUS_RECT = (239, 37, 80, 18)

    def __init__(self, reading=None, parent=None):
        super().__init__(parent)
        self.setFixedSize(QSize(theme.CARD_W, theme.CARD_H))
        self._reading = reading
        self._low = False

        x, y, w, h = self.ICON_RECT
        self.icon = IconWidget(getattr(reading, "icon", "mouse"), 26, parent=self)
        self.icon.setGeometry(x, y, w, h)

        self.title = self._label(theme.font(15, theme.QFontWeight.Medium), theme.TEXT_STRONG)
        self.title.setGeometry(*self.TITLE_RECT)

        self.bar = BatteryBar(self)
        self.bar.setGeometry(*self.BAR_RECT)

        self.subtitle = self._label(theme.font(11), theme.TEXT_SUB)
        self.subtitle.setGeometry(*self.SUB_RECT)

        self.percent = self._label(theme.font(18, theme.QFontWeight.DemiBold), theme.TEXT_STRONG,
                                   align=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.percent.setGeometry(*self.PCT_RECT)

        self.status = self._label(theme.font(11), theme.TEXT_SUB,
                                  align=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.status.setGeometry(*self.STATUS_RECT)

        if reading is not None:
            self.setReading(reading)

    # ---------------- helpers ----------------
    def _label(self, font, color: QColor, align=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter):
        lab = QLabel(self)
        lab.setFont(font)
        lab.setStyleSheet(f"color: {color.name()}; background: transparent;")
        lab.setAlignment(align)
        lab.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        return lab

    def _set_color(self, label: QLabel, color: QColor):
        label.setStyleSheet(f"color: {color.name()}; background: transparent;")

    # ---------------- 数据 ----------------
    def setReading(self, reading, animate: bool = True):
        self._reading = reading
        self.icon.setKind(reading.icon)

        metrics = QFontMetrics(self.title.font())
        self.title.setText(metrics.elidedText(reading.title, Qt.TextElideMode.ElideRight,
                                              self.TITLE_RECT[2]))
        self.subtitle.setText(reading.subtitle)

        battery = reading.battery if reading.online else None
        if battery is None:
            self.percent.setText("--%")
            self.status.setText("未连接")
            self._set_color(self.percent, theme.TEXT_FAINT)
            self.bar.setValue(0.0, theme.TRACK, animate=False)
            return

        self._low = battery < theme.LOW_THRESHOLD
        accent = theme.LOW if self._low else theme.ACCENT
        self.percent.setText(f"{battery}%")
        self.status.setText(reading.status or "使用中")
        self._set_color(self.percent, theme.LOW if self._low else theme.TEXT_STRONG)
        self.bar.setValue(battery / 100.0, accent, animate=animate)

    def paintEvent(self, event):
        with createPainter(self) as p:
            rect = QRectF(0.5, 0.5, self.width() - 1, self.height() - 1)
            path = QPainterPath()
            path.addRoundedRect(rect, theme.CARD_RADIUS, theme.CARD_RADIUS)
            p.setPen(QPen(theme.CARD_BORDER, 1))
            p.setBrush(theme.CARD_BG)
            p.drawPath(path)
