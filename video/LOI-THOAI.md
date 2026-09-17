# VNA Sky Race — video giới thiệu (3:12)

`VNA_SkyRace_GioiThieu.mp4` · 1920×1080 · 24 fps · H.264 + AAC stereo · 49 MB · −16 LUFS

Giọng đọc: **nam, giọng Bắc** (`vi-VN-NamMinh`, giọng nam neural tiếng Việt duy nhất Microsoft
cung cấp), tốc độ +8%, cao độ −3 Hz.

**Video là hoạt hình thật, không phải ảnh tĩnh.** Từng khung hình được chụp trực tiếp từ ứng dụng
đang chạy qua giao thức DevTools, với **đồng hồ ảo**: trình duyệt bị đóng băng thời gian, tua đúng
một khung rồi mới chụp. Nhờ vậy máy bay bay thật, đồng hồ đếm ngược thật, không có hiện tượng giật
hay nhảy số — dù máy render chậm đến đâu.

Bản đồ, toạ độ điểm dừng, biểu tượng sân bay, bảng xếp hạng, thẻ câu hỏi, ba nút trợ giúp và bốn
hiệu ứng thời tiết đều là **của chính app**, không vẽ lại.

---

## 14 cảnh

| # | Mốc | Cảnh | Hoạt hình |
|---|---|---|---|
| 1 | 0:00 | Mở đầu — **không lời thoại** | Máy bay di chuyển trên bản đồ, camera lùi chậm, tiêu đề hiện dần |
| 2 | 0:07 | Giới thiệu | Ba đợt máy bay bay tiếp, bảng xếp hạng đảo vị trí |
| 3 | 0:23 | Bắt đầu chơi | Gõ từng chữ "Minh Anh", lướt qua vài máy bay rồi chọn, nút sáng và được bấm, vào màn chơi |
| 4 | 0:39 | Bản đồ 16 chặng | **Đọc tên điểm nào, điểm đó bật sáng vàng** — 12 điểm theo đúng lời đọc |
| 5 | 1:01 | 4 điểm mốc | Bốn mốc nhấp nháy lần lượt, camera zoom vào cụm HAN, máy bay đi HAN→DAD→HUI |
| 6 | 1:17 | Nhịp một chặng | Câu hỏi hiện trước → 4 đáp án mở + **đồng hồ đếm ngược chạy thật** → Milan sáng xanh → máy bay bay tiếp |
| 7 | 1:32 | 🌈 Trời quang | Máy bay đứng yên, một chiếc tiến lên |
| 8 | 1:41 | 🌪 Nhiễu động | Máy bay đứng yên, một chiếc **bị đẩy lùi** |
| 9 | 1:50 | ⛈ Bão | **Bảng ATC cấp phép 10 máy bay** hiện lên, rồi 10 chiếc bay tiếp |
| 10 | 2:01 | ☀️ Trời nắng đẹp | Hai chiếc +1 chặng, một chiếc **+2 chặng và camera zoom vào** |
| 11 | 2:13 | Ba trợ giúp | Nói tới cái nào cái đó sáng **và được dùng thật**: 50:50 xoá 2 đáp án, Turbo chuyển vàng, chặng đổi sang nhiễu động để bật được Thắt dây an toàn |
| 12 | 2:31 | Về đích | Máy bay bay từ **FRA về FINISH**, camera bám theo và siết vào vạch đích |
| 13 | 2:43 | Giải thưởng | Đọc tới giải nào giải đó sáng lên, kèm **tiếng ting** |
| 14 | 3:01 | Lời chúc | Pháo giấy vàng, thẻ kết |

Câu hỏi demo dùng xuyên suốt: **"Chúng ta đang ở đâu?" — A: Milan · B: Amsterdam · C: Paris · D: London**
(đáp án đúng: Milan).

---

## Nhạc nền

`nhac-nen.wav` — **nhạc tự soạn**, không phải nhạc mua. Rê trưởng, 100 BPM, vòng hoà thanh I–V–vi–IV:
mở bằng pad, thêm bass và pluck, vào trống khi cuộc đua bắt đầu, kèn đồng nổi lên ở đoạn thời tiết
và trợ giúp, kết bằng hợp âm trưởng ngân dài.

> Soạn thay vì lấy nhạc có sẵn vì mọi bản nhạc thật đều cần giấy phép mà sự kiện chưa có — và một
> video khách hàng dùng nhạc sai phép là rắc rối tồn tại lâu hơn cả video. Toàn bộ âm thanh sinh ra
> từ dao động và nhiễu nên hoàn toàn thuộc quyền sử dụng của chương trình.

Nhạc được **tự động hạ xuống khi có lời thoại** (sidechain) và tự lên lại ở quãng nghỉ.
**Muốn thay nhạc khác:** chép file WAV mới đè lên `nhac-nen.wav` rồi chạy lại `build.py` — chỉ mất
vài phút, không phải render lại hình.

---

## Dựng lại

| File | Việc |
|---|---|
| `toolkit/script.json` | 14 cảnh, chia theo **từng câu ngắn**, mỗi câu có thể mang một `cue` |
| `toolkit/tts.py` | Đọc từng câu riêng rồi ghép → biết chính xác mốc thời gian của mỗi `cue` |
| `toolkit/driver.html` | Kịch bản dàn cảnh: mỗi cảnh là một dòng thời gian gắn vào các `cue` |
| `toolkit/cdp.py` | Điều khiển trình duyệt bằng đồng hồ ảo |
| `toolkit/capture.py` | Chụp từng khung hình, đẩy thẳng vào ffmpeg |
| `toolkit/build.py` | Ghép cảnh, trộn lời thoại + nhạc + tiếng ting |
| `toolkit/music.py` | Sinh nhạc nền |

Thứ tự chạy: `tts.py` → `capture.py` → `music.py` → `build.py`.

> Dịch vụ đọc **không trả về mốc thời gian từng từ** cho tiếng Việt (chỉ có mốc từng câu), nên không
> thể hỏi "từ Paris được đọc ở giây thứ mấy". Vì vậy mỗi cảnh được viết thành nhiều câu ngắn, đọc
> riêng từng câu — mốc bắt đầu của mỗi câu là chính xác, và cũng nhờ đó chủ động được nhịp ngắt nghỉ.

Bản dùng để chụp đã **gỡ ba thẻ `<script>` Firebase**, nên luôn chạy offline và không bao giờ chạm
vào cơ sở dữ liệu thật của sự kiện. `public/` không bị sửa.

Cần: `ffmpeg`, `python` + `edge-tts` + `websocket-client` + `numpy`, và Microsoft Edge.

### Ba điều đã phải xử lý khi render (ghi lại để lần sau không mất thời gian)

- **`--window-size` không phải kích thước khung hình.** Phần khung cửa sổ bị trừ vào, nên xin
  1920×1080 mà nhận được 1896×988 — tức tỉ lệ 1,92:1 chứ không phải 16:9. Phải ép bằng
  `Emulation.setDeviceMetricsOverride`.
- **Trình duyệt chỉ chụp được khung mới khi có thứ gì đó chuyển động.** Sau khi tắt hoạt ảnh mây để
  tăng tốc, hai cảnh điện thoại đứng im hoàn toàn và lệnh chụp treo vô hạn. Khắc phục bằng một chấm
  2px nhấp nháy liên tục (`#vidHeartbeat`).
- **Chạy 4 luồng song song trên máy 4 nhân còn chậm hơn 1 luồng** vì tràn RAM. Hai luồng là mức tối
  ưu: 58 phút cho toàn bộ 14 cảnh.
