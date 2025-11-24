"""Linux-style selection clipboard for Windows."""

import subprocess
import sys
import os

def load_requirements():
    req_file = "requirements.txt"
    if not os.path.exists(req_file):
        return []
    with open(req_file, "r") as f:
        return [line.strip() for line in f if line.strip() and not line.startswith("#")]

def ensure_dependencies():
    required = load_requirements()
    missing = []
    for pkg in required:
        pkg_name = pkg.split("==")[0]  # podpora verzí
        try:
            __import__(pkg_name)
        except ImportError:
            missing.append(pkg)

    if not missing:
        return

    print("Missing packages detected:", missing)
    print("Installing...")

    subprocess.check_call([sys.executable, "-m", "pip", "install", *missing])

ensure_dependencies()

import time
import threading
from pynput import mouse, keyboard
import win32clipboard
import win32con
from dotenv import load_dotenv


# --- Configuration initialization ---
load_dotenv()


def _float_env(name, default):
    value = os.getenv(name)
    try:
        return float(value) if value is not None else float(default)
    except (TypeError, ValueError):
        return float(default)


def _int_env(name, default):
    value = os.getenv(name)
    try:
        return int(value) if value is not None else int(default)
    except (TypeError, ValueError):
        return int(default)


COPY_PRESS_DURATION = _float_env('COPY_PRESS_DURATION', 0.05)
PASTE_PRESS_DURATION = _float_env('PASTE_PRESS_DURATION', 0.05)
WAIT_BEFORE_COPY = _float_env('WAIT_BEFORE_COPY', 0.05)
CLIPBOARD_TIMEOUT = _float_env('CLIPBOARD_TIMEOUT', 0.5)
CLIPBOARD_CHECK_INTERVAL = _float_env('CLIPBOARD_CHECK_INTERVAL', 0.05)
COPY_RESTORE_DELAY = _float_env('COPY_RESTORE_DELAY', 0.01)
PASTE_SETTLE_DELAY = _float_env('PASTE_SETTLE_DELAY', 0.02)
PASTE_RESTORE_DELAY = _float_env('PASTE_RESTORE_DELAY', 0.08)
MAIN_LOOP_SLEEP = _float_env('MAIN_LOOP_SLEEP', 0.1)
MIN_DRAG_DISTANCE = _float_env('MIN_DRAG_DISTANCE', 5)
MAX_CLICK_DURATION = _float_env('MAX_CLICK_DURATION', 0.15)
DOUBLE_CLICK_MAX_INTERVAL = _float_env('DOUBLE_CLICK_MAX_INTERVAL', 0.35)
DEBUG = _int_env('DEBUG', 0)


# --- Global vars init ---
_special_clipboard = ""
_special_lock = threading.Lock()
_clipboard_operation_lock = threading.Lock() 

_mouse_press_pos = None
_mouse_press_time = None
_last_click_time = 0.0

kbd_controller = keyboard.Controller()


# --- Debug helper ---
def debug_print(lvl, message):
    """Prints debug message if DEBUG level is met."""
    if lvl >= DEBUG:
        print(f"[DEBUG {str(lvl).zfill(2)}]: {message}")


# --- Clipboard helpers ---
def get_clipboard_text():
    """Retrieves text from the Windows clipboard or returns an empty string."""
    data = ""
    try:
        win32clipboard.OpenClipboard()
        if win32clipboard.IsClipboardFormatAvailable(win32con.CF_UNICODETEXT):
            data = win32clipboard.GetClipboardData(win32con.CF_UNICODETEXT)
    except Exception as e:
        debug_print(3, f"Error reading clipboard: {e}")
        data = ""
    finally:
        try:
            win32clipboard.CloseClipboard()
        except Exception:
            pass
    return data


def set_clipboard_text(text):
    """Sets the text content of the Windows clipboard."""
    try:
        win32clipboard.OpenClipboard()
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardData(win32con.CF_UNICODETEXT, text)
    except Exception as e:
        debug_print(3, f"Error writing clipboard: {e}")
    finally:
        try:
            win32clipboard.CloseClipboard()
        except Exception:
            pass


