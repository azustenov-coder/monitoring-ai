"""
CLASSROOM SERVER - Admin kompyuteri
Tab 1: Ekranlar  |  Tab 2: Kameralar
"""

import socket, threading, struct, io, time
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from datetime import datetime
import hashlib
import os

try:
    from PIL import Image, ImageTk
except ImportError:
    import sys
    os.system(f"{sys.executable} -m pip install pillow")
    from PIL import Image, ImageTk

# ── Sozlamalar ──────────────────────────────
HOST       = '0.0.0.0'
PORT       = 9999
MAX_CLIENTS = 30
# ────────────────────────────────────────────

SHARED_SECRET = b"MonitoringAI_Secure_Key_2026"

def rc4_crypt(data, key):
    S = list(range(256))
    j = 0
    out = bytearray()
    for i in range(256):
        j = (j + S[i] + key[i % len(key)]) % 256
        S[i], S[j] = S[j], S[i]
    i = j = 0
    for char in data:
        i = (i + 1) % 256
        j = (j + S[i]) % 256
        S[i], S[j] = S[j], S[i]
        out.append(char ^ S[(S[i] + S[j]) % 256])
    return bytes(out)

clients      = {}
clients_lock = threading.Lock()
client_counter = 0


# ══════════════ SERVER BACKEND ══════════════

def recv_exactly(sock, n):
    data = b''
    while len(data) < n:
        pkt = sock.recv(n - len(data))
        if not pkt:
            raise ConnectionError("Uzildi")
        data += pkt
    return data


def handle_client(conn, addr, cid):
    global clients
    name = f"Kompyuter-{cid}"
    print(f"[+] {addr}  id={cid}")

    try:
        # Handshake
        challenge = os.urandom(16)
        conn.sendall(challenge)
        response = recv_exactly(conn, 32)
        expected = hashlib.sha256(challenge + SHARED_SECRET).digest()
        if response != expected:
            conn.sendall(b'FAIL')
            raise ConnectionError("Autentifikatsiya muvaffaqiyatsiz")
        conn.sendall(b'OK__')

        with clients_lock:
            clients[cid] = {
                'socket':    conn,
                'name':      name,
                'address':   addr,
                'screen':    None,
                'camera':    None,
                'last_seen': datetime.now(),
                'locked':    False,
                'screen_updated': False,
                'camera_updated': False,
            }

        while True:
            raw_len = recv_exactly(conn, 4)
            msg_len = struct.unpack('>I', raw_len)[0]
            if msg_len > 15 * 1024 * 1024:
                raise ValueError("Juda katta paket")
            
            packet = recv_exactly(conn, msg_len)
            if len(packet) < 8:
                continue
            
            iv = packet[:8]
            enc_payload = packet[8:]
            key = hashlib.sha256(iv + SHARED_SECRET).digest()
            data = rc4_crypt(enc_payload, key)

            if len(data) < 4:
                continue
            mtype   = data[:4].decode('utf-8', errors='ignore')
            payload = data[4:]

            with clients_lock:
                if cid not in clients:
                    break
                c = clients[cid]
                if mtype == 'NAME':
                    c['name']      = payload.decode('utf-8', errors='ignore').strip()
                elif mtype == 'SCRN':
                    try:
                        img = Image.open(io.BytesIO(payload))
                        c['screen']    = img.copy()
                        c['screen_updated'] = True
                        c['last_seen'] = datetime.now()
                    except: pass
                elif mtype == 'CAMA':
                    try:
                        img = Image.open(io.BytesIO(payload))
                        c['camera']    = img.copy()
                        c['camera_updated'] = True
                    except: pass

    except Exception as e:
        print(f"[-] id={cid}: {e}")
    finally:
        with clients_lock:
            if cid in clients:
                del clients[cid]
        try: conn.close()
        except: pass
        print(f"[-] id={cid} chiqdi")


def send_command(cid, cmd_type, payload=b''):
    with clients_lock:
        if cid not in clients:
            return False
        sock = clients[cid]['socket']
    try:
        data   = cmd_type.encode('utf-8') + payload
        iv = os.urandom(8)
        key = hashlib.sha256(iv + SHARED_SECRET).digest()
        enc_data = rc4_crypt(data, key)
        packet = iv + enc_data
        length = struct.pack('>I', len(packet))
        sock.sendall(length + packet)
        return True
    except:
        return False


