"""
CPU Scheduling Simulator - Premium Dark GUI (Single File)
Requirements: customtkinter (pip install customtkinter)
Optional: Pillow (for saving canvas export) - pip install pillow
"""

import customtkinter as ctk
from tkinter import ttk, messagebox, filedialog, simpledialog
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict
import random
import time
import csv
import sys

# Try winsound for Windows beep; otherwise no-op
try:
    import winsound
    def _beep(freq=700, dur=80):
        try:
            winsound.Beep(freq, dur)
        except Exception:
            pass
except Exception:
    def _beep(*a, **k):
        pass

# ---------------------------
# Data model
# ---------------------------
@dataclass
class Process:
    pid: str
    arrival: int
    burst: int
    priority: int = 0
    remaining: int = field(init=False)
    start_time: Optional[int] = None
    completion_time: Optional[int] = None
    waiting: int = 0
    turnaround: int = 0
    response: int = 0

    def __post_init__(self):
        self.remaining = self.burst

# ---------------------------
# Algorithms (returns rows, gantt)
# gantt: List[ (pid, start, end) ]
# rows: List[(PID, Arrival, Burst, Priority, Waiting, Turnaround, Response)]
# ---------------------------
ALGOS = [
    "FCFS",
    "SJF (Non-Preemptive)",
    "SJF (Preemptive)",
    "Round Robin",
    "Priority (Non-Preemptive)",
    "Priority (Preemptive)",
]

def clone_processes(data: List[dict]) -> List[Process]:
    return [Process(d['pid'], int(d['arrival']), int(d['burst']), int(d.get('priority', 0))) for d in data]

def merge_adjacent(gantt: List[Tuple[str,int,int]]):
    if not gantt: return []
    merged = [gantt[0]]
    for pid,s,e in gantt[1:]:
        lp, ls, le = merged[-1]
        if pid == lp and s == le:
            merged[-1] = (lp, ls, e)
        else:
            merged.append((pid,s,e))
    return merged

def results_and_gantt(procs: List[Process], gantt: List[Tuple[str,int,int]]):
    rows = []
    for p in procs:
        if p.completion_time is None: p.completion_time = 0
        p.turnaround = p.completion_time - p.arrival
        p.waiting = p.turnaround - p.burst
        if p.start_time is None:
            p.response = 0
        rows.append((p.pid, p.arrival, p.burst, p.priority, p.waiting, p.turnaround, p.response))
    rows.sort(key=lambda r: r[0])
    return rows, merge_adjacent(gantt)

def schedule_processes(data: List[dict], algo: str, quantum: int = 0):
    procs = clone_processes(data)
    if algo == "FCFS": return fcfs(procs)
    if algo == "SJF (Non-Preemptive)": return sjf_np(procs)
    if algo == "SJF (Preemptive)": return sjf_p(procs)
    if algo == "Round Robin":
        if quantum <= 0: raise ValueError("Quantum must be > 0")
        return rr(procs, quantum)
    if algo == "Priority (Non-Preemptive)": return priority_np(procs)
    if algo == "Priority (Preemptive)": return priority_p(procs)
    raise ValueError("Unknown algo")

def fcfs(procs: List[Process]):
    procs.sort(key=lambda p: (p.arrival, p.pid))
    time_ptr = 0
    gantt = []
    for p in procs:
        if time_ptr < p.arrival:
            gantt.append(("IDLE", time_ptr, p.arrival))
            time_ptr = p.arrival
        p.start_time = time_ptr
        p.response = p.start_time - p.arrival
        end = time_ptr + p.burst
        gantt.append((p.pid, time_ptr, end))
        time_ptr = end
        p.completion_time = time_ptr
        p.remaining = 0
    return results_and_gantt(procs, gantt)

