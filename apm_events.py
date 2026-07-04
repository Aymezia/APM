import time
from pynput import keyboard, mouse


def start_listeners(monitor):
    if getattr(monitor, 'keyboard_listener', None) is not None:
        return
    if keyboard and mouse:
        def on_keyboard_press(key):
            monitor.handle_input_event('keyboard', key)

        def on_mouse_event(*args, **kwargs):
            monitor.handle_input_event('mouse', args[0] if args else None)

        monitor.keyboard_listener = keyboard.Listener(on_press=on_keyboard_press)
        monitor.mouse_listener = mouse.Listener(on_click=on_mouse_event, on_scroll=on_mouse_event)
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
