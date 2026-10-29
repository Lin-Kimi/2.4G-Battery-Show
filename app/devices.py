# -*- coding: utf-8 -*-
"""设备模型：把 HID 读数整理成界面能直接用的结构。

要支持新设备（比如 2.4G 键盘），只要在 SPECS 里加一条即可：
标题、图标类型、副标题（接收器/上报方式）、查询函数。
"""
from __future__ import annotations

from dataclasses import dataclass, field

from . import hid

STATUS_TEXT = {
    "in_use": "使用中",
    "charging": "充电中",
    "full": "已充满",
    "sleeping": "睡眠",
    "unknown": "未知",
}


@dataclass(frozen=True)
class DeviceSpec:
    key: str
    title: str          # 卡片主标题
    icon: str           # icons.py 里的图形：mouse / keyboard / headset
    subtitle: str       # 卡片副标题：接收器 · 查询方式
    query: object       # 返回 dict 或 None 的查询函数


@dataclass
class Reading:
    key: str
    title: str
    icon: str
    subtitle: str
    battery: int | None = None
    status: str = ""
    online: bool = False
    extra: dict = field(default_factory=dict)


SPECS: tuple[DeviceSpec, ...] = (
    DeviceSpec(
        key="mouse",
        title="A7 Ultra 鼠标",
        icon="mouse",
        subtitle="CompX 接收器 · 电量查询",
        query=hid.query_mouse,
    ),
    DeviceSpec(
        key="headset",
        title="V9 Pro 耳机",
        icon="headset",
        subtitle="2.4G 接收器 · 自动上报",
        query=hid.query_headset,
    ),
)


def _status_of(raw: dict, spec: DeviceSpec) -> str:
    if "state" in raw:
        return STATUS_TEXT.get(raw["state"], STATUS_TEXT["unknown"])
    return STATUS_TEXT["charging"] if raw.get("charging") else STATUS_TEXT["in_use"]


def read_one(spec: DeviceSpec) -> Reading:
    try:
        raw = spec.query()
    except Exception:
        raw = None
    if not raw:
        return Reading(spec.key, spec.title, spec.icon, spec.subtitle, online=False)
    return Reading(
        key=spec.key,
        title=spec.title,
        icon=spec.icon,
        subtitle=spec.subtitle,
        battery=int(raw.get("battery", 0)),
        status=_status_of(raw, spec),
        online=True,
        extra=raw,
    )


def query_all() -> list[Reading]:
    """按顺序查询全部设备（阻塞，必须放在工作线程里调用）"""
    return [read_one(spec) for spec in SPECS]
