# -*- coding: utf-8 -*-
"""开机自启动

同时维护两条注册途径（任一存在即视为已开启）：
  1. HKCU\\...\\CurrentVersion\\Run   —— 轻量、标准做法
  2. 启动文件夹里的 .lnk 快捷方式        —— 不容易被“注册表清理”类工具带走

另外把用户意图存在 settings.json 里：每次启动调用 ensure_autostart()，
发现偏好是开、但注册项被删掉或指向旧路径，就当场补回去（自愈）。
"""
from __future__ import annotations

import os
import subprocess
import sys

from . import config

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
VALUE_NAME = "McHoseBattery"
LINK_NAME = "2.4G设备电量助手.lnk"
CREATE_NO_WINDOW = 0x08000000


# ---------------- 路径 ----------------
def app_dir() -> str:
    """assets 所在目录（打包后是 _MEIPASS，开发时是项目根目录）"""
    if hasattr(sys, "_MEIPASS"):
        return sys._MEIPASS
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def asset(name: str) -> str:
    return os.path.join(app_dir(), "assets", name)


def startup_dir() -> str:
    base = os.environ.get("APPDATA") or os.path.expanduser("~")
    return os.path.join(base, r"Microsoft\Windows\Start Menu\Programs\Startup")


def shortcut_path() -> str:
    return os.path.join(startup_dir(), LINK_NAME)


# ---------------- 命令行 ----------------
def _launch_spec() -> tuple[str, str, str]:
    """(可执行文件, 参数, 工作目录)"""
    if getattr(sys, "frozen", False):
        exe = os.path.abspath(sys.executable)
        return exe, "--tray", os.path.dirname(exe)
    launcher = os.path.join(app_dir(), "run.py")
    return os.path.abspath(sys.executable), f'"{launcher}" --tray', app_dir()


def entry_command() -> str:
    target, args, _ = _launch_spec()
    return f'"{target}" {args}'


# ---------------- 注册表 ----------------
def read_command() -> str | None:
    try:
        import winreg

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_READ) as key:
            value, _ = winreg.QueryValueEx(key, VALUE_NAME)
            return str(value)
    except Exception:
        return None


def _write_registry(enabled: bool) -> bool:
    try:
        import winreg

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
            if enabled:
                winreg.SetValueEx(key, VALUE_NAME, 0, winreg.REG_SZ, entry_command())
            else:
                try:
                    winreg.DeleteValue(key, VALUE_NAME)
                except OSError:
                    pass
        return True
    except Exception:
        return False


# ---------------- 启动文件夹快捷方式 ----------------
def _shortcut_ok() -> bool:
    """快捷方式在、且当初就是按当前这个 exe 建的

    .lnk 里路径是「分段 + %USERPROFILE% 环境变量」存的，没法可靠地整串匹配，
    所以把建快捷方式时的 exe 路径记进 settings.json 当签名：程序挪了目录/改了名，
    签名对不上就重写一次。
    """
    if not os.path.isfile(shortcut_path()):
        return False
    recorded = (config.get("shortcut_exe") or "").strip().lower()
    return bool(recorded) and recorded == os.path.abspath(sys.executable).lower()


def _write_shortcut() -> bool:
    target, args, workdir = _launch_spec()

    def q(value: str) -> str:
        return value.replace("'", "''")

    script = (
        "$ws = New-Object -ComObject WScript.Shell\n"
        f"$s = $ws.CreateShortcut('{q(shortcut_path())}')\n"
        f"$s.TargetPath = '{q(target)}'\n"
        f"$s.Arguments = '{q(args)}'\n"
        f"$s.WorkingDirectory = '{q(workdir)}'\n"
        f"$s.IconLocation = '{q(target)},0'\n"
        "$s.Description = '2.4G 设备电量助手'\n"
        "$s.Save()\n"
    )
    try:
        os.makedirs(startup_dir(), exist_ok=True)
        subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-WindowStyle", "Hidden",
             "-ExecutionPolicy", "Bypass", "-Command", script],
            capture_output=True,
            timeout=25,
            creationflags=CREATE_NO_WINDOW,
        )
        if os.path.isfile(shortcut_path()):
            config.set("shortcut_exe", os.path.abspath(sys.executable))
            return True
        return False
    except Exception:
        return False


def _remove_shortcut() -> bool:
    try:
        os.remove(shortcut_path())
    except FileNotFoundError:
        pass
    except Exception:
        return False
    return True


# ---------------- 对外 ----------------
def is_autostart() -> bool:
    """两条途径任一在，就算开着（UI 勾选状态用它）"""
    if read_command() is not None:
        return True
    return _shortcut_ok()


def set_autostart(enabled: bool) -> bool:
    """用户点击开关：两条途径一起写/一起删，并记住意图"""
    config.set("autostart", bool(enabled))
    ok = _write_registry(enabled)
    if enabled:
        ok = _write_shortcut() or ok
    else:
        ok = _remove_shortcut() and ok
    return bool(ok)


def _command_target(command: str) -> str:
    command = command.strip()
    if command.startswith('"'):
        end = command.find('"', 1)
        return command[1:end] if end > 0 else command.strip('"')
    return command.split(" ")[0]


def ensure_autostart() -> bool:
    """启动时自愈：偏好是开，就把两条途径都校正到当前程序。

    只在打包版执行——开发调试时不去写注册表，免得把自启动指到 python.exe。
    """
    if not getattr(sys, "frozen", False):
        return False

    want = config.get("autostart")
    if want is None:
        # 首次运行（还没有偏好文件）：默认开启。托盘小工具本来就该开机就在，
        # 用户明确关掉一次之后 settings.json 里就是 false，不会再被顶回来。
        want = True
        config.set("autostart", True)
    if not want:
        return False

    changed = False
    current = (read_command() or "").strip()
    if current.lower() != entry_command().strip().lower():
        old_name = os.path.basename(_command_target(current)).lower()
        new_exe = os.path.basename(os.path.abspath(sys.executable)).lower()
        # python.exe 是开发调试留下的脏值，一律改掉
        dev_leftover = old_name.startswith("python")
        # 没有值、同名程序换了位置、或脏值 —— 都改指当前程序；指向别的程序就不动
        if not current or dev_leftover or old_name == new_exe:
            changed = _write_registry(True) or changed
    if not _shortcut_ok():
        changed = _write_shortcut() or changed
    return changed
