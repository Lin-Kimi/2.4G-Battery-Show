# -*- coding: utf-8 -*-
"""开发环境入口：python run.py  |  python run.py --tray"""
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "third_party"))

from app.main import main  # noqa: E402

# if __name__ == "__main__":
#     sys.exit(main())
