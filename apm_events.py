import time
from pynput import keyboard, mouse


def start_listeners(monitor):
    if getattr(monitor, 'keyboard_listener', None) is not None:
        return
    if keyboard and mouse:
        monitor.keyboard_listener = keyboard.Listener(on_press=monitor.action_event)
        monitor.mouse_listener = mouse.Listener(on_click=monitor.action_event, on_scroll=monitor.action_event)
        monitor.keyboard_listener.start()
        monitor.mouse_listener.start()
    else:
        monitor.current_label.config(text="APM: ?")


def stop_listeners(monitor):
    try:
        if getattr(monitor, 'keyboard_listener', None) is not None:
            monitor.keyboard_listener.stop()
            monitor.keyboard_listener = None
    except Exception:
        pass
    try:
        if getattr(monitor, 'mouse_listener', None) is not None:
            monitor.mouse_listener.stop()
            monitor.mouse_listener = None
    except Exception:
        pass
