# VNA Sky Race — hướng dẫn dựng và chạy sự kiện

Game quiz đua máy bay 3 màn hình cho sự kiện ~50 người, mỗi người một điện thoại.

```
VNA_Race/
├── public/index.html        ← app (deploy cái này)
├── public/vendor/           ← asset offline, sinh ra bởi scripts/vendor-assets.mjs
├── database.rules.json      ← phân quyền admin/player (Firebase Realtime Database)
├── firebase.json            ← cấu hình database rules deploy (không dùng Firebase Hosting)
├── vercel.json              ← deploy tĩnh public/ lên Vercel, không cần build step
├── scripts/vendor-assets.mjs
└── test/rules.test.js       ← 29 test luật chơi
```

---

## Luật chơi

**Bản đồ:** 12 chặng, `START → CDG → AMS → HAN★ → MUC → MOW → SPC★ → LHR → MXP → CPH → SGN★ → FRA → FINISH★`

**Ngôn ngữ:** app có nút **VI/EN**, **mặc định tiếng Việt**. Nút nằm ở góc trên bên phải màn hình chính, và lặp lại ngay trên thẻ đăng ký của người chơi (khách quét QR vào thẳng `#player` nên không thấy màn hình chính). Toàn bộ giao diện — kể cả **câu hỏi, đáp án và ghi chú người dẫn** — đều đổi theo.

Lựa chọn ngôn ngữ lưu **theo từng thiết bị** (`localStorage`), không đồng bộ: MC có thể chạy màn LED tiếng Việt trong khi một khách nước ngoài đọc điện thoại tiếng Anh. Hai bên vẫn thấy **cùng một chữ cái ứng với cùng một đáp án**, vì thứ tự xáo đáp án chỉ phụ thuộc id câu hỏi chứ không phụ thuộc ngôn ngữ.

> ⚠️ Bản dịch tiếng Việt của 31 câu hỏi và ghi chú người dẫn **nên được người của Vietnam Airlines rà lại trước sự kiện** — MC sẽ đọc trước các đại lý du lịch và nội dung có nhiều thuật ngữ ngành. Các tên riêng sản phẩm (LotusMiles, Transit Tour, Tour Series, Business FOC, Gold Agent, Premium Economy…) được giữ nguyên tiếng Anh theo cách gọi thông dụng trong ngành.

**Ngân hàng câu hỏi:** 31 câu (từ `Question.docx`), hỏi **lần lượt theo đúng thứ tự** trong file, mỗi chặng một câu, **câu đã dùng không bao giờ lặp lại**. Hết 31 câu thì admin không mở thêm được câu mới.

> Vị trí A/B/C/D của mỗi câu được **xáo tự động** khi vào game. File gốc có 29/31 câu đáp án đúng nằm ở B — nếu giữ nguyên, người chơi chỉ cần luôn bấm B là thắng. Nội dung câu hỏi và đáp án đúng giữ nguyên 100%, chỉ đổi vị trí chữ cái. Thuật toán xáo là tất định (seed theo id câu hỏi) nên mọi điện thoại, màn LED và dashboard admin đều thấy **cùng một thứ tự** mà không cần đồng bộ gì thêm.

**Nhịp một chặng — admin bấm 2 lần:**

1. **Next question →** (hoặc *Show question* ở chặng đầu): **câu hỏi hiện ra sau 2 giây** nhưng **chưa có đáp án**, đồng hồ chưa chạy — cả phòng đọc câu hỏi trước. Nếu chặng có thời tiết thì cảnh báo to hiện trước trong **10 giây** rồi mới tới câu hỏi. Cảnh báo **nổi trên bản đồ đang chạy**, không che đen màn hình.
2. **Open answers & start clock**: 4 đáp án hiện lên và đồng hồ **20 giây** bắt đầu chạy.

