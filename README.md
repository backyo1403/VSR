# VNA Sky Race — hướng dẫn dựng và chạy sự kiện

Game quiz đua máy bay 3 màn hình cho sự kiện ~50 người, mỗi người một điện thoại.

```
VNA_Race/
├── public/index.html        ← app (deploy cái này)
├── public/vendor/           ← asset offline, sinh ra bởi scripts/vendor-assets.mjs
├── database.rules.json      ← phân quyền admin/player
├── firebase.json            ← cấu hình hosting + database
├── scripts/vendor-assets.mjs
├── test/rules.test.js       ← 29 test luật chơi
└── vna-sky-race (1).html    ← bản localStorage cũ, giữ làm dự phòng
```

---

## Luật chơi

**Bản đồ:** 12 chặng, `START → CDG → AMS → HAN★ → MUC → MOW → SPC★ → LHR → MXP → CPH → SGN★ → FRA → FINISH★`

**Ngân hàng câu hỏi:** 30 câu, rút ngẫu nhiên theo chặng

| Chặng | Rút từ |
|---|---|
| 1 – 4 | câu 1 – 10 |
| 5 – 8 | câu 11 – 20 |
| 9 – 12 | câu 21 – 30 |

**Turbo Boost** — nút của người chơi, mở khoá riêng cho từng người **khi máy bay của họ tới MUC**. Mỗi người một lần cả ván. Đúng → **+2 chặng**, sai → **−1 chặng**. Không dùng được khi turbulence hoặc khi đang là Power Question. Bật Turbo mà không bấm Nộp thì không bị phạt và không mất lượt.

**Power Question** — nút của admin, **một lần duy nhất cả ván**, bấm trước khi mở câu hỏi. Câu hỏi rút từ 21–30, màn LED hiện ⚡ POWER QUESTION. Người **trả lời đúng nhanh nhất** được **+2 chặng**, người đúng khác +1, người sai đứng nguyên. Không bật được trên chặng turbulence. Huỷ trước khi mở câu thì được trả lại lượt.

**Turbulence** — tự động ở **chặng 6 và chặng 10**. Màn LED chuyển theme mưa sấm chớp, badge đổi từ 🌈 Clear Skies sang 🌪 Turbulence. Trả lời đúng **đứng nguyên**, **không đúng thì lùi 1 chặng** (kể cả người không trả lời). Turbo bị khoá.

**Thắng:** ai tới FINISH trước. Nhiều người cùng tới trong một lượt thì xếp theo *số câu đúng → tổng thời gian trả lời*.

Chạy test luật chơi:

```bash
node test/rules.test.js public/index.html
```

---

## Dựng lần đầu

### 1. Tạo project Firebase

