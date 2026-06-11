# 🎓 MONITORING AI - Ko'rsatmalar

## Nima qiladi?
- Admin barcha o'quvchilarning ekranini **real vaqtda** ko'radi
- Ekranlarni **bloklash/ochish** mumkin
- O'quvchilarga **xabar yuborish** mumkin
- 2x bosib **to'liq ekranda ko'rish** mumkin

---

## 📁 Fayllar
```
classroom_server.py         ← ADMINga (sizga)
classroom_client.py         ← O'QUVCHILARga
install_and_run_client.bat  ← O'rnatish skripti (Windows)
```

---

## 🚀 O'RNATISH

### 1-QADAM: Python o'rnatish (barcha kompyuterlarga)
- https://python.org ga kiring
- Eng so'nggi versiyani yuklab oling
- **MUHIM**: O'rnatishda **"Add Python to PATH"** ni belgilang!

### 2-QADAM: ADMIN kompyuteri sozlash
1. `classroom_server.py` ni kompyuteringizga ko'chiring
2. IP manzilingizni bilib oling:
   - Windows: `cmd` oching → `ipconfig` → IPv4 Address
   - Masalan: `192.168.1.100`
3. `python classroom_server.py` buyrug'i bilan ishga tushiring
4. Dastur sizning IP manzilingizni ko'rsatadi

### 3-QADAM: O'QUVCHI kompyuterlarini sozlash
1. `classroom_client.py` ni oching (Notepad bilan)
2. 20-qatordagi `SERVER_IP` ni o'zgartiring:
   ```python
   SERVER_IP = "192.168.1.172"   # ← Admin IP manzili
   ```
3. Faylni saqlang
4. `install_and_run_client.bat` ni ishga tushiring

---

## 🎮 FOYDALANISH

### Admin panelida:
| Tugma | Vazifasi |
|-------|----------|
| 🔴 HAMMASINI BLOKLASH | Barcha ekranlarni bloklaydi |
| 🟢 HAMMASINI OCHISH | Barcha blokni olib tashlaydi |
| 📢 XABAR YUBORISH | Hammaga xabar yuboradi |
| 2x klik | O'sha ekranni to'liq ko'rish |
| O'ng klik | Bitta o'quvchini boshqarish |

---

## 🔧 MUAMMOLAR

**"Server topilmadi" deydi:**
- Admin kompyuterida server ishlaydimi? Tekshiring
- IP manzil to'g'rimi? `classroom_client.py` da tekshiring
- Firewall/antivirus 9999 portni bloklamasligi kerak

**Firewall uchun:**
- Windows Defender → "Allow an app" → Python qo'shing
- Yoki: `netsh advfirewall firewall add rule name="Classroom" dir=in action=allow protocol=TCP localport=9999`

**O'quvchi ekrani ko'rinmaydi:**
- `classroom_client.py` ishlaydimi? Task Manager da tekshiring
- Bir xil Wi-Fi/tarmoqdami?

---

## 🌐 Tarmoq talablari
- Barcha kompyuterlar bir xil **local network** (Wi-Fi yoki LAN) da bo'lishi kerak
- Port: **9999** (TCP)
- Internet shart emas - faqat lokal tarmoq yetarli

---

## 💡 Maslahatlar
- O'quvchi kompyuterida `pythonw classroom_client.py` (console ko'rinmaydi)
- Windows autostart uchun: `shell:startup` papkasiga `.bat` fayl qo'ying
- Screenshot sifatini `classroom_client.py` da `quality=50` → `quality=30` qilib kamaytirish mumkin (tezroq ishlaydi)