**Đếm ngược & reveal:** đồng hồ đồng bộ trên cả 3 màn hình (player, presenter, admin) — cùng một bộ đếm, sai lệch tối đa 0,2 giây. Đồng hồ **chuyển đỏ và nháy to ở 5 giây cuối**. Hết giờ đáp án **tự động được reveal**, admin không cần bấm gì — màn presenter hiện đáp án đúng (tô xanh) trong **5 giây**, **máy bay chỉ bắt đầu di chuyển sau khi hết 5 giây đó**.

**Chọn rồi mà không bấm Nộp:** hết giờ hệ thống **tự khoá đáp án đang chọn** — vẫn được tính bình thường. Chỉ mất lợi thế về thời gian: đáp án tự khoá được ghi nhận bằng **trọn 20 giây**.

**Không chọn gì:** vẫn bị cộng **trọn 20 giây** vào tổng thời gian. Ngồi im không bao giờ thắng được tiêu chí phụ về thời gian.

### Ba sự trợ giúp

Mỗi thứ dùng **một lần cả ván**, hiển thị là 3 nút tròn dưới ô "Select an answer above". **50:50 dùng được ngay từ chặng đầu, không phân biệt xếp thứ mấy**; Turbo Boost và Fasten Seatbelt **mở khoá riêng cho từng người khi máy bay của họ tới MUC**.

| Trợ giúp | Tác dụng | Bị khoá khi |
|---|---|---|
| ✂️ **50:50** | Loại bỏ 2 đáp án sai | turbulence · storm · Trời nắng đẹp |
| ⚡ **Turbo Boost** | Đúng → **+2 chặng**, sai → **−1 chặng** | turbulence · storm · Trời nắng đẹp |
| 🔒 **Fasten Seatbelt** | **Chỉ dùng được trong turbulence** — trả lời sai vẫn **không bị lùi 1 chặng** | mọi chặng không phải turbulence |

Bật Turbo/Seatbelt mà không bấm Nộp thì không bị phạt và không mất lượt.

**☀️ Trời nắng đẹp / Sunshine** — nút của admin, **một lần duy nhất cả ván**, bấm trước khi mở câu hỏi. Màn LED hiện ☀️ TRỜI NẮNG ĐẸP. Người **trả lời đúng nhanh nhất** được **+2 chặng**, người đúng khác +1, người sai đứng nguyên. Không bật được trên chặng turbulence/storm. Huỷ trước khi mở câu thì được trả lại lượt. Cả ba trợ giúp bị khoá.

**Turbulence** — tự động ở **chặng 6 và chặng 10**. Màn LED chuyển theme mưa sấm chớp, badge đổi từ 🌈 Clear Skies sang 🌪 Turbulence. Trả lời đúng **đứng nguyên**, **không đúng thì lùi 1 chặng** (kể cả người không trả lời) — trừ khi bật 🔒 Fasten Seatbelt. 50:50 và Turbo bị khoá.

**Thông báo thời tiết** — ngay khi admin bấm *Next question →* vào chặng turbulence/storm (hoặc bật Trời nắng đẹp), màn presenter **và** màn của mọi người chơi hiện **thông báo to** kèm luật chơi. Bấm *Open question* thì thông báo to biến mất, chỉ còn badge thời tiết nhỏ ở góc.

**⛈ Storm** — tự động ở **chặng 8**. Màn LED đổi badge sang ⛈ Storm, theme tối/mưa nặng hơn turbulence. Chỉ **10 người trả lời đúng nhanh nhất** (tính theo thời gian riêng của câu này) được ATC cấp phép bay tiếp **+1 chặng**; tất cả người chơi còn lại đứng nguyên (kể cả đúng nhưng không lọt top 10). Turbo và Trời nắng đẹp đều bị khoá ở chặng này. Sau khi admin bấm Reveal, màn presenter hiện danh sách 10 người được bay tiếp trong 10 giây.