# --- Clipboard handlers ---
def copy_selection_to_special():
    """Copy current selection into the special clipboard without disturbing the system clipboard."""

    debug_print(1, "Starting copy_selection_to_special()")
    with _clipboard_operation_lock:
        time.sleep(WAIT_BEFORE_COPY)
        original = get_clipboard_text()
        debug_print(2, f"Original clipboard saved: {repr(original[:50])}")

        debug_print(1, "Sending Ctrl+C for copy")
        with kbd_controller.pressed(keyboard.Key.ctrl):
            kbd_controller.press('c')
            time.sleep(COPY_PRESS_DURATION)
            kbd_controller.release('c')

        captured = ""
        start_time = time.time()
        while time.time() - start_time < CLIPBOARD_TIMEOUT:
            time.sleep(CLIPBOARD_CHECK_INTERVAL)
            captured = get_clipboard_text()
            if captured and captured != original:
                debug_print(1, f"Clipboard changed after {time.time() - start_time:.3f}s. Proceeding.")
                break
            debug_print(3, f"Clipboard content check ({time.time() - start_time:.3f}s): no change yet.")

        if not (captured and captured != original):
            debug_print(1, f"No clipboard change detected within {CLIPBOARD_TIMEOUT}s; using last read.")
            captured = get_clipboard_text()

        debug_print(2, f"Captured text: {repr(captured[:50])}")

        if captured and captured != original:
            with _special_lock:
                global _special_clipboard
                _special_clipboard = captured
                debug_print(1, f"Stored in special clipboard: {len(captured)} chars")
        else:
            debug_print(1, "Skipped storing to special clipboard (empty or identical content).")

        time.sleep(COPY_RESTORE_DELAY)
        set_clipboard_text(original)
        debug_print(2, "Original clipboard restored.")

    debug_print(1, "Finished copy_selection_to_special()")


def paste_special_clipboard():
    """Paste from the special clipboard while preserving the system clipboard."""

    debug_print(1, "Starting paste_special_clipboard()")
    with _clipboard_operation_lock:
        with _special_lock:
            to_paste = _special_clipboard

        if not to_paste:
            debug_print(1, "Special clipboard is empty. Nothing to paste.")
            return

        debug_print(2, f"Pasting: {repr(to_paste[:50])}")
        original = get_clipboard_text()
        set_clipboard_text(to_paste)
        time.sleep(PASTE_SETTLE_DELAY)

        debug_print(1, "Sending Ctrl+V for paste")
        with kbd_controller.pressed(keyboard.Key.ctrl):
            kbd_controller.press('v')
            time.sleep(PASTE_PRESS_DURATION)
            kbd_controller.release('v')

        time.sleep(PASTE_RESTORE_DELAY)
        set_clipboard_text(original)
        debug_print(2, "Original clipboard restored after paste.")

    debug_print(1, "Finished paste_special_clipboard()")


# --- Event Listeners ---
def on_click(x, y, button, pressed):
    global _mouse_press_pos, _mouse_press_time, _last_click_time
    current_time = time.time()

    try:
        if button == mouse.Button.left:
            if pressed:
                _mouse_press_pos = (x, y)
                _mouse_press_time = time.time()
            else:
                if _mouse_press_pos is not None and _mouse_press_time is not None:

                    dx = x - _mouse_press_pos[0]
                    dy = y - _mouse_press_pos[1]
                    distance = (dx * dx + dy * dy) ** 0.5
                    duration = time.time() - _mouse_press_time

                    if distance >= MIN_DRAG_DISTANCE or duration > MAX_CLICK_DURATION:
                        debug_print(1, f"Selection detected (D:{distance:.1f}px, T:{duration:.3f}s). Triggering copy.")
                        threading.Thread(target=copy_selection_to_special, daemon=True).start()
                    else:
                        if (current_time - _last_click_time) <= DOUBLE_CLICK_MAX_INTERVAL:
                            debug_print(1, "Mouse multiclick detected (time window met). Assuming text is selected and triggering copy.")
                            threading.Thread(target=copy_selection_to_special, daemon=True).start()
                        else:
                            debug_print(1, f"Simple click detected (D:{distance:.1f}px, T:{duration:.3f}s). Waiting for multi-click.")

                    _last_click_time = current_time
                    _mouse_press_pos = None
                    _mouse_press_time = None

        elif button == mouse.Button.middle and pressed:
            debug_print(1, "Middle click detected. Triggering paste.")
            threading.Thread(target=paste_special_clipboard, daemon=True).start()
            
    except Exception as e:
        debug_print(3, f"An error occurred in on_click: {e}")

def on_key_press(key):
    try:
        if key == keyboard.Key.end:
            print("End key pressed, exiting...")
            os._exit(0)
    except Exception as e:
        debug_print(3, f"An error occurred in on_key_press: {e}")


# --- Main function ---
def main():
    print("-------------- Special Clipboard for Windows (REV. 2) ---------------")
    print(f"| DEBUG Level: {DEBUG}                                                    |")
    print("| Select text (left drag) to capture it into the special clipboard. |")
    print("| Click the middle mouse button to paste the content.               |")
    print("| Press Ctrl+C in this console or the End key to exit.              |")
    print("---------------------------------------------------------------------")

    mouse_listener = mouse.Listener(on_click=on_click)
    mouse_listener.start()

    keyboard_listener = keyboard.Listener(on_press=on_key_press)
    keyboard_listener.start()

    try:
        while mouse_listener.is_alive() and keyboard_listener.is_alive():
            time.sleep(MAIN_LOOP_SLEEP)
    except KeyboardInterrupt:
        print("\nKeyboard interrupt detected (Ctrl+C). Exiting...")
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")
    finally:
        if mouse_listener.is_alive():
            mouse_listener.stop()
        if keyboard_listener.is_alive():
            keyboard_listener.stop()
        os._exit(0)

if __name__ == '__main__':
    main()