def start_server():
    global client_counter
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((HOST, PORT))
    srv.listen(MAX_CLIENTS)
    print(f"[*] Server {PORT} portda tayyor")
    while True:
        try:
            conn, addr = srv.accept()
            client_counter += 1
            cid = client_counter
            threading.Thread(target=handle_client,
                             args=(conn, addr, cid), daemon=True).start()
        except Exception as e:
            print(f"Accept xato: {e}")


# ══════════════ GUI ══════════════════════════

THUMB_SCREEN = (300, 190)
THUMB_CAMERA = (280, 210)

BTN = dict(font=('Consolas', 10, 'bold'), relief='flat',
           padx=14, pady=7, cursor='hand2', bd=0)


class App:
    def __init__(self, root):
        self.root = root
        self.root.title("🎓 Monitoring AI — Admin Paneli")
        self.root.configure(bg='#0a0a1a')
        self.root.state('zoomed')

        self.fullscreen_win = None
        self._build()
        self._tick()

    # ── Layout ──────────────────────────────
    def _build(self):
        # Top bar
        top = tk.Frame(self.root, bg='#12122a', height=56)
        top.pack(fill='x')
        top.pack_propagate(False)
        tk.Label(top, text="🎓  MONITORING AI",
                 font=('Consolas', 17, 'bold'),
                 bg='#12122a', fg='#00d4ff').pack(side='left', padx=20)
        self.lbl_count = tk.Label(top, text="Ulangan: 0",
                 font=('Consolas', 12), bg='#12122a', fg='#ffcc00')
        self.lbl_count.pack(side='left', padx=20)
        self.lbl_ip = tk.Label(top, text="",
                 font=('Consolas', 11), bg='#12122a', fg='#888')
        self.lbl_ip.pack(side='right', padx=20)
        self._show_ip()

        # Global tugmalar
        bf = tk.Frame(self.root, bg='#0a0a1a', pady=6)
        bf.pack(fill='x', padx=8)
        tk.Button(bf, text="🔴  HAMMASINI BLOKLASH",
                  bg='#c0392b', fg='white',
                  command=self.lock_all,   **BTN).pack(side='left', padx=4)
        tk.Button(bf, text="🟢  HAMMASINI OCHISH",
                  bg='#00875a', fg='white',
                  command=self.unlock_all, **BTN).pack(side='left', padx=4)
        tk.Button(bf, text="📢  XABAR YUBORISH",
                  bg='#b8860b', fg='white',
                  command=self.msg_all,    **BTN).pack(side='left', padx=4)

        tk.Label(bf, text="2× klik → to'liq  |  O'ng klik → menyu",
                 font=('Consolas', 9), bg='#0a0a1a', fg='#444466').pack(side='right', padx=10)

        tk.Frame(self.root, bg='#222244', height=1).pack(fill='x')

        # Notebook (2 tab)
        style = ttk.Style()
        style.theme_use('default')
        style.configure('TNotebook',            background='#0a0a1a', borderwidth=0)
        style.configure('TNotebook.Tab',
                        background='#1a1a3e', foreground='#aaaacc',
                        font=('Consolas', 11, 'bold'),
                        padding=[20, 8])
        style.map('TNotebook.Tab',
                  background=[('selected', '#2a2a6e')],
                  foreground=[('selected', '#00d4ff')])

        self.nb = ttk.Notebook(self.root)
        self.nb.pack(fill='both', expand=True, padx=4, pady=4)

        self.tab_screen = tk.Frame(self.nb, bg='#0a0a1a')
        self.tab_camera = tk.Frame(self.nb, bg='#0a0a1a')
        self.nb.add(self.tab_screen, text='🖥️  EKRANLAR')
        self.nb.add(self.tab_camera, text='📷  KAMERALAR')

        self.scroll_screen = self._make_scroll_canvas(self.tab_screen)
        self.scroll_camera = self._make_scroll_canvas(self.tab_camera)

        self.grid_screen = self.scroll_screen['grid']
        self.grid_camera = self.scroll_camera['grid']

        self.cards_screen = {}
        self.cards_camera = {}

    def _make_scroll_canvas(self, parent):
        frame = tk.Frame(parent, bg='#0a0a1a')
        frame.pack(fill='both', expand=True)
        canvas = tk.Canvas(frame, bg='#0a0a1a', highlightthickness=0)
        sb     = ttk.Scrollbar(frame, orient='vertical', command=canvas.yview)
        grid   = tk.Frame(canvas, bg='#0a0a1a')
        canvas.configure(yscrollcommand=sb.set)
        canvas.pack(side='left', fill='both', expand=True)
        sb.pack(side='right', fill='y')
        win_id = canvas.create_window((0,0), window=grid, anchor='nw')
        grid.bind('<Configure>',
                  lambda e, c=canvas: c.configure(scrollregion=c.bbox('all')))
        canvas.bind('<Configure>',
                    lambda e, c=canvas, w=win_id: c.itemconfig(w, width=e.width))
        canvas.bind_all('<MouseWheel>',
                        lambda e, c=canvas: c.yview_scroll(int(-1*(e.delta/120)), 'units'))
        return {'canvas': canvas, 'grid': grid}

    def _show_ip(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]; s.close()
            self.lbl_ip.config(text=f"Sizning IP: {ip}  |  Port: {PORT}")
        except:
            pass

    # ── Refresh loop ────────────────────────
    def _tick(self):
        self._refresh()
        self.root.after(1000, self._tick)

    def _refresh(self):
        with clients_lock:
            cur = set(clients.keys())

        sc = set(self.cards_screen.keys())
        cc = set(self.cards_camera.keys())

        for cid in cur - sc: self._add_card(cid, 'screen')
        for cid in cur - cc: self._add_card(cid, 'camera')
        for cid in sc - cur: self._del_card(cid, 'screen')
        for cid in cc - cur: self._del_card(cid, 'camera')
        for cid in cur:
            self._upd_card(cid, 'screen')
            self._upd_card(cid, 'camera')

        self.lbl_count.config(text=f"Ulangan: {len(cur)} ta")

    # ── Card helpers ────────────────────────
    def _cards(self, kind):
        return self.cards_screen if kind == 'screen' else self.cards_camera

    def _grid(self, kind):
        return self.grid_screen if kind == 'screen' else self.grid_camera

    def _thumb(self, kind):
        return THUMB_SCREEN if kind == 'screen' else THUMB_CAMERA

    def _cols(self, kind):
        canvas = (self.scroll_screen if kind == 'screen'
                  else self.scroll_camera)['canvas']
        w = canvas.winfo_width()
        cw = self._thumb(kind)[0] + 24
        return max(1, min(6, w // cw))

    def _reposition(self, kind):
        cards = self._cards(kind)
        grid  = self._grid(kind)
        cols  = self._cols(kind)
        for i, (cid, card) in enumerate(sorted(cards.items())):
            r, c = divmod(i, cols)
            card['frame'].grid(row=r, column=c, padx=8, pady=8, sticky='nw')

    def _add_card(self, cid, kind):
        cards = self._cards(kind)
        grid  = self._grid(kind)
        tw, th = self._thumb(kind)

        frame = tk.Frame(grid, bg='#161630', cursor='hand2')

        # Header
        hdr = tk.Frame(frame, bg='#24245a', height=26)
        hdr.pack(fill='x'); hdr.pack_propagate(False)
        icon = '🖥️' if kind == 'screen' else '📷'
        with clients_lock:
            name = clients[cid]['name'] if cid in clients else f"ID-{cid}"
        nlbl = tk.Label(hdr, text=f"{icon} {name}",
                        font=('Consolas', 9, 'bold'),
                        bg='#24245a', fg='#00d4ff', anchor='w', padx=6)
        nlbl.pack(side='left', fill='both', expand=True)
        dot = tk.Label(hdr, text='●', font=('Arial', 9),
                       bg='#24245a', fg='#00ff88', padx=5)
        dot.pack(side='right')

        # Image
        img_lbl = tk.Label(frame, bg='#0d0d20', width=tw, height=th)
        img_lbl.pack(padx=2, pady=2)

        # Footer buttons
        ft = tk.Frame(frame, bg='#161630')
        ft.pack(fill='x', padx=3, pady=3)
        bkw = dict(font=('Consolas', 8), relief='flat',
                   padx=5, pady=2, cursor='hand2', bd=0)
        lbtn = tk.Button(ft, text='🔴 BLOKLASH', bg='#6b1515', fg='white',
                         command=lambda c=cid: self.lock_one(c), **bkw)
        lbtn.pack(side='left', padx=2)
        tk.Button(ft, text='💬', bg='#3a3a00', fg='#ffcc00',
                  command=lambda c=cid: self.msg_one(c), **bkw).pack(side='left', padx=2)
        tk.Button(ft, text='🔍', bg='#003a3a', fg='#00ffff',
                  command=lambda c=cid, k=kind: self.open_full(c, k), **bkw).pack(side='right', padx=2)

        img_lbl.bind('<Double-Button-1>',
                     lambda e, c=cid, k=kind: self.open_full(c, k))
        img_lbl.bind('<Button-3>',
                     lambda e, c=cid: self.ctx_menu(e, c))

        cards[cid] = {'frame': frame, 'img_lbl': img_lbl,
                      'nlbl': nlbl, 'dot': dot, 'lbtn': lbtn, 'photo': None}
        self._reposition(kind)

    def _del_card(self, cid, kind):
        cards = self._cards(kind)
        if cid in cards:
            cards[cid]['frame'].destroy()
            del cards[cid]
            self._reposition(kind)

    def _upd_card(self, cid, kind):
        cards = self._cards(kind)
        if cid not in cards: return
        card = cards[cid]

        with clients_lock:
            if cid not in clients: return
            d       = clients[cid]
            name    = d['name']
            locked  = d['locked']
            ls      = d['last_seen']
            img     = d['screen'] if kind == 'screen' else d['camera']
            updated = d['screen_updated'] if kind == 'screen' else d['camera_updated']
            
            # Reset flags
            if kind == 'screen':
                d['screen_updated'] = False
            else:
                d['camera_updated'] = False

        icon = '🖥️' if kind == 'screen' else '📷'
        card['nlbl'].config(text=f"{icon} {name}")

        diff = (datetime.now() - ls).seconds
        color = '#00ff88' if diff < 5 else '#ffcc00' if diff < 15 else '#ff4444'
        card['dot'].config(fg=color)

        if locked:
            card['lbtn'].config(text='🟢 OCHISH',   bg='#155a15',
                                command=lambda c=cid: self.unlock_one(c))
        else:
            card['lbtn'].config(text='🔴 BLOKLASH', bg='#6b1515',
                                command=lambda c=cid: self.lock_one(c))

        if img:
            # Only resize and update image on screen if there is a new frame or if first load
            if updated or card['photo'] is None:
                try:
                    th = img.copy()
                    th.thumbnail(self._thumb(kind), Image.BILINEAR)
                    photo = ImageTk.PhotoImage(th)
                    card['img_lbl'].config(image=photo, text='')
                    card['photo'] = photo
                except: pass
        else:
            label = "⏳ Screenshot kutilmoqda..." if kind=='screen' else "📷 Kamera kutilmoqda..."
            card['img_lbl'].config(text=label, fg='#444466',
                                   font=('Consolas', 9))

    # ── Full screen viewer ──────────────────
    def open_full(self, cid, kind='screen'):
        if self.fullscreen_win:
            try: self.fullscreen_win.destroy()
            except: pass

        with clients_lock:
            if cid not in clients: return
            name = clients[cid]['name']

        win = tk.Toplevel(self.root)
        icon = '🖥️' if kind == 'screen' else '📷'
        win.title(f"{icon}  {name} — To'liq ko'rinish")
        win.configure(bg='#080818')
        win.state('zoomed')
        self.fullscreen_win = win

        tk.Label(win, text=f"{icon}  {name}",
                 font=('Consolas', 14, 'bold'),
                 bg='#12122a', fg='#00d4ff', pady=6).pack(fill='x')

        img_lbl = tk.Label(win, bg='#080818')
        img_lbl.pack(expand=True, fill='both')

        def _update():
            if not win.winfo_exists(): return
            with clients_lock:
                if cid not in clients:
                    win.destroy(); return
                img = clients[cid]['screen'] if kind=='screen' \
                      else clients[cid]['camera']
            if img:
                try:
                    w = win.winfo_width() - 20
                    h = win.winfo_height() - 90
                    if w > 0 and h > 0:
                        ri = img.copy(); ri.thumbnail((w,h), Image.LANCZOS)
                        ph = ImageTk.PhotoImage(ri)
                        img_lbl.config(image=ph); img_lbl.photo = ph
                except: pass
            win.after(800, _update)

        win.after(300, _update)

        # Footer
        fb = tk.Frame(win, bg='#12122a', pady=5)
        fb.pack(fill='x', side='bottom')
        bkw = dict(font=('Consolas', 11, 'bold'), relief='flat',
                   padx=18, pady=7, cursor='hand2', bd=0)
        tk.Button(fb, text='🔴 BLOKLASH', bg='#c0392b', fg='white',
                  command=lambda: self.lock_one(cid),   **bkw).pack(side='left', padx=8)
        tk.Button(fb, text='🟢 OCHISH',   bg='#00875a', fg='white',
                  command=lambda: self.unlock_one(cid), **bkw).pack(side='left', padx=4)
        tk.Button(fb, text='💬 XABAR',    bg='#b8860b', fg='white',
                  command=lambda: self.msg_one(cid),    **bkw).pack(side='left', padx=4)

        # Tab switcher
        other = 'camera' if kind == 'screen' else 'screen'
        other_lbl = '📷 Kamerani ko\'r' if kind == 'screen' else '🖥️ Ekranni ko\'r'
        tk.Button(fb, text=other_lbl, bg='#1a3a5a', fg='#00d4ff',
                  command=lambda: [win.destroy(), self.open_full(cid, other)],
                  **bkw).pack(side='left', padx=4)

        tk.Button(fb, text='✖ YOPISH',   bg='#2a2a4a', fg='white',
                  command=win.destroy,    **bkw).pack(side='right', padx=10)

    # ── Context menu ────────────────────────
    def ctx_menu(self, event, cid):
        m = tk.Menu(self.root, tearoff=0, bg='#1a1a3e', fg='white',
                    activebackground='#2a2a6e', font=('Consolas', 10))
        with clients_lock:
            name   = clients[cid]['name']   if cid in clients else '?'
            locked = clients[cid]['locked'] if cid in clients else False
        m.add_command(label=f"💻  {name}", state='disabled')
        m.add_separator()
        m.add_command(label="🖥️  Ekranni ko'r",  command=lambda: self.open_full(cid,'screen'))
        m.add_command(label="📷  Kamerani ko'r", command=lambda: self.open_full(cid,'camera'))
        m.add_separator()
        if locked:
            m.add_command(label="🟢  Ochish",   command=lambda: self.unlock_one(cid))
        else:
            m.add_command(label="🔴  Bloklash", command=lambda: self.lock_one(cid))
        m.add_command(label="💬  Xabar",         command=lambda: self.msg_one(cid))
        try: m.tk_popup(event.x_root, event.y_root)
        finally: m.grab_release()

    # ── Commands ────────────────────────────
    def lock_one(self, cid):
        send_command(cid, 'LOCK')
        with clients_lock:
            if cid in clients: clients[cid]['locked'] = True

    def unlock_one(self, cid):
        send_command(cid, 'ULCK')
        with clients_lock:
            if cid in clients: clients[cid]['locked'] = False

    def lock_all(self):
        if messagebox.askyesno("Tasdiqlash",
                               "Barcha ekranlarni bloklaysizmi?", icon='warning'):
            with clients_lock: ids = list(clients.keys())
            for cid in ids: self.lock_one(cid)

    def unlock_all(self):
        with clients_lock: ids = list(clients.keys())
        for cid in ids: self.unlock_one(cid)

    def msg_one(self, cid):
        with clients_lock:
            name = clients[cid]['name'] if cid in clients else '?'
        msg = simpledialog.askstring("Xabar", f"{name} ga xabar:", parent=self.root)
        if msg: send_command(cid, 'MSGS', msg.encode('utf-8'))

    def msg_all(self):
        msg = simpledialog.askstring("Xabar", "Barcha o'quvchilarga:", parent=self.root)
        if msg:
            with clients_lock: ids = list(clients.keys())
            for cid in ids: send_command(cid, 'MSGS', msg.encode('utf-8'))


# ══════════════ MAIN ════════════════════════
if __name__ == '__main__':
    print("="*60)
    print("  MONITORING AI SERVER  |  Ekran + Kamera")
    print(f"  Port: {PORT}")
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]; s.close()
        print(f"\n  ✅ Sizning IP: {ip}")
        print(f"  classroom_client.py da  SERVER_IP = \"{ip}\"  qiling\n")
    except:
        pass
    print("="*60)

    threading.Thread(target=start_server, daemon=True).start()

    root = tk.Tk()
    App(root)
    try:
        root.mainloop()
    except KeyboardInterrupt:
        print("To'xtatildi")
