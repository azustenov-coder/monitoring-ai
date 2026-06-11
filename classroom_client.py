"""
CLASSROOM CLIENT - O'quvchi kompyuteriga o'rnatiladi
Screenshot + Kamera yuboradi
"""

import socket
import threading
import time
import io
import struct
import sys
import os
import platform
import hashlib

try:
    from PIL import ImageGrab, Image
except ImportError:
    os.system(f"{sys.executable} -m pip install pillow")
    from PIL import ImageGrab, Image

try:
    import cv2
except ImportError:
    os.system(f"{sys.executable} -m pip install opencv-python")
    import cv2

# =============================================
# SOZLAMALAR - BU YERNI O'ZGARTIRING
# =============================================
SERVER_IP   = "127.0.0.1"   # <-- Admin kompyuteri IP
SERVER_PORT = 9999
SCREEN_INTERVAL  = 3    # Ekran screenshot (sekund)
CAMERA_INTERVAL  = 2    # Kamera (sekund)
COMPUTER_NAME    = socket.gethostname()
CAMERA_INDEX     = 0    # Odatda 0 (birinchi kamera)
# =============================================

running         = True
connected       = False
client_socket   = None
sock_lock       = threading.Lock()
locked          = False
lock_window     = None


# ---------- yordamchi ----------
SHARED_SECRET = b"MonitoringAI_Secure_Key_2026"
camera_capture = None

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


def send_data(sock, data):
    iv = os.urandom(8)
    key = hashlib.sha256(iv + SHARED_SECRET).digest()
    enc_data = rc4_crypt(data, key)
    packet = iv + enc_data
    length = struct.pack('>I', len(packet))
    with sock_lock:
        sock.sendall(length + packet)


