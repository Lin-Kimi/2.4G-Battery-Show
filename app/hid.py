# -*- coding: utf-8 -*-
"""HID 协议层（纯 ctypes，无第三方依赖）

协议依据（浏览器实测 + 官方驱动逆向）：
- 鼠标 A7 Ultra（VID 0x5253）：col02(0xFF01) Feature 0x11 命令，
  SetFeature(0x11, [~0x06=0xf9, ~0x00=0xff x19]) -> 0.4s -> GetFeature(0x11)，
  响应每字节取反：~W[1]==0x06 子命令、~W[2]==0x53 VID、~W[10]&7=模式(1无线)、
  ~W[11]=电量%、~W[12]=充电状态(1充/0放)
- 耳机 V9 Pro（VID 0x291D）：0xFF90 集合 Output 报告 rid=85，
  WriteFile [85,101,1,0...] -> ReadFile -> [101, 电量, 状态]，
  状态 0=充电 2=放电 4=充满 26=睡眠

设备枚举、报文构造与解析都在这里，上层只拿到 dict（电量 / 充电状态 / 连接模式），
不关心 HID 细节。
"""
from __future__ import annotations

import ctypes
import time
from ctypes import wintypes

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
setupapi = ctypes.WinDLL("setupapi", use_last_error=True)
hid = ctypes.WinDLL("hid", use_last_error=True)

GUID = ctypes.c_ubyte * 16
INVALID_HANDLE = ctypes.c_void_p(-1).value

GENERIC_READ = 0x80000000
GENERIC_WRITE = 0x40000000
OPEN_EXISTING = 3
FILE_SHARE_RW = 3
FILE_FLAG_OVERLAPPED = 0x40000000
WAIT_OBJECT_0 = 0
ERROR_IO_PENDING = 997

MOUSE_VID = "vid_5253"
HEADSET_VID = "vid_291d"
HEADSET_USAGE_PAGE = 65424  # 0xFF90


class SP_DEVICE_INTERFACE_DATA(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("InterfaceClassGuid", GUID),
        ("Flags", wintypes.DWORD),
        ("Reserved", ctypes.c_void_p),
    ]


class SP_DEVICE_INTERFACE_DETAIL_DATA(ctypes.Structure):
    _fields_ = [("cbSize", wintypes.DWORD), ("DevicePath", wintypes.WCHAR * 512)]


class HIDP_CAPS(ctypes.Structure):
    _fields_ = [
        ("Usage", ctypes.c_ushort),
        ("UsagePage", ctypes.c_ushort),
        ("InputReportByteLength", ctypes.c_ushort),
        ("OutputReportByteLength", ctypes.c_ushort),
        ("FeatureReportByteLength", ctypes.c_ushort),
        ("Reserved", ctypes.c_ushort * 17),
        ("NumberLinkCollectionNodes", ctypes.c_ushort),
        ("NumberInputButtonCaps", ctypes.c_ushort),
        ("NumberInputValueCaps", ctypes.c_ushort),
        ("NumberInputDataIndices", ctypes.c_ushort),
        ("NumberOutputButtonCaps", ctypes.c_ushort),
        ("NumberOutputValueCaps", ctypes.c_ushort),
        ("NumberOutputDataIndices", ctypes.c_ushort),
        ("NumberFeatureButtonCaps", ctypes.c_ushort),
        ("NumberFeatureValueCaps", ctypes.c_ushort),
        ("NumberFeatureDataIndices", ctypes.c_ushort),
    ]


class OVERLAPPED(ctypes.Structure):
    _fields_ = [
        ("Internal", ctypes.c_void_p),
        ("InternalHigh", ctypes.c_void_p),
        ("Offset", wintypes.DWORD),
        ("OffsetHigh", wintypes.DWORD),
        ("hEvent", ctypes.c_void_p),
    ]


setupapi.SetupDiGetClassDevsW.restype = ctypes.c_void_p
setupapi.SetupDiGetClassDevsW.argtypes = [ctypes.POINTER(GUID), ctypes.c_wchar_p,
                                         ctypes.c_void_p, wintypes.DWORD]
setupapi.SetupDiDestroyDeviceInfoList.argtypes = [ctypes.c_void_p]
setupapi.SetupDiEnumDeviceInterfaces.argtypes = [
    ctypes.c_void_p, ctypes.c_void_p, ctypes.POINTER(GUID), wintypes.DWORD,
    ctypes.POINTER(SP_DEVICE_INTERFACE_DATA)]
setupapi.SetupDiEnumDeviceInterfaces.restype = wintypes.BOOL
setupapi.SetupDiGetDeviceInterfaceDetailW.argtypes = [
    ctypes.c_void_p, ctypes.POINTER(SP_DEVICE_INTERFACE_DATA),
    ctypes.POINTER(SP_DEVICE_INTERFACE_DETAIL_DATA), wintypes.DWORD,
    ctypes.POINTER(wintypes.DWORD), ctypes.c_void_p]
