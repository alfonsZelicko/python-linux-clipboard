# Windows special clipboard script

## What it does:

- This script simulates Linux-style clipboard behavior on Windows.
- When you select text (detects left mouse button release), it captures the selection into a separate in-memory "special clipboard" without altering the normal Windows clipboard.
- Pressing the middle mouse button pastes the content of this special clipboard into the active window, mimicking the Linux middle-click paste behavior.

- .. it is possible to add a new task into windows Scheduled Task
    - Task Scheduler
    - Create Task
    - Run whether user is logged on or not
    - Start a program:
        {root}/start.bat


## Limitations:

- Some applications do not respond to synthetic Ctrl+Insert/Ctrl+V events; in those cases this method may not work.
- Selection detection is heuristic: it triggers on left mouse button release and may sometimes fire even when no text is selected.


## Requirements: 

- Windows
- Python 3.8+

## How to run:
Just run the ```start.bat``` batch script, or...

1. (Optional) Create a virtual environment and activate it:
    - ```python -m venv linuxCb```
    - ```[CMD]: linuxCb\Scripts\activate```
    - ```[PowerShell]: linuxCb\Scripts\Activate.ps1```
~~2. (Optional) Install packages into the virtual environment:~~
    ~~- ```pip install pynput pywin32 python-dotenv rich```~~
3. (Optional) Configure settings in `.env` file:
    - Copy `env.example` to `.env` if it doesn't exist
    - Edit `.env` to adjust timing values and debug mode
4. Run the script:
    - ```python linux-clipboard.py```

## Configuration

All runtime tweaks can be set through environment variables (for local development place them in `.env`). Defaults are listed in `env.example`. You no need to change/set... it is mostly for debug purposes.

| Variable | Default | Description |
| --- | --- | --- |
| `COPY_PRESS_DURATION` | `0.05` | How long to hold `Ctrl+C` while capturing a selection. |
| `PASTE_PRESS_DURATION` | `0.05` | How long to hold `Ctrl+V` during paste. |
| `WAIT_BEFORE_COPY` | `0.05` | Delay after mouse selection before issuing copy. |
| `CLIPBOARD_TIMEOUT` | `0.5` | Maximum time to wait for clipboard content to change after copy. |
| `CLIPBOARD_CHECK_INTERVAL` | `0.05` | Poll interval while waiting for clipboard change. |
| `COPY_RESTORE_DELAY` | `0.01` | Delay before restoring the original clipboard after copy. |
| `PASTE_SETTLE_DELAY` | `0.02` | Wait after loading special clipboard into the system clipboard before pasting. |
| `PASTE_RESTORE_DELAY` | `0.08` | Wait after sending `Ctrl+V` before restoring the original clipboard. |
| `MAIN_LOOP_SLEEP` | `0.1` | Sleep interval for the main listener loop. |
| `MIN_DRAG_DISTANCE` | `5` | Minimum cursor travel (pixels) that counts as a drag selection. |
| `MAX_CLICK_DURATION` | `0.15` | Maximum duration (seconds) for a click to count as simple click. Longer presses count as selections. |
| `DOUBLE_CLICK_MAX_INTERVAL` | `0.35` | Time window for double/triple click detection. |
| `DEBUG` | `1` | Debug verbosity (0 = off). |

## TODOS:
 - [ ] add support for text selecting with 'shift'+ arrows/ctrl+shift/... keys