def get_screenshot():
    try:
        img = ImageGrab.grab()
        img = img.resize((img.width // 2, img.height // 2), Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format='JPEG', quality=45)
        return buf.getvalue()
    except:
        return None


def get_camera_frame():
    global camera_capture
    try:
        if camera_capture is None:
            camera_capture = cv2.VideoCapture(CAMERA_INDEX)
        if not camera_capture.isOpened():
            camera_capture = None
            return None
        ret, frame = camera_capture.read()
        if not ret:
            return None
        # Kichiklashtirish
        h, w = frame.shape[:2]
        frame = cv2.resize(frame, (w // 2, h // 2))
        _, buf = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 50])
        return buf.tobytes()
    except:
        return None


# ---------- asosiy ulanish ----------
def connect_loop():
    global connected, client_socket, running, camera_capture

    while running:
        try:
            print(f"Server {SERVER_IP}:{SERVER_PORT} ga ulanmoqda...")
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10)
            sock.connect((SERVER_IP, SERVER_PORT))
            sock.settimeout(None)

            # Handshake
            challenge = sock.recv(16)
            if len(challenge) != 16:
                raise ConnectionError("Challenge qabul qilinmadi")
            response = hashlib.sha256(challenge + SHARED_SECRET).digest()
            sock.sendall(response)
            ok_status = sock.recv(4)
            if ok_status != b'OK__':
                raise ConnectionError("Autentifikatsiya rad etildi")

            client_socket = sock
            connected = True
            print(f"Ulandi! [{COMPUTER_NAME}]")

            # Nom yuborish
            name_bytes = COMPUTER_NAME.encode('utf-8')
            send_data(sock, b'NAME' + name_bytes)

            # Screen + Camera threadlarini boshlash
            ts = threading.Thread(target=screen_loop, daemon=True)
            tc = threading.Thread(target=camera_loop, daemon=True)
            tr = threading.Thread(target=recv_loop,   daemon=True)
            ts.start(); tc.start(); tr.start()
            ts.join()   # screen_loop tugaguncha kutish

        except ConnectionRefusedError:
            print(f"Server topilmadi. {SCREEN_INTERVAL*2}s da qayta...")
        except Exception as e:
            print(f"Xato: {e}")
        finally:
            connected = False
            if client_socket:
                try: client_socket.close()
                except: pass
            if camera_capture is not None:
                try:
                    camera_capture.release()
                except:
                    pass
                camera_capture = None
        time.sleep(SCREEN_INTERVAL * 2)


def screen_loop():
    global connected
    while running and connected:
        data = get_screenshot()
        if data:
            try:
                send_data(client_socket, b'SCRN' + data)
            except:
                connected = False
                return
        time.sleep(SCREEN_INTERVAL)


def camera_loop():
    global connected
    while running and connected:
        data = get_camera_frame()
        if data:
            try:
                send_data(client_socket, b'CAMA' + data)
            except:
                connected = False
                return
        time.sleep(CAMERA_INTERVAL)


def recv_loop():
    global connected
    while running and connected:
        try:
            raw = client_socket.recv(4)
            if not raw: break
            msg_len = struct.unpack('>I', raw)[0]
            
            packet = b''
            while len(packet) < msg_len:
                pkt = client_socket.recv(min(msg_len - len(packet), 65536))
                if not pkt: break
                packet += pkt
            if len(packet) < 8: continue
            
            iv = packet[:8]
            enc_payload = packet[8:]
            key = hashlib.sha256(iv + SHARED_SECRET).digest()
            data = rc4_crypt(enc_payload, key)
            
            if len(data) < 4: continue
            cmd  = data[:4].decode('utf-8', errors='ignore')
            body = data[4:]
            if   cmd == 'LOCK': lock_screen()
            elif cmd == 'ULCK': unlock_screen()
            elif cmd == 'MSGS': show_message(body.decode('utf-8', errors='ignore'))
        except:
            connected = False
            return


# ---------- lock / message ----------
def lock_screen():
    global locked, lock_window
    if locked: return
    locked = True
    import tkinter as tk
    def _run():
        global lock_window
        r = tk.Tk()
        lock_window = r
        r.title("BLOKLANGAN")
        r.attributes('-fullscreen', True)
        r.attributes('-topmost',    True)
        r.configure(bg='#1a1a2e')
        r.grab_set()
        f = tk.Frame(r, bg='#1a1a2e')
        f.place(relx=.5, rely=.5, anchor='center')
        tk.Label(f, text="🔒",       font=('Arial', 80),      bg='#1a1a2e', fg='#e94560').pack()
        tk.Label(f, text="KOMPYUTER BLOKLANGAN",
                 font=('Arial', 28, 'bold'), bg='#1a1a2e', fg='white').pack(pady=20)
        tk.Label(f, text="Admin ruxsat berguncha kuting",
                 font=('Arial', 16),         bg='#1a1a2e', fg='#888').pack()
        r.bind('<Key>', lambda e: 'break')
        r.protocol("WM_DELETE_WINDOW", lambda: None)
        r.mainloop()
    threading.Thread(target=_run, daemon=True).start()


def unlock_screen():
    global locked, lock_window
    locked = False
    if lock_window:
        try: lock_window.quit(); lock_window.destroy()
        except: pass
        lock_window = None


def show_message(text):
    import tkinter as tk
    from tkinter import messagebox
    def _run():
        r = tk.Tk(); r.withdraw()
        r.attributes('-topmost', True)
        messagebox.showinfo("Admindan xabar", text, parent=r)
        r.destroy()
    threading.Thread(target=_run, daemon=True).start()


def add_to_startup():
    if platform.system() == 'Windows':
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE)
            script_path = os.path.abspath(sys.argv[0])
            pythonw_path = sys.executable.replace("python.exe", "pythonw.exe")
            cmd = f'"{pythonw_path}" "{script_path}"'
            winreg.SetValueEx(key, "MonitoringAIClient", 0, winreg.REG_SZ, cmd)
            winreg.CloseKey(key)
            print("[+] Windows Startup-ga muvaffaqiyatli qo'shildi (Auto-run)")
        except Exception as e:
            print(f"[-] Startup-ga qo'shishda xatolik: {e}")


if __name__ == '__main__':
    print("="*50)
    print("MONITORING AI - CLIENT")
    print(f"Kompyuter : {COMPUTER_NAME}")
    print(f"Server    : {SERVER_IP}:{SERVER_PORT}")
    print("="*50)
    add_to_startup()
    try:
        connect_loop()
    except KeyboardInterrupt:
        running = False
        print("\nTo'xtatildi")
