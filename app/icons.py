# -*- coding: utf-8 -*-
"""线性图标：全部用 QPainter 现画，不依赖图片资源，任意 DPI 都清晰。"""
from __future__ import annotations

import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen


def _pen(color: QColor, width: float) -> QPen:
    pen = QPen(color, width)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    return pen


def _stroke_rounded(p: QPainter, rect: QRectF, radius: float, color: QColor, width: float):
    path = QPainterPath()
    path.addRoundedRect(rect, radius, radius)
    p.setPen(_pen(color, width))
    p.setBrush(Qt.NoBrush)
    p.drawPath(path)


def draw_keyboard(p: QPainter, box: QRectF, color: QColor, width: float = 1.6):
    body = QRectF(box.x() + 0.8, box.y() + 4.4, box.width() - 1.6, 17.2)
    _stroke_rounded(p, body, 3.0, color, width)

    p.setPen(Qt.NoPen)
    p.setBrush(color)
    dot_r = 0.85
    for row_y in (9.6, 13.6):
        for i in range(4):
            cx = box.x() + 5.6 + i * 4.7
            p.drawEllipse(QPointF(cx, box.y() + row_y), dot_r, dot_r)
    # 空格键
    bar = QRectF(box.x() + 9.6, box.y() + 16.9, 7.0, 1.7)
    p.drawRoundedRect(bar, 0.85, 0.85)


def draw_mouse(p: QPainter, box: QRectF, color: QColor, width: float = 1.6):
    cx = box.center().x()
    w, h = 15.4, 23.2
    body = QRectF(cx - w / 2, box.y() + 1.2, w, h)
    _stroke_rounded(p, body, w / 2, color, width)

    p.setPen(_pen(color, width))
    p.drawLine(QPointF(cx, box.y() + 2.4), QPointF(cx, box.y() + 9.4))


def draw_headset(p: QPainter, box: QRectF, color: QColor, width: float = 1.6):
    cx = box.center().x()
    band = QRectF(cx - 8.0, box.y() + 2.4, 16.0, 16.0)
    path = QPainterPath()
    path.arcMoveTo(band, 0)
    path.arcTo(band, 0, 180)
    p.setPen(_pen(color, width))
    p.setBrush(Qt.NoBrush)
    p.drawPath(path)

    cup_w, cup_h = 5.2, 9.0
    for sign in (-1, 1):
        x = cx + sign * 8.0 - (cup_w if sign > 0 else 0)
        cup = QRectF(x, box.y() + 9.4, cup_w, cup_h)
        p.setPen(_pen(color, width))
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(cup, 2.4, 2.4)


def draw_refresh(p: QPainter, box: QRectF, color: QColor, angle: float = 0.0):
    """粗圆环 + 大三角箭头（比例取自参考图），angle 用于查询中的旋转动画（弧度）

    参考图（256²）实测：外径 227、线宽 23（≈外径 10%），
    缺口在上方 46°~110°，三角箭头底边为竖直线、尖端朝向缺口。
    下列系数都以「外半径」为单位，缩放后比例不变。
    """
    cx = box.center().x()
    # 图形比圆环本身高（箭头探出环顶 0.229R），所以圆心要略向下，才能让整体居中
    r_out = 0.462 * min(box.width(), box.height())
    cy = box.center().y() + 0.1145 * r_out
    stroke = r_out * 0.205
    r_mid = r_out - stroke / 2

    p.save()
    p.translate(cx, cy)
    p.rotate(math.degrees(angle))

    # 环：从 110° 逆时针扫 296°，在上方留出缺口
    rect = QRectF(-r_mid, -r_mid, 2 * r_mid, 2 * r_mid)
    arc = QPainterPath()
    arc.arcMoveTo(rect, 110)
    arc.arcTo(rect, 110, 296)
    p.setPen(_pen(color, stroke))
    p.setBrush(Qt.NoBrush)
    p.drawPath(arc)

    # 箭头：竖底边 + 右指尖端
    head = QPainterPath()
    head.moveTo(-0.145 * r_out, -1.250 * r_out)
    head.lineTo(0.300 * r_out, -0.921 * r_out)
    head.lineTo(-0.145 * r_out, -0.560 * r_out)
    head.closeSubpath()
    p.setPen(Qt.NoPen)
    p.setBrush(color)
    p.drawPath(head)

    p.restore()


DRAWERS = {
    "keyboard": draw_keyboard,
    "mouse": draw_mouse,
    "headset": draw_headset,
}


def draw(kind: str, p: QPainter, box: QRectF, color: QColor, width: float = 1.6):
    DRAWERS.get(kind, draw_mouse)(p, box, color, width)