def sjf_np(procs: List[Process]):
    procs.sort(key=lambda p: (p.arrival, p.burst, p.pid))
    time_ptr = 0
    i = 0
    n = len(procs)
    ready = []
    gantt = []
    while i < n or ready:
        while i < n and procs[i].arrival <= time_ptr:
            ready.append(procs[i]); i += 1
        if not ready:
            nxt = procs[i].arrival
            gantt.append(("IDLE", time_ptr, nxt))
            time_ptr = nxt
            continue
        ready.sort(key=lambda p: (p.burst, p.arrival, p.pid))
        p = ready.pop(0)
        p.start_time = time_ptr
        p.response = p.start_time - p.arrival
        end = time_ptr + p.burst
        gantt.append((p.pid, time_ptr, end))
        time_ptr = end
        p.completion_time = time_ptr
        p.remaining = 0
    return results_and_gantt(procs, gantt)

def sjf_p(procs: List[Process]):
    procs.sort(key=lambda p: (p.arrival, p.burst, p.pid))
    time_ptr = 0
    i = 0
    n = len(procs)
    ready = []
    gantt = []
    current = None
    while i < n or ready or current:
        while i < n and procs[i].arrival <= time_ptr:
            ready.append(procs[i]); i += 1
        if not current and not ready:
            if i < n:
                nxt = procs[i].arrival
                gantt.append(("IDLE", time_ptr, nxt))
                time_ptr = nxt
                continue
            else:
                break
        if current:
            ready.append(current)
        ready.sort(key=lambda p: (p.remaining, p.arrival, p.pid))
        current = ready.pop(0)
        if current.start_time is None:
            current.start_time = time_ptr
            current.response = current.start_time - current.arrival
        # run 1 unit
        seg_start = time_ptr
        time_ptr += 1
        current.remaining -= 1
        gantt.append((current.pid, seg_start, time_ptr))
        if current.remaining == 0:
            current.completion_time = time_ptr
            current = None
    return results_and_gantt(procs, gantt)

def rr(procs: List[Process], q: int):
    procs.sort(key=lambda p: (p.arrival, p.pid))
    time_ptr = 0
    i = 0
    n = len(procs)
    queue = []
    gantt = []
    while i < n or queue:
        if not queue and i < n and time_ptr < procs[i].arrival:
            nxt = procs[i].arrival
            gantt.append(("IDLE", time_ptr, nxt))
            time_ptr = nxt
        while i < n and procs[i].arrival <= time_ptr:
            queue.append(procs[i]); i += 1
        if not queue:
            continue
        p = queue.pop(0)
        if p.start_time is None:
            p.start_time = time_ptr
            p.response = p.start_time - p.arrival
        run = min(q, p.remaining)
        seg_start = time_ptr
        time_ptr += run
        p.remaining -= run
        gantt.append((p.pid, seg_start, time_ptr))
        while i < n and procs[i].arrival <= time_ptr:
            queue.append(procs[i]); i += 1
        if p.remaining > 0:
            queue.append(p)
        else:
            p.completion_time = time_ptr
    return results_and_gantt(procs, gantt)

def priority_np(procs: List[Process]):
    procs.sort(key=lambda p: (p.arrival, p.priority, p.pid))
    time_ptr = 0
    i = 0
    n = len(procs)
    ready = []
    gantt = []
    while i < n or ready:
        while i < n and procs[i].arrival <= time_ptr:
            ready.append(procs[i]); i += 1
        if not ready:
            if i < n:
                nxt = procs[i].arrival
                gantt.append(("IDLE", time_ptr, nxt))
                time_ptr = nxt
                continue
            else:
                break
        ready.sort(key=lambda p: (p.priority, p.arrival, p.pid))
        p = ready.pop(0)
        p.start_time = time_ptr
        p.response = p.start_time - p.arrival
        end = time_ptr + p.burst
        gantt.append((p.pid, time_ptr, end))
        time_ptr = end
        p.completion_time = time_ptr
        p.remaining = 0
    return results_and_gantt(procs, gantt)

def priority_p(procs: List[Process]):
    procs.sort(key=lambda p: (p.arrival, p.priority, p.pid))
    time_ptr = 0
    i = 0
    n = len(procs)
    ready = []
    gantt = []
    current = None
    while i < n or ready or current:
        while i < n and procs[i].arrival <= time_ptr:
            ready.append(procs[i]); i += 1
        if not current and not ready:
            if i < n:
                nxt = procs[i].arrival
                gantt.append(("IDLE", time_ptr, nxt))
                time_ptr = nxt
                continue
            else:
                break
        if current:
            ready.append(current)
        ready.sort(key=lambda p: (p.priority, p.arrival, p.pid))
        current = ready.pop(0)
        if current.start_time is None:
            current.start_time = time_ptr
            current.response = current.start_time - current.arrival
        seg_start = time_ptr
        time_ptr += 1
        current.remaining -= 1
        gantt.append((current.pid, seg_start, time_ptr))
        if current.remaining == 0:
            current.completion_time = time_ptr
            current = None
    return results_and_gantt(procs, gantt)

