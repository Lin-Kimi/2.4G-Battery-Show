# -*- coding: utf-8 -*-
"""视觉规格：颜色、字体、尺寸。

数值来自设计稿（800x659 @2x）按 2 倍换算成逻辑像素。
所有尺寸都以逻辑像素给出，Qt 会按系统 DPI 自动缩放。
"""
from PySide6.QtGui import QColor, QFont

# ---------------- 颜色 ----------------
ACCENT = QColor("#0067C0")          # 填充蓝
ACCENT_PRESSED = QColor("#005BA8")
LOW = QColor("#C42B1C")             # 低电量红

PANEL_BG = QColor("#F9F9F9")
PANEL_BORDER = QColor("#E8E8E8")
CARD_BG = QColor("#FDFDFD")
CARD_BORDER = QColor("#EAEAEA")
CARD_BORDER_HOVER = QColor("#DCDCDC")

TEXT_STRONG = QColor("#1A1A1A")
TEXT_SUB = QColor("#5F5F5F")
TEXT_FAINT = QColor("#8A8A8A")
TRACK = QColor("#8C8C8C")
HOVER = QColor(0, 0, 0, 12)

# ---------------- 字体 ----------------
FAMILIES = ["Segoe UI", "Microsoft YaHei UI", "Microsoft YaHei", "PingFang SC"]

QFontWeight = QFont.Weight


def font(px: int, weight: QFont.Weight = QFont.Weight.Normal) -> QFont:
    f = QFont()
    f.setFamilies(FAMILIES)
    f.setPixelSize(px)
    f.setWeight(weight)
    f.setHintingPreference(QFont.HintingPreference.PreferDefaultHinting)
    return f


# ---------------- 尺寸 ----------------
SHADOW = 5           # 阴影留白（越小越收敛）
PANEL_W = 380
PANEL_RADIUS = 8
PAD = 24             # 左右内边距

CARD_W = PANEL_W - PAD * 2 + 3   # 设计稿卡片 335，右侧留白略小于左侧
CARD_H = 78
CARD_GAP = 12
CARD_RADIUS = 8

CARDS_TOP = 72       # 第一张卡片距离面板顶部
HEADER_TOP = 15
FOOTER_GAP = 26
BOTTOM_PAD = 26

LOW_THRESHOLD = 20
REFRESH_INTERVAL = 600  # 秒（10 分钟）