setupapi.SetupDiGetDeviceInterfaceDetailW.restype = wintypes.BOOL

hid.HidD_GetPreparsedData.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p)]
hid.HidD_GetPreparsedData.restype = wintypes.BOOL
hid.HidP_GetCaps.argtypes = [ctypes.c_void_p, ctypes.POINTER(HIDP_CAPS)]
hid.HidP_GetCaps.restype = wintypes.ULONG
hid.HidD_FreePreparsedData.argtypes = [ctypes.c_void_p]
hid.HidD_GetFeature.argtypes = [ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD]
hid.HidD_GetFeature.restype = wintypes.BOOL
hid.HidD_SetFeature.argtypes = [ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD]
hid.HidD_SetFeature.restype = wintypes.BOOL

kernel32.CreateFileW.restype = ctypes.c_void_p
kernel32.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                                 ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD,
                                 ctypes.c_void_p]
kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
kernel32.WriteFile.argtypes = [ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD,
                               ctypes.POINTER(wintypes.DWORD), ctypes.POINTER(OVERLAPPED)]
kernel32.ReadFile.argtypes = [ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD,
                              ctypes.POINTER(wintypes.DWORD), ctypes.POINTER(OVERLAPPED)]
kernel32.GetOverlappedResult.argtypes = [ctypes.c_void_p, ctypes.POINTER(OVERLAPPED),
                                         ctypes.POINTER(wintypes.DWORD), wintypes.BOOL]
kernel32.GetOverlappedResult.restype = wintypes.BOOL
kernel32.WaitForSingleObject.argtypes = [ctypes.c_void_p, wintypes.DWORD]
kernel32.WaitForSingleObject.restype = wintypes.DWORD
kernel32.CancelIo.argtypes = [ctypes.c_void_p]
kernel32.CreateEventW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.BOOL,
                                  ctypes.c_wchar_p]
kernel32.CreateEventW.restype = ctypes.c_void_p


def _hid_guid() -> GUID:
    g = GUID()
    hid.HidD_GetHidGuid(ctypes.byref(g))
    return g


def enum_hid_paths() -> list[str]:
    """枚举所有 HID 设备接口路径"""
    g = _hid_guid()
    hdev = setupapi.SetupDiGetClassDevsW(ctypes.byref(g), None, None, 0x12)
    if hdev in (None, 0, INVALID_HANDLE):
        return []
    paths: list[str] = []
    try:
        i = 0
        while True:
            did = SP_DEVICE_INTERFACE_DATA()
            did.cbSize = ctypes.sizeof(SP_DEVICE_INTERFACE_DATA)
            if not setupapi.SetupDiEnumDeviceInterfaces(
                    hdev, None, ctypes.byref(g), i, ctypes.byref(did)):
                break
            i += 1
            need = wintypes.DWORD()
            setupapi.SetupDiGetDeviceInterfaceDetailW(
                hdev, ctypes.byref(did), None, 0, ctypes.byref(need), None)
            detail = SP_DEVICE_INTERFACE_DETAIL_DATA()
            detail.cbSize = 8
            if setupapi.SetupDiGetDeviceInterfaceDetailW(
                    hdev, ctypes.byref(did), ctypes.byref(detail), need.value, None, None):
                paths.append(detail.DevicePath)
    finally:
        setupapi.SetupDiDestroyDeviceInfoList(hdev)
    return paths


def get_caps(path: str):
    """读取集合的 (UsagePage, Usage, InLen, OutLen, FeatureLen)"""
    h = kernel32.CreateFileW(path, GENERIC_READ | GENERIC_WRITE, FILE_SHARE_RW,
                             None, OPEN_EXISTING, 0, None)
    if h in (None, INVALID_HANDLE):
        return None
    try:
        prep = ctypes.c_void_p()
        if not hid.HidD_GetPreparsedData(h, ctypes.byref(prep)):
            return None
        try:
            caps = HIDP_CAPS()
            if hid.HidP_GetCaps(prep, ctypes.byref(caps)) != 0x110000:
                return None
            return (caps.UsagePage, caps.Usage, caps.InputReportByteLength,
                    caps.OutputReportByteLength, caps.FeatureReportByteLength)
        finally:
            hid.HidD_FreePreparsedData(prep)
    finally:
        kernel32.CloseHandle(h)


def find_mouse_path() -> str | None:
    """A7 Ultra 接收器 col02(0xFF01)，Feature 0x11 所在集合"""
    for p in enum_hid_paths():
        low = p.lower()
        if MOUSE_VID in low and "col02" in low:
            return p
    return None