# ---------------------------
# GUI - Premium
# ---------------------------
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("dark-blue")

class PremiumScheduler(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("⚙️ CPU Scheduler — Premium")
        self.geometry("1280x820")
        self.minsize(1100,700)
        self.configure(fg_color="#11121a")

        # data
        self.processes: List[dict] = []
        self.gantt: List[Tuple[str,int,int]] = []
        self.pid_colors: Dict[str,str] = {}
        self.animation_index = 0
        self.animating = False
        self.paused = False
        self.current_segment_item = None
        self.animation_speed = 1.0  # multiplier, larger => faster
        self.play_after_id = None
        self.step_mode = False

        # palette (pleasant distinct colors, good contrast on dark bg)
        self.palette = [
            "#4DB6AC", "#81C784", "#4FC3F7", "#64B5F6", "#BA68C8",
            "#FF8A65", "#FFD54F", "#A1887F", "#90A4AE", "#F06292",
            "#E57373", "#7986CB"
        ]
        random.shuffle(self.palette)

        self._build_ui()
        self._seed_example()

    # ---------------- UI ----------------
    def _build_ui(self):
        # Header
        header = ctk.CTkFrame(self, height=64, fg_color="#0f1724")
        header.pack(side="top", fill="x")
        logo = ctk.CTkLabel(header, text="⚙️ Scheduler Pro", font=("Segoe UI",20,"bold"))
        logo.pack(side="left", padx=18)
        subtitle = ctk.CTkLabel(header, text="Dark • Premium • Animated Gantt", font=("Segoe UI",11))
        subtitle.pack(side="left", padx=6)

        # Main layout: left controls, right main
        container = ctk.CTkFrame(self, fg_color="#0f1220")
        container.pack(fill="both", expand=True, padx=12, pady=12)

        # Left controls
        left = ctk.CTkFrame(container, width=340, corner_radius=12, fg_color="#111226")
        left.pack(side="left", fill="y", padx=(0,12), pady=6)
        left.pack_propagate(False)

        # Process input card
        ctk.CTkLabel(left, text="Add Process", font=("Segoe UI",14,"bold")).pack(pady=(12,6))
        self.pid_entry = ctk.CTkEntry(left, placeholder_text="PID (e.g. P1)")
        self.arrival_entry = ctk.CTkEntry(left, placeholder_text="Arrival (int)")
        self.burst_entry = ctk.CTkEntry(left, placeholder_text="Burst (int)")
        self.priority_entry = ctk.CTkEntry(left, placeholder_text="Priority (optional)")
        for w in (self.pid_entry, self.arrival_entry, self.burst_entry, self.priority_entry):
            w.pack(fill="x", padx=14, pady=6)
        btn_frame = ctk.CTkFrame(left, fg_color="#0f1220")
        btn_frame.pack(fill="x", padx=12, pady=(6,12))
        ctk.CTkButton(btn_frame, text="Add", command=self._on_add, width=90).pack(side="left", padx=8)
        ctk.CTkButton(btn_frame, text="Auto 5", command=self._auto5, width=90).pack(side="left", padx=8)
        ctk.CTkButton(btn_frame, text="Clear", command=self._clear_all, width=90).pack(side="left", padx=8)

        # Algorithm selection
        ctk.CTkLabel(left, text="Algorithm", font=("Segoe UI",14,"bold")).pack(pady=(6,6))
        self.algo_var = ctk.StringVar(value=ALGOS[0])
        self.algo_menu = ctk.CTkOptionMenu(left, variable=self.algo_var, values=ALGOS, command=self._on_algo_change)
        self.algo_menu.pack(fill="x", padx=14, pady=(0,8))
        self.quantum_entry = ctk.CTkEntry(left, placeholder_text="Quantum (for RR)")
        # quantum initially hidden
        self.quantum_entry.pack_forget()

        # Controls (play, pause, step, speed)
        ctk.CTkLabel(left, text="Simulation", font=("Segoe UI",14,"bold")).pack(pady=(8,6))
        sim_frame = ctk.CTkFrame(left, fg_color="#0f1220")
        sim_frame.pack(fill="x", padx=12, pady=6)
        self.play_btn = ctk.CTkButton(sim_frame, text="▶ Play", command=self.play, width=80)
        self.play_btn.pack(side="left", padx=6)
        self.pause_btn = ctk.CTkButton(sim_frame, text="⏸ Pause", command=self.pause, width=80)
        self.pause_btn.pack(side="left", padx=6)
        self.step_btn = ctk.CTkButton(sim_frame, text="⏭ Step", command=self.step, width=80)
        self.step_btn.pack(side="left", padx=6)

        speed_frame = ctk.CTkFrame(left, fg_color="#0f1220")
        speed_frame.pack(fill="x", padx=12, pady=(10,12))
        ctk.CTkLabel(speed_frame, text="Speed").pack(anchor="w")
        self.speed_slider = ctk.CTkSlider(speed_frame, from_=0.2, to=4.0, number_of_steps=18, command=self._on_speed)
        self.speed_slider.set(1.0)
        self.speed_slider.pack(fill="x", pady=6)

        # File operations
        ctk.CTkLabel(left, text="Data", font=("Segoe UI",14,"bold")).pack(pady=(6,6))
        ctk.CTkButton(left, text="Load CSV", command=self.load_csv).pack(fill="x", padx=14, pady=6)
        ctk.CTkButton(left, text="Save CSV", command=self.save_csv).pack(fill="x", padx=14, pady=6)
        ctk.CTkButton(left, text="Export Log", command=self.export_log).pack(fill="x", padx=14, pady=6)

        # Right main area
        right = ctk.CTkFrame(container, fg_color="#0f1220")
        right.pack(side="left", fill="both", expand=True, pady=6)

        # Top: table and metrics
        top_row = ctk.CTkFrame(right, fg_color="#0f1220")
        top_row.pack(fill="x", pady=(0,8))

        # Table (process list)
        table_frame = ctk.CTkFrame(top_row, corner_radius=12, fg_color="#0f1116")
        table_frame.pack(side="left", fill="both", expand=True, padx=(0,10), pady=6)
        cols = ("PID","Arrival","Burst","Priority","Waiting","Turnaround","Response")
        self.tree = ttk.Treeview(table_frame, columns=cols, show="headings", selectmode="browse", height=8)
        for c in cols:
            self.tree.heading(c, text=c)
            self.tree.column(c, width=100, anchor="center")
        self.tree.pack(side="left", fill="both", expand=True, padx=(6,0), pady=6)
        t_scroll = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=t_scroll.set)
        t_scroll.pack(side="right", fill="y", padx=(0,6), pady=6)
        # context menu
        self.tree.bind("<Button-3>", self._on_right_click)

        # Metrics cards
        metrics_frame = ctk.CTkFrame(top_row, width=300, corner_radius=12, fg_color="#0f1116")
        metrics_frame.pack(side="left", fill="y", padx=(10,0), pady=6)
        metrics_frame.pack_propagate(False)
        self.metric_cards = {}
        for name in ["Avg WT", "Avg TAT", "Avg Resp", "CPU Util", "Throughput"]:
            frm = ctk.CTkFrame(metrics_frame, fg_color="#0f1220", height=56)
            frm.pack(fill="x", padx=12, pady=8)
            lbl_title = ctk.CTkLabel(frm, text=name, anchor="w", font=("Segoe UI",10))
            lbl_title.pack(anchor="w", padx=10, pady=(6,0))
            lbl_val = ctk.CTkLabel(frm, text="-", anchor="w", font=("Segoe UI",14,"bold"))
            lbl_val.pack(anchor="w", padx=10, pady=(0,8))
            self.metric_cards[name] = lbl_val

        # Middle: Gantt canvas
        gantt_frame = ctk.CTkFrame(right, corner_radius=12, fg_color="#0f1116")
        gantt_frame.pack(fill="both", expand=True, pady=4)
        # horizontal scrollbar
        self.canvas = ctk.CTkCanvas(gantt_frame, height=220, bg="#0c0d12", highlightthickness=0)
        self.h_scroll = ttk.Scrollbar(gantt_frame, orient="horizontal", command=self.canvas.xview)
        self.canvas.configure(xscrollcommand=self.h_scroll.set)
        self.canvas.pack(side="top", fill="both", expand=True, padx=8, pady=(8,0))
        self.h_scroll.pack(side="top", fill="x", padx=8, pady=(4,8))

        # bottom: logs
        logs_frame = ctk.CTkFrame(right, corner_radius=12, fg_color="#0f1116")
        logs_frame.pack(fill="x", pady=(6,0))
        self.log_box = ctk.CTkTextbox(logs_frame, height=120)
        self.log_box.pack(fill="both", expand=True, padx=8, pady=8)

    # ---------------- internal helpers ----------------
    def _seed_example(self):
        # put a nice initial sample
        sample = [
            {"pid":"P1","arrival":0,"burst":5,"priority":2},
            {"pid":"P2","arrival":2,"burst":3,"priority":1},
            {"pid":"P3","arrival":4,"burst":1,"priority":3}
        ]
        self.processes = sample.copy()
        self._refresh_table()

    def _pick_color(self, pid: str):
        if pid in self.pid_colors: return self.pid_colors[pid]
        # choose next color from palette (cycle)
        idx = len(self.pid_colors) % len(self.palette)
        color = self.palette[idx]
        self.pid_colors[pid] = color
        return color

    def _on_algo_change(self, *_):
        algo = self.algo_var.get()
        if "Round Robin" in algo:
            self.quantum_entry.pack(fill="x", padx=14, pady=(0,8))
        else:
            self.quantum_entry.pack_forget()

    # ---------------- Process CRUD ----------------
    def _on_add(self):
        pid = self.pid_entry.get().strip() or None
        if not pid:
            # auto PID
            pid = f"P{len(self.processes)+1}"
        if any(p['pid'] == pid for p in self.processes):
            messagebox.showerror("Duplicate PID", f"PID '{pid}' already exists.")
            return
        arrival = self._safe_int(self.arrival_entry.get().strip(), default=None)
        burst = self._safe_int(self.burst_entry.get().strip(), default=None)
        if arrival is None or burst is None:
            messagebox.showerror("Input Error", "Arrival and Burst must be integers.")
            return
        if burst <= 0:
            messagebox.showerror("Input Error", "Burst must be > 0.")
            return
        pr = self._safe_int(self.priority_entry.get().strip(), default=0)
        self.processes.append({"pid": pid, "arrival": arrival, "burst": burst, "priority": pr})
        self.pid_entry.delete(0, "end"); self.arrival_entry.delete(0, "end"); self.burst_entry.delete(0, "end"); self.priority_entry.delete(0, "end")
        self._refresh_table()
        self._log(f"Added: {pid} (arr={arrival}, burst={burst}, pr={pr})")

    def _safe_int(self, txt, default=None):
        if txt is None or txt == "": return default
        try:
            return int(txt)
        except Exception:
            return None

    def _auto5(self):
        self.processes.clear()
        for i in range(5):
            pid = f"P{i+1}"
            arrival = random.randint(0, 6)
            burst = random.randint(1, 10)
            pr = random.randint(0, 4)
            self.processes.append({"pid": pid, "arrival": arrival, "burst": burst, "priority": pr})
        self.pid_colors.clear()
        self._refresh_table()
        self._log("Auto-generated 5 processes.")

    def _clear_all(self):
        self.processes.clear()
        self.pid_colors.clear()
        self._refresh_table()
        self.canvas.delete("all")
        self.log_box.delete("1.0", "end")
        self._update_metrics([], [])
        self._log("Cleared all processes / canvas.")

    def _on_right_click(self, event):
        iid = self.tree.identify_row(event.y)
        if iid:
            menu = ctk.CTkToplevel(self)
            menu.geometry(f"220x120+{self.winfo_rootx()+event.x}+{self.winfo_rooty()+event.y}")
            menu.overrideredirect(True)
            item = self.tree.item(iid)['values']
            pid = item[0]
            def edit():
                menu.destroy()
                self._edit_process(pid)
            def delete():
                menu.destroy()
                self._delete_process(pid)
            ctk.CTkButton(menu, text="Edit", command=edit).pack(fill="x", padx=10, pady=6)
            ctk.CTkButton(menu, text="Delete", command=delete).pack(fill="x", padx=10, pady=6)
            ctk.CTkButton(menu, text="Close", command=menu.destroy).pack(fill="x", padx=10, pady=6)
        else:
            return

    def _edit_process(self, pid):
        p = next((x for x in self.processes if x['pid'] == pid), None)
        if not p:
            messagebox.showerror("Not found", pid)
            return
        new_arr = simpledialog.askinteger("Edit Arrival", f"Arrival for {pid}", initialvalue=p['arrival'])
        if new_arr is None: return
        new_burst = simpledialog.askinteger("Edit Burst", f"Burst for {pid}", initialvalue=p['burst'])
        if new_burst is None or new_burst <= 0:
            messagebox.showerror("Invalid", "Burst must be > 0")
            return
        new_pr = simpledialog.askinteger("Edit Priority", f"Priority for {pid}", initialvalue=p.get('priority', 0))
        if new_pr is None: return
        p['arrival'] = new_arr; p['burst'] = new_burst; p['priority'] = new_pr
        self._refresh_table()
        self._log(f"Edited {pid}")

    def _delete_process(self, pid):
        self.processes = [p for p in self.processes if p['pid'] != pid]
        if pid in self.pid_colors: del self.pid_colors[pid]
        self._refresh_table()
        self._log(f"Deleted {pid}")

    def _refresh_table(self, rows=None):
        # if rows provided (results), show results else raw processes
        for r in self.tree.get_children():
            self.tree.delete(r)
        if rows:
            for row in rows:
                self.tree.insert("", "end", values=row)
        else:
            for p in sorted(self.processes, key=lambda x: x['pid']):
                self.tree.insert("", "end", values=(p['pid'], p['arrival'], p['burst'], p.get('priority',0), "-", "-", "-"))

    # ---------------- Logging / metrics ----------------
    def _log(self, msg):
        ts = time.strftime("%H:%M:%S")
        self.log_box.insert("end", f"[{ts}] {msg}\n")
        self.log_box.see("end")
        # heartbeat sound on each log entry (no toggle)
        try:
            _beep(800, 50)
        except Exception:
            pass

    def _update_metrics(self, rows, gantt):
        if not rows:
            for k in self.metric_cards:
                self.metric_cards[k].configure(text="-")
            return
        n = len(rows)
        avg_wt = sum(r[4] for r in rows)/n
        avg_tat = sum(r[5] for r in rows)/n
        avg_resp = sum(r[6] for r in rows)/n
        total_time = max((e for _,_,e in gantt), default=0)
        total_burst = sum(p['burst'] for p in self.processes)
        cpu_util = (total_burst/total_time*100) if total_time>0 else 0.0
        throughput = (len(self.processes)/total_time) if total_time>0 else 0.0
        self.metric_cards["Avg WT"].configure(text=f"{avg_wt:.2f}")
        self.metric_cards["Avg TAT"].configure(text=f"{avg_tat:.2f}")
        self.metric_cards["Avg Resp"].configure(text=f"{avg_resp:.2f}")
        self.metric_cards["CPU Util"].configure(text=f"{cpu_util:.2f}%")
        self.metric_cards["Throughput"].configure(text=f"{throughput:.3f}")

    # ---------------- Running / Animation ----------------
    def _prepare_schedule(self):
        if not self.processes:
            messagebox.showerror("No processes", "Add processes before running.")
            return None
        algo = self.algo_var.get()
        q = 0
        if "Round Robin" in algo:
            qtxt = self.quantum_entry.get().strip()
            try:
                q = int(qtxt)
                if q <= 0:
                    raise ValueError()
            except Exception:
                messagebox.showerror("Quantum", "Enter valid positive integer quantum.")
                return None
        try:
            rows, gantt = schedule_processes(self.processes, algo, q)
        except Exception as e:
            messagebox.showerror("Schedule Error", str(e))
            return None
        # merge adjacent done inside scheduling; still ensure merged
        gantt = merge_adjacent(gantt)
        return rows, gantt

    def play(self):
        if self.animating and not self.paused:
            return  # already playing
        prepared = self._prepare_schedule()
        if prepared is None:
            return
        rows, gantt = prepared
        self._refresh_table(rows)
        self.gantt = gantt
        # canvas draw setup
        self._draw_gantt_base()
        self._update_metrics(rows, gantt)
        self.animation_index = 0
        self.animating = True
        self.paused = False
        self.step_mode = False
        self._log(f"Start animation [{self.algo_var.get()}]")
        # begin loop
        self._run_next_segment()

    def pause(self):
        self.paused = True
        self._log("Paused animation")
        if self.play_after_id:
            try:
                self.after_cancel(self.play_after_id)
            except Exception:
                pass
            self.play_after_id = None

    def step(self):
        # step-through single segment
        prepared = self._prepare_schedule()
        if prepared is None:
            return
        rows, gantt = prepared
        self._refresh_table(rows)
        self.gantt = gantt
        self._draw_gantt_base()
        self._update_metrics(rows, gantt)
        # allow stepping even when paused
        if not self.animating:
            self.animating = True
            self.animation_index = 0
        self.paused = True
        self.step_mode = True
        self._run_next_segment()

    def _on_speed(self, v):
        self.animation_speed = float(v)

    def _run_next_segment(self):
        if not self.animating:
            return
        if self.animation_index >= len(self.gantt):
            self._log("Animation complete")
            self.animating = False
            self.animation_index = 0
            return
        if self.paused and not self.step_mode:
            return
        pid, s, e = self.gantt[self.animation_index]
        # highlight table row
        self._highlight_pid_row(pid)
        seg_len = max(1, e - s)
        # compute animation duration (ms) scaled by speed slider; base 400ms per time unit
        base_ms_per_unit = 300  # base duration for 1 time unit
        duration = int(base_ms_per_unit * seg_len / max(0.2, self.animation_speed))
        # animate bar growth
        bar_id = self._animate_segment(pid, s, e, duration)
        # after animation finishes, increment index and continue
        def after_seg():
            # mark segment finished (solid)
            if bar_id is not None:
                self.canvas.itemconfig(bar_id, outline="#0b0b0b")
            self.animation_index += 1
            self.step_mode = False
            if not self.paused:
                self.play_after_id = self.after(60, self._run_next_segment)
        # schedule after duration + slight gap
        self.play_after_id = self.after(duration + 60, after_seg)

    def _highlight_pid_row(self, pid):
        # select the row with pid in the tree (first column)
        for iid in self.tree.get_children():
            vals = self.tree.item(iid)['values']
            if vals and vals[0] == pid:
                self.tree.selection_set(iid)
                self.tree.see(iid)
                # set style using tags not straightforward; use selection only
                return
        # if pid is IDLE, clear selection
        self.tree.selection_remove(self.tree.selection())

    def _draw_gantt_base(self):
        self.canvas.delete("all")
        if not self.gantt:
            return
        # compute time range
        tmin = min(s for _, s, _ in self.gantt)
        tmax = max(e for _, _, e in self.gantt)
        total = max(1, tmax - tmin)
        # visual width depends on total units; use px_per_unit
        px_per_unit = max(24, int(900 / max(1, total)))  # ensure readable
        width = px_per_unit * total + 120
        height = 200
        self.canvas.configure(scrollregion=(0,0,width,height))
        y = 20
        lane_h = 36
        # draw time grid
        for t in range(tmin, tmax+1):
            x = 60 + (t - tmin) * px_per_unit
            self.canvas.create_line(x, 12, x, height-12, fill="#1c1c28", width=1)
            if (t - tmin) % max(1, int(max(1,total/20))) == 0:
                self.canvas.create_text(x, 8, text=str(t), anchor="n", fill="#9aa0b4", font=("Segoe UI",9))
        # draw baseline (single lane)
        lane_y = y
        self.canvas.create_rectangle(40, lane_y-6, width-40, lane_y + lane_h + 6, fill="#0b0c10", outline="#111216")
        # prepare segment placeholders (initially zero-length)
        self.segment_items = []
        for idx, (pid, s, e) in enumerate(self.gantt):
            color = "#666666" if pid == "IDLE" else self._pick_color(pid)
            x1 = 60 + (s - tmin) * px_per_unit
            x2 = x1  # start collapsed
            item = self.canvas.create_rectangle(x1, lane_y, x2, lane_y + lane_h, fill=color, outline="", tags=("segment",))
            text = self.canvas.create_text(x1+6, lane_y + lane_h/2, text=pid, anchor="w", fill="#0b0b0b" if pid == "IDLE" else "white", font=("Segoe UI",10,"bold"))
            self.segment_items.append((item, text, s, e, color, px_per_unit, x1))
        # small legend
        lx = 12
        for pid, color in list(self.pid_colors.items())[:6]:
            self.canvas.create_rectangle(lx, height-24, lx+18, height-8, fill=color, outline="")
            self.canvas.create_text(lx+22, height-16, text=pid, anchor="w", fill="#9aa0b4", font=("Segoe UI",9))
            lx += 80

    def _animate_segment(self, pid, s, e, duration_ms):
        # find the corresponding segment item for current animation_index
        idx = self.animation_index
        if idx < 0 or idx >= len(self.segment_items): return None
        item, text, seg_s, seg_e, color, px_per_unit, x_start = self.segment_items[idx]
        # guard: recompute target x2
        seg_len_units = max(1, seg_e - seg_s)
        target_x = x_start + seg_len_units * px_per_unit
        # We will expand rectangle's x2 from x_start to target_x in N steps (duration_ms / step_ms)
        step_ms = 20
        steps = max(5, duration_ms // step_ms)
        dx = (target_x - x_start) / steps
        cur_step = 0
        def step_expand():
            nonlocal cur_step
            cur_step += 1
            new_x = x_start + dx * cur_step
            # update rectangle
            try:
                self.canvas.coords(item, x_start, 20, new_x, 20 + 36)
                # update text position to remain centered-ish
                self.canvas.coords(text, min(new_x-6, x_start+6 + (new_x-x_start)/2), 20 + 18)
            except Exception:
                pass
            if cur_step < steps:
                self.after(int(step_ms / max(0.2, self.animation_speed)), step_expand)
        # start expansion
        step_expand()
        return item

    # ---------------- File I/O ----------------
    def load_csv(self):
        path = filedialog.askopenfilename(filetypes=[("CSV","*.csv"),("All","*.*")])
        if not path: return
        try:
            with open(path, newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                self.processes = []
                for r in reader:
                    pid = r.get('pid') or f"P{len(self.processes)+1}"
                    arr = int(r.get('arrival', 0))
                    burst = int(r.get('burst', 1))
                    pr = int(r.get('priority', 0))
                    self.processes.append({"pid":pid,"arrival":arr,"burst":burst,"priority":pr})
            self.pid_colors.clear()
            self._refresh_table()
            self._log(f"Loaded {len(self.processes)} processes from CSV.")
        except Exception as e:
            messagebox.showerror("Load error", str(e))

    def save_csv(self):
        if not self.processes:
            messagebox.showinfo("No data", "No processes to save.")
            return
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV","*.csv")])
        if not path: return
        try:
            with open(path, "w", newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(["pid","arrival","burst","priority"])
                for p in self.processes:
                    writer.writerow([p['pid'], p['arrival'], p['burst'], p.get('priority',0)])
            self._log(f"Saved processes to {path}")
        except Exception as e:
            messagebox.showerror("Save error", str(e))

    def export_log(self):
        txt = self.log_box.get("1.0", "end").strip()
        if not txt:
            messagebox.showinfo("No logs", "Nothing in log.")
            return
        path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text","*.txt")])
        if not path: return
        try:
            with open(path, "w", encoding='utf-8') as f:
                f.write(txt)
            self._log(f"Log exported to {path}")
        except Exception as e:
            messagebox.showerror("Export error", str(e))

# ---------------------------
# Run application
# ---------------------------
if __name__ == "__main__":
    app = PremiumScheduler()
    app.mainloop()