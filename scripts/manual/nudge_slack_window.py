"""Bring the local Slack desktop window forward with a small visual nudge."""

import time

import win32con
import win32gui


def find_slack_window():
    """Return the first visible desktop window whose title contains Slack."""

    def enum_handler(hwnd, result):
        """Collect visible Slack window handles during Win32 enumeration."""
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            if "Slack" in title:
                result.append(hwnd)

    hwnds = []
    win32gui.EnumWindows(enum_handler, hwnds)
    return hwnds[0] if hwnds else None


def slack_nudge(intensity=10, shakes=10, delay=0.02):
    """Restore, focus, and briefly move the Slack desktop window."""
    hwnd = find_slack_window()
    if not hwnd:
        print("Slack desktop window was not found.")
        return

    win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
    win32gui.SetForegroundWindow(hwnd)

    rect = win32gui.GetWindowRect(hwnd)
    x, y = rect[0], rect[1]

    for _ in range(shakes):
        win32gui.SetWindowPos(hwnd, None, x + intensity, y, 0, 0, win32con.SWP_NOSIZE | win32con.SWP_NOZORDER)
        time.sleep(delay)
        win32gui.SetWindowPos(hwnd, None, x - intensity, y, 0, 0, win32con.SWP_NOSIZE | win32con.SWP_NOZORDER)
        time.sleep(delay)

    win32gui.SetWindowPos(hwnd, None, x, y, 0, 0, win32con.SWP_NOSIZE | win32con.SWP_NOZORDER)


slack_nudge()
