# -*- coding: utf-8 -*-
"""把设计稿和当前渲染上下拼接，方便逐项核对间距与字号

用法：python tools/compare.py 设计稿.png [渲染图.png] [输出.png]
  渲染图默认取项目根目录的 preview.png（可用 tools/preview.py 生成）
  输出默认写到项目根目录的 compare.png
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "third_party"))

from PySide6.QtGui import QColor, QImage, QPainter  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from app import theme  # noqa: E402

# 设计稿里面板可见区域的裁切范围（2 倍图，左上角 + 宽高）
REF_CROP = (23, 21, 760, 617)


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2

    ref_path = sys.argv[1]
    mine_path = sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, "preview.png")
    out_path = sys.argv[3] if len(sys.argv) > 3 else os.path.join(ROOT, "compare.png")

    app = QApplication(sys.argv[:1])  # noqa: F841 - QImage 绘制需要 QGuiApplication 实例

    ref = QImage(ref_path)
    mine = QImage(mine_path)
    if ref.isNull() or mine.isNull():
        print("读不到图片：", ref_path if ref.isNull() else mine_path)
        return 1

    s = theme.SHADOW * 2  # 预览图是 2 倍渲染，阴影留白也要跟着翻倍
    ref_panel = ref.copy(*REF_CROP)
    mine_panel = mine.copy(s, s, theme.PANEL_W * 2, mine.height() - 4 * s)

    out = QImage(760, ref_panel.height() + mine_panel.height() + 12,
                 QImage.Format.Format_ARGB32)
    out.fill(QColor("#333333"))
    painter = QPainter(out)
    painter.drawImage(0, 0, ref_panel)
    painter.drawImage(0, ref_panel.height() + 12, mine_panel)
    painter.end()

    out.save(out_path)
    print("saved", out_path, out.width(), out.height())
    return 0


if __name__ == "__main__":
    sys.exit(main())
