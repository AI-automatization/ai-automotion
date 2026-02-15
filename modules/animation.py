"""
JARVIS — HUD Animatsiya, Sozlamalar, Tarixi oynalari
"""
import math, os, threading
import tkinter as tk
from tkinter import Canvas, ttk, messagebox

from modules.core import State, state_manager


# ══════════════════════════════════════════════════════════
#  HUD ANIMATSIYA
# ══════════════════════════════════════════════════════════
class JarvisAnimation:
    W, H   = 240, 310
    BG     = "#050810"
    PANEL  = "#0a1628"
    BORDER = "#0d2444"

    STATE_CFG = {
        "idle":       {"color": "#00aaff", "label": "STANDBY",      "dim": 0.35},
        "background": {"color": "#004466", "label": "FONDA",        "dim": 0.20},
        "listening":  {"color": "#00ffee", "label": "TINGLAYAPMAN", "dim": 1.0},
        "processing": {"color": "#ffaa00", "label": "O'YLAMOQDA",   "dim": 1.0},
        "speaking":   {"color": "#00ff88", "label": "GAPIRMOQDA",   "dim": 1.0},
    }

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("JARVIS")
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", 0.96)
        self.root.configure(bg=self.BG)

        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        self.root.geometry(f"{self.W}x{self.H}+{sw-self.W-18}+{sh-self.H-55}")

        self.cv = Canvas(self.root, width=self.W, height=self.H,
                         bg=self.BG, highlightthickness=0)
        self.cv.pack(fill="both", expand=True)

        self._drag_x = self._drag_y = 0
        self.cv.bind("<ButtonPress-1>", self._drag_start)
        self.cv.bind("<B1-Motion>",     self._drag_move)
        self.cv.bind("<Button-3>",      self._show_menu)

        self._cur_color = self.STATE_CFG["background"]["color"]
        self._particles = []
        self._frame     = 0
        self._running   = True
        self._stats     = {}
        self._stats_tick = 0
        self._state_str  = "background"

        self._menu = tk.Menu(self.root, tearoff=0,
                             bg="#0a1628", fg="#00aaff",
                             activebackground="#00aaff",
                             activeforeground="#000")
        self._menu.add_command(label="⚙️  Sozlamalar",
                               command=lambda: open_settings_window(self.root))
        self._menu.add_command(label="📋 Buyruqlar tarixi",
                               command=lambda: open_history_window(self.root))
        self._menu.add_separator()
        self._menu.add_command(label="❌ Jarvisni yopish", command=self._quit)

        self._spawn_particles()

        # StateManager bilan bog'lash
        state_manager.on_change(self._on_state_change)

        self._animate()

    def _on_state_change(self, new_state: State):
        self._state_str = new_state.value

    def _quit(self):
        self._running = False
        self.root.destroy()
        os._exit(0)

    def _drag_start(self, e): self._drag_x = e.x; self._drag_y = e.y
    def _drag_move(self, e):
        x = self.root.winfo_x() + e.x - self._drag_x
        y = self.root.winfo_y() + e.y - self._drag_y
        self.root.geometry(f"+{x}+{y}")

    def _show_menu(self, e):
        try: self._menu.tk_popup(e.x_root, e.y_root)
        finally: self._menu.grab_release()

    def _spawn_particles(self):
        import random
        cx, cy = self.W//2, 110
        self._particles = [{
            "angle": random.uniform(0, 2*math.pi),
            "speed": random.uniform(0.3, 1.1),
            "dist":  random.uniform(28, 72),
            "size":  random.uniform(1.5, 3.5),
            "phase": random.uniform(0, 2*math.pi),
            "cx": cx, "cy": cy,
        } for _ in range(18)]

    def _lerp_color(self, c1, c2, t):
        t = max(0.0, min(1.0, t))
        def ch(c): return int(c[1:3],16), int(c[3:5],16), int(c[5:7],16)
        r1,g1,b1 = ch(c1); r2,g2,b2 = ch(c2)
        return f"#{int(r1+(r2-r1)*t):02x}{int(g1+(g2-g1)*t):02x}{int(b1+(b2-b1)*t):02x}"

    def _dim(self, color, factor):
        r = min(255, int(int(color[1:3],16)*factor))
        g = min(255, int(int(color[3:5],16)*factor))
        b = min(255, int(int(color[5:7],16)*factor))
        return f"#{r:02x}{g:02x}{b:02x}"

    def _animate(self):
        if not self._running: return
        cv  = self.cv
        W, H = self.W, self.H
        cv.delete("all")

        state  = self._state_str
        cfg    = self.STATE_CFG.get(state, self.STATE_CFG["idle"])
        color, dim_f, label = cfg["color"], cfg["dim"], cfg["label"]
        t = self._frame / 30.0

        self._cur_color = self._lerp_color(self._cur_color, color, 0.08)
        c = self._cur_color; pad = 8

        cv.create_rectangle(pad, pad, W-pad, H-pad,
                            fill=self.PANEL, outline=self.BORDER, width=1)
        cv.create_rectangle(pad, pad, W-pad, pad+28,
                            fill="#07111f", outline="", width=0)
        cv.create_text(W//2, pad+14, text="J · A · R · V · I · S",
                       font=("Courier", 9, "bold"), fill=self._dim(c, 0.7))
        cv.create_line(pad+4, pad+29, W-pad-4, pad+29,
                       fill=self._dim(c, 0.25), width=1)

        cx, cy_orb = W//2, 110

        for gs, ga in zip([52, 42, 34], [0.06, 0.10, 0.16]):
            cv.create_oval(cx-gs, cy_orb-gs, cx+gs, cy_orb+gs,
                           fill=self._dim(c, ga*(1.5 if state not in ("idle","background") else 0.5)),
                           outline="")

        if state in ("idle", "background"):
            breath = 0.5 + 0.5*math.sin(t*1.2)
            r_b = 22 + 4*breath
            cv.create_oval(cx-r_b, cy_orb-r_b, cx+r_b, cy_orb+r_b,
                           fill=self._dim(c, 0.15),
                           outline=self._dim(c, 0.4 * dim_f), width=1)
            rd = 7 + 2*breath
            cv.create_oval(cx-rd, cy_orb-rd, cx+rd, cy_orb+rd,
                           fill=self._dim(c, 0.5*dim_f), outline="")
            lc = self._dim(c, 0.35*dim_f)
            cv.create_line(cx-14, cy_orb, cx+14, cy_orb, fill=lc, width=1)
            cv.create_line(cx, cy_orb-14, cx, cy_orb+14, fill=lc, width=1)

        elif state == "listening":
            for i in range(4):
                phase = (t*1.6 - i*0.45) % 1.0
                r_s = 16 + phase*46
                cv.create_oval(cx-r_s, cy_orb-r_s, cx+r_s, cy_orb+r_s,
                               fill="", outline=self._dim(c, (1.0-phase)*0.8),
                               width=max(1, int(2*(1-phase))))
            mw, mh = 10, 15
            cv.create_rectangle(cx-mw//2, cy_orb-mh//2,
                                cx+mw//2, cy_orb+mh//2,
                                fill=c, outline=self._dim(c,0.5), width=1)
            cv.create_arc(cx-mw//2-3, cy_orb-mh//2,
                          cx+mw//2+3, cy_orb+mh//2+6,
                          start=0, extent=-180,
                          outline=c, fill="", style="arc", width=2)
            cv.create_line(cx, cy_orb+mh//2+5, cx, cy_orb+mh//2+10, fill=c, width=2)
            cv.create_line(cx-6, cy_orb+mh//2+10, cx+6, cy_orb+mh//2+10, fill=c, width=2)

        elif state == "processing":
            for ring_i, (orb_r, spd, ph) in enumerate([(36,2.0,0),(26,-3.2,0.5)]):
                ang = t*spd + ph
                rx, ry = orb_r, orb_r*0.38
                cv.create_oval(cx-rx, cy_orb-ry, cx+rx, cy_orb+ry,
                               outline=self._dim(c, 0.18), fill="", width=1)
                dx = cx + rx*math.cos(ang)
                dy = cy_orb + ry*math.sin(ang)
                dr = 5 if ring_i==0 else 4
                cv.create_oval(dx-dr, dy-dr, dx+dr, dy+dr, fill=c, outline="")
                for tr in range(6):
                    ta  = ang - tr*0.18
                    tdx = cx + rx*math.cos(ta)
                    tdy = cy_orb + ry*math.sin(ta)
                    tdr = dr*(1-tr/7)
                    cv.create_oval(tdx-tdr, tdy-tdr, tdx+tdr, tdy+tdr,
                                   fill=self._dim(c, 0.5*(1-tr/6)), outline="")
            r_star = 10 + 2*math.sin(t*5)
            cv.create_oval(cx-r_star, cy_orb-r_star, cx+r_star, cy_orb+r_star,
                           fill=self._dim(c, 0.9), outline="")

        elif state == "speaking":
            n_bars=11; bar_w=8; gap=4
            total_w = n_bars*(bar_w+gap)-gap
            sx = cx - total_w//2
            max_h=44; min_h=5
            for i in range(n_bars):
                h = min_h + (max_h-min_h)*abs(math.sin(t*4.5 + i*0.55))
                bx = sx + i*(bar_w+gap)
                cv.create_rectangle(bx-2, cy_orb+int(h+4)//2,
                                    bx+bar_w+2, cy_orb-int(h+4)//2,
                                    fill=self._dim(c,0.2), outline="")
                cv.create_rectangle(bx, cy_orb+h//2, bx+bar_w, cy_orb-h//2,
                                    fill=c, outline="")
                cv.create_rectangle(bx, cy_orb-int(h)//2,
                                    bx+bar_w, cy_orb-int(h)//2+2,
                                    fill="white", outline="")

        if state not in ("idle", "background"):
            for p in self._particles:
                p["angle"] += p["speed"]*0.02
                pulse = 0.7 + 0.3*math.sin(t*2 + p["phase"])
                px = p["cx"] + p["dist"]*math.cos(p["angle"])*pulse
                py = p["cy"] + p["dist"]*math.sin(p["angle"])*pulse*0.6
                ps = p["size"]*pulse*dim_f
                cv.create_oval(px-ps, py-ps, px+ps, py+ps,
                               fill=self._dim(c, 0.55*dim_f), outline="")

        # Tizim statistikasi
        self._stats_tick += 1
        if self._stats_tick >= 60:
            self._stats_tick = 0
            try:
                from modules.file_manager import get_system_stats
                self._stats = get_system_stats()
            except Exception: pass

        stats_y = cy_orb + 70
        cv.create_line(pad+4, stats_y-4, W-pad-4, stats_y-4,
                       fill=self._dim(c, 0.20), width=1)

        if self._stats:
            bar_bg = "#0d2444"
            def draw_bar(lbl, val, yp, bc):
                cv.create_text(pad+12, yp, text=lbl,
                               font=("Courier", 7), fill=self._dim(c, 0.6), anchor="w")
                bx1, bx2 = pad+42, W-pad-12
                cv.create_rectangle(bx1, yp-3, bx2, yp+3, fill=bar_bg, outline="")
                filled = int((bx2-bx1) * min(100, val) / 100)
                if filled > 0:
                    cv.create_rectangle(bx1, yp-3, bx1+filled, yp+3, fill=bc, outline="")
                cv.create_text(bx2+4, yp, text=f"{val}%",
                               font=("Courier", 6), fill=self._dim(c, 0.55), anchor="w")
            cpu_c = "#ff4444" if self._stats.get("cpu",0)>80 else c
            draw_bar("CPU", self._stats.get("cpu",0),  stats_y+8,  cpu_c)
            ram_c = "#ff8800" if self._stats.get("ram",0)>85 else c
            draw_bar("RAM", self._stats.get("ram",0),  stats_y+20, ram_c)
            bat = self._stats.get("battery")
            if bat is not None:
                plug = self._stats.get("plugged", False)
                bc   = c if plug or bat>20 else "#ff2222"
                cv.create_text(pad+12, stats_y+32,
                               text=f"{'⚡' if plug else '🔋'} BAT  {bat}%",
                               font=("Courier", 7), fill=bc, anchor="w")

        y_bot = H-pad-28
        cv.create_line(pad+4, y_bot, W-pad-4, y_bot,
                       fill=self._dim(c, 0.20), width=1)
        blink = abs(math.sin(t*3.0))
        cv.create_oval(pad+10, y_bot+7, pad+16, y_bot+13,
                       fill=self._dim(c, blink*dim_f), outline="")
        cv.create_text(W//2+4, y_bot+10, text=label,
                       font=("Courier", 8, "bold"),
                       fill=self._dim(c, 0.85*dim_f))

        glow_a = 0.18 + 0.08*math.sin(t*2)
        cv.create_rectangle(pad, pad, W-pad, H-pad,
                            fill="", outline=self._dim(c, glow_a), width=2)
        cv.create_rectangle(pad+1, pad+1, W-pad-1, H-pad-1,
                            fill="", outline=self._dim(c, glow_a*0.5), width=1)

        self._frame += 1
        self.root.after(33, self._animate)

    def set_state(self, state_str: str):
        self._state_str = state_str

    def stop(self):
        self._running = False
        try: self.root.destroy()
        except Exception: pass

    def run(self):
        self.root.mainloop()


def start_animation():
    anim = JarvisAnimation()
    anim.run()


# ══════════════════════════════════════════════════════════
#  SOZLAMALAR OYNASI
# ══════════════════════════════════════════════════════════
def open_settings_window(parent=None):
    import os
    from modules.memory_manager import get_all_memory
    from modules.memory_manager import add_task, get_tasks, format_tasks_text

    win = tk.Toplevel(parent) if parent else tk.Tk()
    win.title("JARVIS — Sozlamalar")
    win.geometry("500x520")
    win.configure(bg="#0a1628")
    win.resizable(False, False)

    style = ttk.Style(win)
    style.theme_use("clam")
    style.configure("TNotebook",      background="#0a1628", borderwidth=0)
    style.configure("TNotebook.Tab",  background="#0d2444", foreground="#00aaff",
                                      padding=[10,4])
    style.configure("TFrame",         background="#0a1628")
    style.configure("TLabel",         background="#0a1628", foreground="#aabbcc",
                                      font=("Courier",9))
    style.configure("TEntry",         fieldbackground="#07111f", foreground="#ffffff",
                                      insertcolor="#00aaff")
    style.configure("TButton",        background="#0d2444", foreground="#00aaff",
                                      font=("Courier",9))

    nb = ttk.Notebook(win)
    nb.pack(fill="both", expand=True, padx=10, pady=10)

    # ── API tab ──────────────────────────────────────────
    tab_api = ttk.Frame(nb); nb.add(tab_api, text="🔑 API Kalitlar")

    fields = [("Claude API Key:", "CLAUDE_API_KEY"),
              ("Weather API Key:", "WEATHER_API_KEY")]
    entries = {}
    for i, (lbl, key) in enumerate(fields):
        ttk.Label(tab_api, text=lbl).grid(row=i, column=0, sticky="w", padx=12, pady=8)
        e = ttk.Entry(tab_api, width=35, show="*")
        e.grid(row=i, column=1, padx=8, pady=8)
        e.insert(0, os.environ.get(key, ""))
        entries[key] = e

    def save_api():
        base     = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        env_path = os.path.join(base, ".env")
        lines = []
        for key, entry in entries.items():
            val = entry.get().strip()
            if val: lines.append(f"{key}={val}")
        with open(env_path, "w") as f:
            f.write("\n".join(lines) + "\n")
        messagebox.showinfo("Saqlandi", ".env faylga saqlandi.\nJarvisni qayta ishga tushiring.", parent=win)

    ttk.Button(tab_api, text="💾 Saqlash", command=save_api).grid(
        row=len(fields), column=1, sticky="e", padx=8, pady=12)

    # ── Xotira tab ───────────────────────────────────────
    tab_mem = ttk.Frame(nb); nb.add(tab_mem, text="🧠 Xotira")
    mem_text = tk.Text(tab_mem, bg="#07111f", fg="#aabbcc",
                       font=("Courier",9), width=55, height=12)
    mem_text.pack(fill="both", expand=True, padx=12, pady=8)

    def load_mem():
        mem_text.config(state="normal"); mem_text.delete("1.0","end")
        data = get_all_memory()
        mem_text.insert("end", "\n".join(f"{k}: {v}" for k,v in data.items()) if data else "Xotira bo'sh")
        mem_text.config(state="disabled")

    load_mem()
    ttk.Button(tab_mem, text="🔄 Yangilash", command=load_mem).pack(pady=4)

    # ── Vazifalar tab ────────────────────────────────────
    tab_tasks = ttk.Frame(nb); nb.add(tab_tasks, text="📌 Vazifalar")
    task_text = tk.Text(tab_tasks, bg="#07111f", fg="#aabbcc",
                        font=("Courier",9), width=55, height=10)
    task_text.pack(fill="both", expand=True, padx=12, pady=8)

    def load_tasks():
        task_text.config(state="normal"); task_text.delete("1.0","end")
        task_text.insert("end", format_tasks_text(get_tasks(only_pending=False)))
        task_text.config(state="disabled")

    load_tasks()
    fr = tk.Frame(tab_tasks, bg="#0a1628"); fr.pack(fill="x", padx=12, pady=4)
    inp = ttk.Entry(fr, width=40); inp.pack(side="left", padx=4)

    def add_gui():
        txt = inp.get().strip()
        if txt: add_task(txt); inp.delete(0,"end"); load_tasks()

    ttk.Button(fr, text="➕ Qo'sh", command=add_gui).pack(side="left", padx=4)

    if not parent: win.mainloop()


# ══════════════════════════════════════════════════════════
#  TARIXI OYNASI
# ══════════════════════════════════════════════════════════
def open_history_window(parent=None):
    from modules.history import get_recent

    win = tk.Toplevel(parent) if parent else tk.Tk()
    win.title("JARVIS — Buyruqlar tarixi")
    win.geometry("600x400")
    win.configure(bg="#0a1628")

    scroll = tk.Scrollbar(win)
    scroll.pack(side="right", fill="y")

    text = tk.Text(win, bg="#07111f", fg="#aabbcc",
                   font=("Courier",9), wrap="word",
                   yscrollcommand=scroll.set)
    text.pack(fill="both", expand=True, padx=10, pady=10)
    scroll.config(command=text.yview)

    rows = get_recent(50)
    if rows:
        for ts, cmd, resp in rows:
            text.insert("end", f"[{ts}] 👤 {cmd}\n")
            text.insert("end", f"       🤖 {resp[:80]}\n\n")
    else:
        text.insert("end", "Hali buyruqlar tarixi yo'q\n")
    text.config(state="disabled")

    if not parent: win.mainloop()