def find_headset_path() -> str | None:
    """V9 Pro 耳机 0xFF90 集合（UsagePage 0xFF90），Input/Output rid=85"""
    for p in enum_hid_paths():
        if HEADSET_VID not in p.lower():
            continue
        caps = get_caps(p)
        if caps and caps[0] == HEADSET_USAGE_PAGE:
            return p
    return None


def query_mouse() -> dict | None:
    """SetFeature(0x11) -> 0.4s -> GetFeature(0x11) -> 解析电量。

    固件对连续查询不稳定（会回显帧），所以靠调用方控制频率（>=60s）。
    失败返回 None。
    """
    path = find_mouse_path()
    if not path:
        return None
    h = kernel32.CreateFileW(path, 0xC0000000, FILE_SHARE_RW, None, OPEN_EXISTING, 0, None)
    if h in (None, INVALID_HANDLE):
        return None
    try:
        size = 65
        buf = (ctypes.c_ubyte * size)()
        buf[0] = 0x11
        for i, v in enumerate([0xF9] + [0xFF] * 19):
            if 1 + i < size:
                buf[1 + i] = v
        if not hid.HidD_SetFeature(h, buf, size):
            return None
        time.sleep(0.4)
        rbuf = (ctypes.c_ubyte * size)()
        rbuf[0] = 0x11
        if not hid.HidD_GetFeature(h, rbuf, size):
            return None
        b = bytes(rbuf)
        if len(b) < 13:
            return None
        if ((~b[1]) & 0xFF) != 0x06 or ((~b[2]) & 0xFF) != 0x53:
            return None
        mode = (~b[10]) & 7
        battery = (~b[11]) & 0xFF
        charging = (~b[12]) & 0xFF
        return {
            "battery": battery,
            "charging": charging == 1,
            "wireless": mode == 1,
        }
    finally:
        kernel32.CloseHandle(h)


def _overlapped_read(h, read_buf, read_size, timeout_ms):
    r_ev = kernel32.CreateEventW(None, True, False, None)
    rov = OVERLAPPED()
    rov.hEvent = r_ev
    read = wintypes.DWORD(0)
    ok = kernel32.ReadFile(h, read_buf, read_size, ctypes.byref(read), ctypes.byref(rov))
    if ok:
        return True, bytes(read_buf[: read.value])
    if ctypes.get_last_error() == ERROR_IO_PENDING:
        if kernel32.WaitForSingleObject(r_ev, timeout_ms) == WAIT_OBJECT_0:
            got = wintypes.DWORD(0)
            kernel32.GetOverlappedResult(h, ctypes.byref(rov), ctypes.byref(got), False)
            return True, bytes(read_buf[: got.value])
        kernel32.CancelIo(h)
        return False, None
    return False, None


def query_headset() -> dict | None:
    """V9 Pro：0xFF90 集合 WriteFile rid=85 帧 -> ReadFile -> [101, 电量, 状态]"""
    path = find_headset_path()
    if not path:
        return None
    h = kernel32.CreateFileW(path, GENERIC_READ | GENERIC_WRITE, FILE_SHARE_RW,
                             None, OPEN_EXISTING, FILE_FLAG_OVERLAPPED, None)
    if h in (None, INVALID_HANDLE):
        return None
    try:
        w_ev = kernel32.CreateEventW(None, True, False, None)
        wbuf = (ctypes.c_ubyte * 64)()
        wbuf[0] = 85
        wbuf[1] = 101
        wbuf[2] = 1
        wov = OVERLAPPED()
        wov.hEvent = w_ev
        written = wintypes.DWORD(0)
        ok = kernel32.WriteFile(h, wbuf, 64, ctypes.byref(written), ctypes.byref(wov))
        if not ok:
            if ctypes.get_last_error() == ERROR_IO_PENDING:
                if kernel32.WaitForSingleObject(w_ev, 1000) != WAIT_OBJECT_0:
                    kernel32.CancelIo(h)
                    return None
            else:
                return None

        rbuf = (ctypes.c_ubyte * 256)()
        ok2, resp = _overlapped_read(h, rbuf, 256, 1200)
        if not ok2 or not resp or len(resp) < 3:
            return None

        offset = -1
        for i in range(len(resp) - 2):
            if resp[i] == 101 and resp[i + 1] <= 100:
                offset = i
                break
        if offset == -1:
            return None

        raw_status = resp[offset + 2]
        # 0=充电 2=放电 3=充电 4=充满 26=睡眠
        status = {0: "charging", 2: "in_use", 3: "charging",
                  4: "full", 26: "sleeping"}.get(raw_status, "unknown")
        return {"battery": resp[offset + 1], "charging": status in ("charging", "full"),
                "wireless": True, "state": status}
    finally:
        kernel32.CloseHandle(h)


def device_present() -> tuple[bool, bool]:
    """(鼠标, 耳机) 是否在位，用于快速检测插拔"""
    return find_mouse_path() is not None, find_headset_path() is not None