**Kết thúc ván & Overtime** — ván đấu chỉ thực sự kết thúc (`FINISHED`) khi có **đủ 4 người chơi về tới FINISH**. Bản đồ chỉ có 12 chặng, nhưng nếu hết chặng 12 mà chưa đủ 4 người về đích, admin vẫn bấm **Next question →** để mở thêm câu hỏi — màn hình hiện **"Overtime round N"** thay vì số chặng. Ai về tới FINISH trước sẽ thấy ngay màn hình cá nhân báo thứ hạng + lời chúc, kể cả khi ván vẫn đang tiếp diễn cho người khác.

**Thắng & giải thưởng:** ai tới FINISH trước. Nhiều người cùng tới trong một lượt thì xếp theo *số câu đúng → tổng thời gian trả lời*.

| Hạng | Giải |
|---|---|
| 1 | 🏆 Cúp vô địch — 1 vé máy bay hạng Thương gia |
| 2 | 🥇 Huy chương vàng — 1 vé máy bay hạng Phổ thông Đặc biệt |
| 3 | 🥈 Huy chương bạc — 1 voucher nâng hạng lên Thương gia |
| 4 | 🥉 Huy chương đồng — 1 vé máy bay hạng Phổ thông |

Cùng rất nhiều phần quà nhỏ hấp dẫn khác. Danh sách giải thưởng hiện ngay trong **Hướng dẫn** (trang 1).

Bộ biểu tượng này dùng thống nhất ở **Live Leaderboard**, bảng xếp hạng admin, màn hình cá nhân khi về đích và **lễ trao giải** (tên nhà vô địch hiện to nhất kèm cúp, ba người còn lại xếp thành hàng vàng–bạc–đồng).

**☀️ FINAL ROUND** — ngay khi có người đỗ tại **FRA** (chặng áp chót), câu đúng tiếp theo là về đích. Màn presenter chuyển sang hệ nắng chói chang kèm badge **FINAL ROUND** đặt cạnh chỉ báo thời tiết; màn người chơi cũng đổi theo. Badge thời tiết vẫn giữ nguyên bên cạnh — nếu chặng đó có turbulence/storm thì hiệu ứng thời tiết được ưu tiên, chỉ hiện thêm badge.

**Người đầu tiên về đích** — màn presenter zoom vào ô FINISH, **chỉ máy bay của người đó** từ từ bay vào đích trong 5 giây, sau đó mới tới lượt tất cả máy bay còn lại di chuyển.

**Khi ván kết thúc, mọi người chơi** — không chỉ 4 người có giải — đều nhận được màn hình báo **thứ hạng cuối cùng của mình** kèm lời chúc của chương trình.

**Live Leaderboard** hiện **tất cả người chơi** (panel tự cuộn). Riêng bản đồ vẫn giữ nguyên cách hiển thị cũ: 5 máy bay dẫn đầu có tên, còn lại gộp thành cụm `+N`.

**✈️ Cabin Bulletin** — ô ngay dưới leaderboard (cao bằng 1/2), viết theo giọng thông báo trên máy bay, tổng kết **câu vừa xong**: người trả lời đúng nhanh nhất 🥇, số người đúng ✅, tỉ lệ đúng 📊, người dẫn đầu đang ở chặng nào 👑, chặng đông máy bay nhất 🛬, và nhịp độ phòng 🚀/🧭/🐢 (theo thời gian trả lời trung bình: dưới 7s Fast, dưới 14s Steady, còn lại Slow).

**Màn hình người chơi** hiện **route map nằm ngang** thay cho thanh tiến độ: 13 điểm dừng nối liền nhau, điểm đang đứng sáng vàng và to hơn kèm tên mã, điểm đã qua mờ đi, điểm phía trước mờ hơn nữa.

**📖 Hướng dẫn** có 5 trang: (1) luật chơi + giải thưởng, (2) **bản đồ hành trình vẽ tĩnh** — cùng đường cong chữ S và cùng toạ độ mà màn presenter dùng, để người chơi hình dung trước sa bàn sẽ đua, (3) các loại thời tiết, (4) ba trợ giúp, (5) tài liệu chương trình (Sales Kit tiếng Việt + tiếng Anh).