Vào [console.firebase.google.com](https://console.firebase.google.com) → **Add project** → đặt tên `vna-sky-race`.

- **Realtime Database** → Create Database → chọn vùng **asia-southeast1 (Singapore)** → Start in **locked mode**.
- **Authentication** → Get started → bật **Anonymous** và **Email/Password**.
- **Authentication → Users → Add user**: email `admin@vna-sky-race.local`, đặt mật khẩu mạnh. Đây là tài khoản admin duy nhất — mật khẩu không nằm trong code.
- **Project settings → Your apps → Web (`</>`)** → copy khối `firebaseConfig`.

> Với 50 người chơi, hãy **nâng lên gói Blaze** và đặt budget alert $1. Gói Spark có trần 100 kết nối đồng thời; kết nối treo sau mỗi lần F5 khiến 50 người thật có thể chạm trần, và khi chạm thì người vào sau bị chặn im lặng.

### 2. Điền config

Mở `public/index.html`, tìm `FIREBASE_CONFIG` (gần đầu file) và thay các chỗ `PASTE_..._HERE` bằng giá trị vừa copy.

Chưa điền thì app vẫn chạy được ở **chế độ offline** (một máy duy nhất) — đó chính là phương án dự phòng khi hội trường mất mạng.

### 3. Đóng gói asset offline

```bash
node scripts/vendor-assets.mjs
```

Tải font, confetti và Firebase SDK về `public/vendor/` rồi trỏ lại đường dẫn. Sau bước này app không còn phụ thuộc CDN nào; kết nối mạng duy nhất còn lại là WebSocket tới database.

### 4. Deploy

```bash
npm install -g firebase-tools
```

```bash
firebase login && firebase init --project vna-sky-race && firebase deploy
```

Khi `firebase init` hỏi, chọn **Hosting** và **Realtime Database**, và **giữ nguyên** `public/`, `firebase.json`, `database.rules.json` đã có sẵn (trả lời **No** khi nó hỏi ghi đè).

### 5. Ba đường link

| Vai | Link |
|---|---|
| Người chơi | `https://<project>.web.app/#player` ← **in QR khổ lớn, dán nhiều chỗ** |
| Màn LED | `https://<project>.web.app/#presenter` |
| Điều phối | `https://<project>.web.app/#admin` → nhập mật khẩu tài khoản admin |

Chơi nhiều lượt thì thêm room code: `?room=SKY02#player` (mặc định `SKY01`).

---

## Phân quyền

Quyền do **database cưỡng chế**, không phải UI che đi. Gõ `#admin` vẫn mở được giao diện nhưng mọi nút bấm sẽ bị từ chối nếu chưa đăng nhập.

| Nhánh dữ liệu | Ai ghi được |
|---|---|
| `admin/` (trạng thái ván đấu) | chỉ tài khoản admin |
| `progress/{uid}` (vị trí, điểm) | chỉ tài khoản admin |
| `profiles/{uid}` (tên, máy bay) | chỉ chính người đó |
| `answers/{chặng}/{uid}` | chỉ chính người đó, **ghi một lần** |

Đáng chú ý trong `database.rules.json`:

- `!data.child('submitted').val()` — đổi đáp án thoải mái trước khi Nộp, nộp rồi thì khoá cứng.
- `gameState == 'question'` và `now < deadline` — **giờ máy chủ Firebase quyết định hết giờ**. Admin quên bấm Close hay trình duyệt admin treo thì đáp án muộn vẫn bị từ chối.
- `answers` chỉ admin đọc — người chơi không xem được đáp án của nhau.

---

## Van an toàn khi chạy sự kiện

| Tính năng | Dùng khi |
|---|---|
| **↩️ Undo last reveal** | Đáp án sai trong ngân hàng câu hỏi, câu bị tranh cãi, mở nhầm chặng |
| **−1 / +1** trong Manage Players | Điện thoại hết pin giữa câu, mất sóng đúng lúc, khiếu nại tại chỗ |
| Reveal **idempotent** | Bấm nhầm nhiều lần không cộng chặng hai lần |
| **Reset** phải gõ chữ `RESET` | Chống bấm nhầm nút xoá sạch người chơi khi đang chơi |
| Badge góc phải màn hình | 🟢 LIVE = đang đồng bộ cloud · 🟠 OFFLINE = chỉ máy này |
| Tự rơi về offline | Không kết nối được trong 8 giây thì chuyển chế độ, chương trình không chết |

**State nằm ở database, không nằm ở laptop admin.** Laptop admin sập thì mở laptop dự phòng, đăng nhập, chơi tiếp đúng chặng đang dừng.

---

## Checklist ngày sự kiện

| Mốc | Việc |
|---|---|
| T‑7 | Dựng xong, deploy, tự chạy thử đủ 12 chặng |
| T‑2 | **Diễn tập với 8–10 điện thoại thật** — việc giá trị nhất trong danh sách |
| T‑1 | Khoá code, không sửa gì nữa. In QR + bảng sự cố. Laptop dự phòng đăng nhập sẵn |
| T‑0 | Đến sớm 45 phút, mở 3 màn hình, cho 2 máy join thử, chơi 1 câu rồi Reset |

**Mạng:** người chơi dùng **4G**, tránh WiFi hội trường. Laptop admin và presenter **mỗi máy một nguồn mạng độc lập** — một dây LAN, một phát 4G, không dùng chung.

### Sự cố → xử lý

| Sự cố | Xử lý |
|---|---|
| Laptop admin sập | Mở laptop dự phòng đã đăng nhập → chơi tiếp đúng chặng đang dừng |
| Màn LED mất kết nối | F5 trang presenter, state tự khôi phục, người chơi không ảnh hưởng |
| Một người mất mạng | Họ F5 khi có sóng lại; chặng đã lỡ thì dùng **+1** nếu chính đáng |
| Người chơi mất danh tính | Đăng ký lại tên cũ, chỉnh vị trí bằng **+1/−1** cho khớp |
| Câu hỏi sai/tranh cãi | **↩️ Undo last reveal** → bỏ câu, sang câu kế |
| Mạng hội trường sập | Admin chuyển sang 4G; vẫn hỏng thì app tự về offline, MC dẫn trên màn lớn |
| Chạy quá giờ | Dừng ở chặng bất kỳ, bấm **🏆 Trao giải** |
