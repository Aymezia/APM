import os
import time
import json
from tkinter import filedialog, messagebox


def build_session_summary(apm, avg, cps, dpm, total_actions, session_count, active_seconds, best_apm, low_apm):
    duration = time.strftime('%H:%M:%S', time.gmtime(active_seconds))
    return (
        f"APM {int(round(apm))} | Avg {avg:.1f} | Best {int(round(best_apm))} | Low {int(round(low_apm)) if low_apm is not None else '-'}\n"
        f"CPS {cps} | DPM {dpm} | Actions {total_actions} | Sessions {session_count} | Active {duration}"
    )


def export_history(history, root):
    if not history:
        messagebox.showinfo("Export CSV", "Aucune donnée d'historique disponible.")
        return
    path = filedialog.asksaveasfilename(
        defaultextension='.csv',
        filetypes=[('CSV files', '*.csv'), ('All files', '*.*')],
        title='Exporter l\'historique en CSV'
    )
    if not path:
        return
    try:
        with open(path, 'w', encoding='utf-8') as f:
            f.write('timestamp,apm,cps,dpm,avg\n')
            for row in history:
                f.write(f"{row['timestamp']},{row['apm']},{row['cps']},{row['dpm']},{row['avg']:.1f}\n")
        messagebox.showinfo("Export CSV", f"Historique exporté vers {path}")
    except Exception as exc:
        messagebox.showerror("Export CSV", f"Impossible d'exporter : {exc}")


def take_snapshot(monitor):
    try:
        os.makedirs(os.path.join(os.path.dirname(__file__), 'snapshots'), exist_ok=True)
        stamp = time.strftime('%Y%m%d_%H%M%S')
        path = os.path.join(os.path.dirname(__file__), 'snapshots', f'apm_snapshot_{stamp}.json')
        payload = {
            'timestamp': time.time(),
            'apm': int(round(monitor.compute_apm())),
            'avg': round(monitor.compute_average(), 2),
            'cps': monitor.compute_cps(),
            'dpm': monitor.compute_dpm(),
            'best': int(round(monitor.high_apm)),
            'worst': int(round(monitor.low_apm)) if monitor.low_apm is not None else None,
            'total_actions': monitor.total_actions,
        }
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(payload, f, indent=2)
        monitor.last_snapshot_path = path
        return path
    except Exception:
        return None