**Nâng hạng khoang theo thứ hạng** — người **dẫn đầu** thấy màn hình chuyển sang **vàng Hạng Thương gia**, người **hạng nhì** sang **xanh ngọc Hạng Phổ thông Đặc biệt**, từ hạng ba trở xuống giữ giao diện thường. Cả hai đều kèm dòng báo ai đang bám sát phía sau và cách bao nhiêu chặng.

**Màn presenter** — khi admin mở câu hỏi, màn LED hiện **câu hỏi + 4 đáp án + đồng hồ đếm ngược cỡ lớn** trên nền đặc (không blur, để đọc được từ cuối phòng), bảng xếp hạng vẫn hiện bên phải. Có nút **⛶ Fullscreen** ở góc trên.

Chạy test luật chơi:

```bash
node test/rules.test.js public/index.html
```

---

## Dựng lần đầu

Project Firebase (`vietnam-airlines-sky-race`) và `FIREBASE_CONFIG` đã có sẵn, hardcode thẳng trong `public/index.html` — không cần điền gì thêm để chạy. Config này (apiKey, databaseURL...) an toàn khi lộ ra client, vì quyền hạn thật sự nằm ở `database.rules.json`, không phải ở việc giấu mấy giá trị này.

### 1. Kiểm tra Firebase project (nếu chưa từng dựng)

Vào [console.firebase.google.com](https://console.firebase.google.com) → project `vietnam-airlines-sky-race`:

- **Realtime Database** đã bật, databaseURL: `https://vietnam-airlines-sky-race-default-rtdb.firebaseio.com`.
- **Authentication** → bật **Anonymous** và **Email/Password**.
- **Authentication → Users → Add user**: email `admin@vna-sky-race.local`, đặt mật khẩu mạnh. Đây là tài khoản admin duy nhất — mật khẩu không nằm trong code.
- **Realtime Database → Rules** → dán nội dung `database.rules.json` (hoặc `firebase deploy --only database` — cần `npm install -g firebase-tools` rồi `firebase login`).

> Với ~50-200 người chơi, hãy **nâng lên gói Blaze** và đặt budget alert $1. Gói Spark có trần 100 kết nối đồng thời; kết nối treo sau mỗi lần F5 khiến người chơi thật có thể chạm trần, và khi chạm thì người vào sau bị chặn im lặng.

### 2. Đóng gói asset offline (tuỳ chọn)

```bash
node scripts/vendor-assets.mjs
```

Tải font và confetti về `public/vendor/` rồi trỏ lại đường dẫn (Firebase SDK vẫn load từ CDN của Google — xem đầu `public/index.html` — vì app đã tự rơi về offline nếu 3 script đó tải lỗi). Cần internet để chạy, làm ở văn phòng chứ không phải tại sự kiện.

### 3. Deploy — GitHub + Vercel

```bash
git push
```

Push lên [github.com/backyo1403/VSR](https://github.com/backyo1403/VSR), Vercel tự build lại (không cần build step — `vercel.json` trỏ thẳng `outputDirectory` vào `public/`). App live tại **https://vsr-seven.vercel.app**.

### 4. Ba đường link

| Vai | Link |
|---|---|
| Người chơi | `https://vsr-seven.vercel.app/#player` ← **in QR khổ lớn, dán nhiều chỗ** |
| Màn LED | `https://vsr-seven.vercel.app/#presenter` |
| Điều phối | `https://vsr-seven.vercel.app/#admin` → nhập mật khẩu tài khoản admin |

Chơi nhiều lượt thì thêm room code: `?room=SKY02#player` (mặc định `SKY01`), hoặc người chơi tự gõ room code ở màn đăng ký (giới hạn 200 người/phòng).

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
