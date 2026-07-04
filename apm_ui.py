import tkinter as tk
from tkinter import ttk


def build_main_window(monitor):
    pad = 8
    frame = tk.Frame(monitor.root, bg=monitor.bg)
    frame.pack(fill="both", expand=True, padx=pad, pady=pad)

    current_label = tk.Label(
        frame,
        text="APM: 0",
        fg=monitor.fg,
        bg=monitor.bg,
        font=("Consolas", monitor.font_size, "bold"),
        anchor="w",
    )
    current_label.pack(fill="x")

    stats_label = tk.Label(
        frame,
        text="Avg: 0.0 | Best: 0 | Worst: 0",
        fg=monitor.fg,
        bg=monitor.bg,
        font=("Consolas", 11),
        anchor="w",
    )
    stats_label.pack(fill="x", pady=(4, 0))

    summary_label = tk.Label(
        frame,
        text="CPS: 0 | DPM: 0 | Sessions: 0 | Active: 00:00:00",
        fg=monitor.fg,
        bg=monitor.bg,
        font=("Consolas", 9),
        anchor="w",
    )
    summary_label.pack(fill="x", pady=(2, 0))

    extra_label = tk.Label(
        frame,
        text="CPS: 0    Actions: 0    DPM: 0",
        fg=monitor.fg,
        bg=monitor.bg,
        font=("Consolas", 9),
        anchor="w",
    )
    extra_label.pack(fill="x", pady=(2, 0))

    session_summary_label = tk.Label(
        frame,
        text="Session summary",
        fg=monitor.fg,
        bg=monitor.bg,
        font=("Consolas", 8),
        anchor="w",
        justify="left",
    )
    session_summary_label.pack(fill="x", pady=(2, 0))

    remote_label = tk.Label(
        frame,
        text="Remote: off",
        fg=monitor.fg,
        bg=monitor.bg,
        font=("Consolas", 9),
        anchor="w",
    )
    remote_label.pack(fill="x", pady=(2, 0))

    segment_label = tk.Label(
        frame,
        text="Best: 0    Zone: normal",
        fg=monitor.fg,
        bg=monitor.bg,
        font=("Consolas", 9),
        anchor="w",
    )
    segment_label.pack(fill="x", pady=(2, 0))

    graph_canvas = tk.Canvas(frame, height=56, bg=monitor.bg, highlightthickness=0)
    graph_canvas.pack(fill="x", pady=(4, 4))

    timer_label = tk.Label(
        frame,
        text="Temps: 00:00:00",
        fg=monitor.fg,
        bg=monitor.bg,
        font=("Consolas", 10),
        anchor="w",
    )
    timer_label.pack(fill="x", pady=(2, 10))

    controls = tk.Frame(frame, bg=monitor.bg)
    controls.pack(fill="x")

    overlay_var = tk.BooleanVar(value=monitor.overlay)
    monitor.overlay_var = overlay_var

    overlay_btn = tk.Button(
        controls,
        text="Toggle Overlay",
        command=monitor.toggle_overlay_button,
        bg="#334155",
        fg=monitor.fg,
        relief="flat",
        bd=0,
        activebackground="#1e2936",
        padx=10,
        pady=6,
    )
    overlay_btn.grid(row=0, column=0, padx=(0, 8), pady=(0, 8))

    pause_btn = tk.Button(
        controls,
        text="Pause",
        command=monitor.toggle_pause,
        bg="#334155",
        fg=monitor.fg,
        relief="flat",
        bd=0,
        activebackground="#1e2936",
        padx=10,
        pady=6,
    )
    pause_btn.grid(row=0, column=1, padx=(0, 8), pady=(0, 8))

    focus_btn = tk.Button(
        controls,
        text="Focus",
        command=monitor.toggle_focus_mode,
        bg="#334155",
        fg=monitor.fg,
        relief="flat",
        bd=0,
        activebackground="#1e2936",
        padx=10,
        pady=6,
    )
    focus_btn.grid(row=0, column=2, padx=(0, 8), pady=(0, 8))

    copy_btn = tk.Button(
        controls,
        text="Copy",
        command=monitor.copy_stats,
        bg="#334155",
        fg=monitor.fg,
        relief="flat",
        bd=0,
        activebackground="#1e2936",
        padx=10,
        pady=6,
    )
    copy_btn.grid(row=0, column=3, padx=(0, 8), pady=(0, 8))

    snapshot_btn = tk.Button(
        controls,
        text="Snap",
        command=monitor.take_snapshot,
        bg="#334155",
        fg=monitor.fg,
        relief="flat",
        bd=0,
        activebackground="#1e2936",
        padx=10,
        pady=6,
    )
    snapshot_btn.grid(row=0, column=4, padx=(0, 8), pady=(0, 8))

    settings_btn = tk.Button(
        controls,
        text="Paramètres",
        command=monitor.open_settings,
        bg="#334155",
        fg=monitor.fg,
        relief="flat",
        bd=0,
        activebackground="#1e2936",
        padx=10,
        pady=6,
    )
    settings_btn.grid(row=0, column=5, padx=(0, 8), pady=(0, 8))

    reset_btn = tk.Button(
        controls,
        text="Reset APM",
        command=monitor.reset_stats,
        bg="#334155",
        fg=monitor.fg,
        relief="flat",
        bd=0,
        activebackground="#1e2936",
        padx=10,
        pady=6,
    )
    reset_btn.grid(row=1, column=0, padx=(0, 8), pady=(0, 8))

    font_scale = tk.Scale(
        controls,
        from_=16,
        to=48,
        orient="horizontal",
        bg=monitor.bg,
        fg=monitor.fg,
        troughcolor="#555555",
        highlightthickness=0,
        command=monitor.change_font,
    )
    font_scale.set(monitor.font_size)
    font_scale.grid(row=2, column=0, columnspan=6, sticky="we", pady=(8, 0))

    help_label = tk.Label(
        frame,
        text="Esc: quitter — F10: toggle overlay — Ctrl+Shift+S: paramètres",
        fg=monitor.fg,
        bg=monitor.bg,
        font=("Consolas", 8),
        anchor="w",
    )
    help_label.pack(fill="x", pady=(8, 0))

    mini_toggle_btn = tk.Button(
        frame,
        text="",
        command=monitor.toggle_mini_mode,
        bg=monitor.bg,
        fg=monitor.fg,
        bd=0,
        highlightthickness=0,
        activebackground=monitor.bg,
        activeforeground=monitor.fg,
        width=1,
        height=1,
    )
    mini_toggle_btn.place_forget()

    monitor.widgets = {
        'frame': frame,
        'current_label': current_label,
        'stats_label': stats_label,
        'summary_label': summary_label,
        'extra_label': extra_label,
        'session_summary_label': session_summary_label,
        'remote_label': remote_label,
        'segment_label': segment_label,
        'graph_canvas': graph_canvas,
        'timer_label': timer_label,
        'controls': controls,
        'overlay_var': overlay_var,
        'overlay_btn': overlay_btn,
        'settings_btn': settings_btn,
        'reset_btn': reset_btn,
        'font_scale': font_scale,
        'help_label': help_label,
        'mini_toggle_btn': mini_toggle_btn,
        'pause_btn': pause_btn,
        'focus_btn': focus_btn,
        'copy_btn': copy_btn,
        'snapshot_btn': snapshot_btn,
    }
    monitor.overlay_btn = overlay_btn
    monitor.settings_btn = settings_btn
    monitor.reset_btn = reset_btn
    monitor.font_scale = font_scale
    monitor.help_label = help_label
    monitor.mini_toggle_btn = mini_toggle_btn
    monitor.pause_btn = pause_btn
    monitor.focus_btn = focus_btn
    monitor.session_summary_label = session_summary_label
    monitor.copy_btn = copy_btn
    monitor.snapshot_btn = snapshot_btn

    return monitor.widgets
