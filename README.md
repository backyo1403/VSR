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

> ⚠️ File gốc `Question Viet.docx` trộn cả câu tiếng Việt lẫn câu tiếng Anh, còn `Question Viet addon.docx` thuần tiếng Việt. Câu nào thiếu ngôn ngữ nào thì **đã được dịch bổ sung** để nút VI/EN đổi được toàn bộ. Bản dịch **nên được người của Vietnam Airlines rà lại trước sự kiện** — MC sẽ đọc trước các đại lý du lịch và nội dung có nhiều thuật ngữ ngành. Các tên riêng sản phẩm (LotusMiles, Transit Tour, Tour Series, Business FOC, Gold Agent, Premium Economy…) được giữ nguyên tiếng Anh theo cách gọi thông dụng trong ngành.

**Ngân hàng câu hỏi:** 30 câu thường từ `Question Viet.docx`, **đánh số đúng theo file** (id N = "Câu N"). Hỏi **lần lượt theo đúng thứ tự** đó, mỗi lượt một câu, **câu đã dùng không bao giờ lặp lại**. Hết 30 câu thì admin không mở thêm được câu mới.

> **Đáp án đúng giữ nguyên 100% theo file** — chỉ **vị trí A/B/C/D bị xáo**. Muốn cập nhật ngân hàng câu hỏi thì sửa `QUESTION_BANK` trong `public/index.html`: mỗi mục có `id` (số câu trong file), `correct` (chỉ số 0-3 của đáp án đúng **theo thứ tự gốc trong file**, trước khi xáo), và hai khối `vi` / `en`.

**Câu hỏi Sunshine** nằm riêng, **không bao giờ ra ở lượt thường**: nó chỉ hiện khi admin bấm ☀️ Trời nắng đẹp. Bấm lần nữa để huỷ thì câu thường đang chờ được trả lại nguyên vẹn vào kho.

> Vị trí A/B/C/D của mỗi câu được **xáo tự động** khi vào game. File gốc để đáp án đúng ở B hoặc C gần như mọi câu — nếu giữ nguyên, người chơi chỉ cần luôn bấm B/C là thắng. Nội dung câu hỏi và đáp án đúng giữ nguyên 100%, chỉ đổi vị trí chữ cái. Thuật toán xáo là tất định (seed theo id câu hỏi) nên mọi điện thoại, màn LED và dashboard admin đều thấy **cùng một thứ tự** mà không cần đồng bộ gì thêm.

**Nhịp một chặng — admin bấm 2 lần:**

1. **Next question →** (hoặc *Show question* ở chặng đầu): **câu hỏi hiện ra sau 2 giây** nhưng **chưa có đáp án**, đồng hồ chưa chạy — cả phòng đọc câu hỏi trước. Nếu chặng có thời tiết thì cảnh báo to hiện trước trong **10 giây** rồi mới tới câu hỏi. Cảnh báo **nổi trên bản đồ đang chạy**, không che đen màn hình.
2. **Open answers & start clock**: 4 đáp án hiện lên và đồng hồ **20 giây** bắt đầu chạy.

**Đếm ngược & reveal:** đồng hồ đồng bộ trên cả 3 màn hình (player, presenter, admin) — cùng một bộ đếm, sai lệch tối đa 0,2 giây. Đồng hồ **chuyển đỏ và nháy to ở 5 giây cuối**. Hết giờ đáp án **tự động được reveal**, admin không cần bấm gì — màn presenter hiện đáp án đúng (tô xanh) trong **5 giây**, **máy bay chỉ bắt đầu di chuyển sau khi hết 5 giây đó**.

**Chọn rồi mà không bấm Nộp:** hết giờ hệ thống **tự khoá đáp án đang chọn** — vẫn được tính bình thường. Chỉ mất lợi thế về thời gian: đáp án tự khoá được ghi nhận bằng **trọn 20 giây**.

**Không chọn gì:** vẫn bị cộng **trọn 20 giây** vào tổng thời gian. Ngồi im không bao giờ thắng được tiêu chí phụ về thời gian.

### Ba sự trợ giúp

Mỗi thứ dùng **một lần cả ván**, hiển thị là 3 nút tròn dưới ô "Select an answer above". Cả ba — 50:50, Turbo Boost và Fasten Seatbelt — **mở khoá riêng cho từng người khi máy bay của chính họ tới MUC**, không phải khi cuộc đua tới MUC.

> **Mở khoá là một chiều.** Đã tới MUC một lần thì giữ trợ giúp **cả ván**, kể cả khi nhiễu động đẩy tụt lại HAN hay về tận START. Mất trợ giúp trên đường lùi lại nghĩa là bị phạt hai lần cho cùng một câu trả lời sai. Cờ `reachedMuc` nằm trên node `progress` (admin sở hữu) nên sống sót qua reload điện thoại; nó cũng tự bật cho người chơi đã ở MUC trở lên nhưng dữ liệu cũ chưa có cờ này.

| Trợ giúp | Tác dụng | Bị khoá khi |
|---|---|---|
| ✂️ **50:50** | Loại bỏ 2 đáp án sai | turbulence · storm · Trời nắng đẹp |
| ⚡ **Turbo Boost** | Đúng → **+2 chặng**, sai → **−1 chặng** | turbulence · storm · Trời nắng đẹp |
| 🔒 **Fasten Seatbelt** | **Chỉ dùng được trong turbulence** — trả lời sai vẫn **không bị lùi 1 chặng** | mọi chặng không phải turbulence |

Bật Turbo/Seatbelt mà không bấm Nộp thì không bị phạt và không mất lượt.

**☀️ Trời nắng đẹp / Sunshine** — nút của admin, **một lần duy nhất cả ván**, bấm trước khi mở câu hỏi. Màn LED hiện ☀️ TRỜI NẮNG ĐẸP và **câu hỏi Sunshine riêng** được đưa ra thay cho câu thường. Người **trả lời đúng nhanh nhất** được **+2 chặng**, người đúng khác +1, người sai đứng nguyên. Không bật được trên chặng turbulence/storm. Huỷ trước khi mở câu thì được trả lại lượt. Cả ba trợ giúp bị khoá.

**Turbulence** — tự động ở **chặng 6 và chặng 10**, cộng thêm **một lượt bất ngờ ngay sau khi máy bay đầu tiên tới SGN**. Màn LED chuyển theme mưa sấm chớp, badge đổi từ 🌈 Clear Skies sang 🌪 Turbulence. Trả lời đúng **đứng nguyên**, **không đúng thì lùi 1 chặng** (kể cả người không trả lời) — trừ khi bật 🔒 Fasten Seatbelt. 50:50 và Turbo bị khoá.

> Lượt nhiễu động theo SGN được tính bằng **vị trí ≥ SGN** chứ không phải "hạ cánh đúng ở SGN", vì một cú Turbo (+2 chặng) có thể đưa máy bay vượt thẳng qua SGN mà không dừng lại. Nếu lượt kế tiếp đã có thời tiết riêng (chặng 6/10 hoặc chặng Storm) thì nó tự đẩy sang lượt sau để không chồng lên nhau. Bấm *Undo* sẽ trả lại trạng thái trước khi lượt này được kích hoạt.

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

**Nâng hạng khoang theo thứ hạng** — người **dẫn đầu** thấy màn hình chuyển sang **vàng Hạng Thương gia**, người **hạng nhì** sang **xanh ngọc Hạng Phổ thông Đặc biệt**. **Hạng ba và hạng tư** là **Hạng Phổ thông**, riêng hạng ba có thêm dòng *"Nâng lên hạng Thương gia nếu còn chỗ"*. Từ hạng năm trở xuống không có ruy-băng. Cả bốn hạng đầu đều kèm dòng báo ai đang bám sát phía sau và cách bao nhiêu chặng.

> Chỉ hạng nhất và hạng nhì đổi cả nền màn hình; hạng ba/tư chỉ có ruy-băng — để khoang vàng và khoang xanh ngọc vẫn là thứ đáng để giành giật.

**Đổi khoang thì màu chuyển từ từ**, không nhảy phát một: nền cũ mờ dần trong khi nền mới hiện dần (~1,1 giây), các panel đổi màu viền/nền theo trong ~0,9 giây, và ruy-băng mới trượt vào. Được nâng hạng — hoặc bị tụt xuống — phải *cảm nhận* được như đèn khoang đổi màu, chứ không như vừa tải lại trang.

> CSS **không transition được gradient** (`background-image` không phải thuộc tính animate được), nên mỗi khoang có một **lớp phủ toàn màn hình riêng** và chỉ **độ mờ của lớp** được transition. Nhờ vậy vàng và xanh ngọc mới hoà vào nhau được, và cả hai đều mờ hẳn đi khi người chơi tụt về Phổ thông. Riêng ô đáp án đúng/sai lúc công bố vẫn đổi màu **tức thì** — chỗ đó chậm lại là sai.

**Màn presenter** — khi admin mở câu hỏi, màn LED hiện **câu hỏi + 4 đáp án + đồng hồ đếm ngược cỡ lớn** trên nền đặc (không blur, để đọc được từ cuối phòng), bảng xếp hạng vẫn hiện bên phải. Có nút **⛶ Fullscreen** ở góc trên.

### Bản đồ đường đua

Bản đồ chạy trên **tranh minh hoạ quần đảo** (`public/vendor/route-bg.jpg`). Mỗi điểm dừng được **ghim đúng vào công trình của nó** trên tranh — START ở đường băng, CDG ở tháp Eiffel, MOW ở nhà thờ Thánh Basil, HAN ở chùa, FINISH ở đường băng phía trên…

Toạ độ 13 điểm trong `ROUTE` là **số đo lấy từ chính bức tranh**, không phải sinh ra bằng công thức (bản trước rải đều theo đường cong chữ S). Muốn dời một điểm thì đọc toạ độ pixel trên tranh rồi nhân với `MAP_W / chiều-rộng-ảnh`. **Đừng "nắn" lại cho thành đường cong đẹp** — đó là số đo, không phải bố cục.

Tranh **phủ kín panel, sát tới viền bo ngoài** — không có dải trống nào — và **không bị kéo méo**: tranh được phóng đúng tỉ lệ gốc cho tới khi che kín cả hai chiều, phần thừa bị cắt bởi khung ngoài. Với tỉ lệ panel thực tế (~1,48–1,54) thì phần cắt chỉ khoảng 1–3%, không điểm nào bị cắt mất.

> **Vì sao kích thước tranh do JS đặt** (`fitMapStage`), không phải `background-size:cover`: ghim được định vị bằng **phần trăm của bức tranh**. Nếu chỉ cho CSS cắt ảnh nền, phần trăm đó vẫn tính trên khung chưa cắt và **mọi ghim sẽ trôi khỏi công trình**. Đặt kích thước cho chính phần tử chứa tranh thì ghim và ảnh nằm chung một hệ toạ độ — đo thực tế độ lệch ghim là 0,00002 (tức bằng 0).

> **Đường bay vàng vẽ hai nét chồng nhau**: một nét viền tối bên dưới rồi nét vàng đứt nét bên trên. Nét chấm mảnh của bản cũ hợp với nền gradient phẳng, nhưng đặt lên tranh thì mất hút giữa vùng nước sáng và bãi cát.

**Bản đồ có sự sống** — vài chiếc thuyền buồm trôi chậm trên sông, dăm đàn chim bay ngang, và mấy đám mây trôi qua khung hình. Tất cả đều **rất chậm** (một lượt qua màn mất 90–260 giây) và **nằm dưới đường bay lẫn các điểm dừng** — không thứ gì được phép che một điểm dừng hay một máy bay trên màn LED.

> **Tuyến thuyền không phải ước lượng bằng mắt.** Bức tranh được lấy mẫu trên lưới 50×33 và phân loại theo màu pixel (xanh dương trội rõ, không gần trắng); 5 tuyến trong `SHIPPING_LANES` là những dải cho kết quả "nước" từ đầu đến cuối. Bộ test kiểm lại từng tuyến trên chính bản đồ nước đó — lần chạy đầu đã bắt được một tuyến ở đường chân trời đi xuyên qua một hòn đảo nhỏ. Toạ độ tính theo phần trăm bản đồ nên thuyền giữ đúng luồng nước ở mọi kích thước màn.

**Máy bay bay theo hướng đường vàng** — mỗi máy bay xoay theo đúng hướng chặng nó sắp bay, thay vì luôn chúc mũi lên trời. Về tới FINISH thì giữ nguyên hướng lúc hạ cánh chứ không quay ngược về hướng bắc. Icon trong bảng xếp hạng vẫn để thẳng đứng như cũ.

⚠️ **File gốc `Background.png` (8000×5328, ~197 MB) không được commit** — GitHub chặn file trên 100 MB và nó sẽ phình repo vĩnh viễn. File này đã nằm trong `.gitignore`; giữ bản gốc trên ổ chia sẻ. Bản web `public/vendor/route-bg.jpg` (2400px, ~780 KB) mới là bản app dùng và **có** được commit. Muốn xuất lại bản web thì resize `Background.png` xuống 2400px, JPEG chất lượng ~82.

### Bầu trời trên màn presenter

**Trời quang** — nắng nhẹ hắt từ **góc trên bên phải** bản đồ: một vầng sáng ấm cộng một lớp wash rộng, nên nửa trên bên phải sáng hơn hẳn góc dưới bên trái. Thân máy bay **bắt sáng theo vị trí** — càng bay về phía nắng càng sáng và có viền vàng nhẹ (HAN/MUC/FINISH là ba điểm sáng nhất, START/CPH tối nhất). Khi một máy bay lọt vào **vùng sáng nhất**, một **lens flare rất nhẹ** loé lên khoảng 1 giây rồi tắt. Cả ba hiệu ứng **tự tắt** khi có nhiễu động, bão hoặc Trời nắng đẹp — lúc đó theme thời tiết làm chủ màn hình.

> Flare chỉ loé **khi máy bay vừa bay vào** vùng sáng, không loé lại nếu nó đứng yên ở đó — nếu không mỗi giây một lần sẽ thành đèn nháy.

**Mây chia 3 lớp** để có chiều sâu — mỗi lớp khác nhau cả tốc độ, kích thước, độ mờ và độ nét, kèm bóng đổ nhẹ:

| Lớp | Số mây | Một vòng qua màn hình |
|---|---|---|
| Mây xa | 5 | ~150–220s (bò rất chậm, nhỏ và mờ nhất) |
| Mây giữa | 4 | ~85–130s |
| Mây gần | 3 | ~44–66s (to, rõ và nhanh nhất) |

**Turbo Boost → cả bầu trời tăng tốc** khoảng **1,8×** trong 6 giây, giữ nguyên tỉ lệ parallax giữa ba lớp, nên khán giả *cảm* được tốc độ chứ không chỉ thấy một máy bay nhảy 2 chặng. Hiệu ứng khớp đúng lúc máy bay bắt đầu bay (sau khi thẻ đáp án tắt).

> Màn presenter **không đọc được** nhánh `answers` trên Firebase (chỉ admin đọc được — xem `database.rules.json`), nên số lượt dùng Turbo được admin tính sẵn và **gửi kèm trong `legBrief`**. Đó là cách màn LED biết có ai vừa boost.

**Vật thể nhỏ ở hậu cảnh** — cứ **15–25 giây** ngẫu nhiên xuất hiện **một** thứ rất nhỏ và rất mờ, bay ngang qua rồi mất: chim bay xa (🐦/🕊), một máy bay thương mại siêu nhỏ (✈️), hoặc một vệt contrail mảnh. Bay cả hai chiều. Mục đích duy nhất là làm thế giới trông như đang sống — nên chúng cố tình nhỏ và mờ tới mức không tranh sự chú ý với cuộc đua. Tự dừng khi có thời tiết hoặc khi không ai đang xem màn presenter.

**Camera System** — ba nút cạnh nút Fullscreen, đổi góc quay bản đồ:

| Nút | Góc quay | Zoom |
|---|---|---|
| **CAM 1** | Toàn bộ đường đua | 1× |
| **CAM 2** | Bám theo người dẫn đầu | 1,85× |
| **CAM 3** | Vùng đang đông máy bay nhất | 1,6× |

CAM 2 và CAM 3 **tự bám theo** khi đội hình di chuyển. Nếu chưa có người chơi nào thì cả hai tự trả về góc rộng thay vì zoom vào chỗ trống.

> **Cinematic luôn thắng camera.** Lúc máy bay đầu tiên hạ cánh (zoom solo) và lúc kết thúc cuộc đua (zoom vào FINISH), bản đồ do cinematic điều khiển; bộ chọn CAM mờ đi và không có tác dụng. Khi cinematic xong, camera **tự trả về đúng CAM mà MC đang chọn** — không nhảy về CAM 1.

> **Zoom kéo theo cả nền tranh.** Tranh nền nằm trên đúng phần tử mà camera phóng to, nên tranh, đường bay và các điểm dừng phóng cùng nhau như một khối. Trước đây tranh nằm ở lớp trên nên chỉ điểm và đường bay phóng, còn nền đứng yên — mọi điểm lệch khỏi công trình khi đổi CAM.

### Thông báo Turbo Boost

Ngay khi có người bấm **⚡ Turbo Boost**, tên người đó hiện lên **góc trên bên phải** màn presenter trong **3 giây**. Nhiều người bấm cùng lúc thì bảng ghi **tất cả các tên**, và bảng chỉ tắt **3 giây sau khi người cuối cùng bấm** — mỗi người bấm thêm sẽ gia hạn bảng.

> Hai người bấm cách nhau hơn 3 giây sẽ được tính là **hai đợt riêng**, mỗi đợt một bảng, chứ không gộp thành một bảng chạy mãi.

Bảng đặt **chồng lên đầu cột bên phải, không bao giờ che câu hỏi** — lúc có câu hỏi thì khung câu hỏi phủ kín toàn bộ bản đồ, nên mọi thứ đặt trong bản đồ sẽ hoặc bị khuất, hoặc che mất đáp án.

> Màn presenter **không đọc được** nhánh `answers` (chỉ admin đọc được), nên nếu chờ tới lúc công bố đáp án mới biết ai bật Turbo thì đã quá muộn để thông báo. Vì vậy có thêm nhánh `boosts/{lượt}/{uid}` trong `database.rules.json`, **chỉ chứa tên và mốc thời gian — không bao giờ chứa đáp án** — nên mọi client đã đăng nhập đều đọc được mà không lộ bài của ai. Mỗi người chỉ ghi được vào ô của chính mình; bỏ bật Turbo thì xoá luôn tên khỏi bảng.

⚠️ **Nhánh `boosts` là rule mới — phải publish lại `database.rules.json` lên Firebase Console**, nếu không thông báo sẽ không chạy khi online (offline vẫn chạy vì cả state được broadcast).

### Event Feed — dòng tin chạy dưới cùng

Một dải tin kiểu bản tin thời sự, có cờ đỏ **TRỰC TIẾP / LIVE** ghim bên trái, chữ **chạy liên tục từ phải sang trái suốt cả cuộc đua**. Nội dung tự sinh từ tình hình thực tế, khoảng **12–18 tin** mỗi vòng:

- **Thứ hạng** — ai dẫn đầu và đang ở đâu, hạng nhì kém bao nhiêu chặng, hạng ba, ai đang về sau cùng. Nếu hạng nhì ngang bằng hoặc chỉ kém 1 chặng thì đổi thành tin "sát nút / bám sát".
- **Đường về đích** — người dẫn đầu còn bao nhiêu chặng nữa là hạ cánh, cảnh báo CHẶNG CUỐI, ai đã hạ cánh và về thứ mấy, còn bao nhiêu suất về đích.
- **Vòng vừa rồi** — bao nhiêu người trả lời đúng (có câu riêng cho "không ai đúng" và "cả phòng đều đúng"), ai trả lời đúng nhanh nhất và trong bao lâu, mấy người bật Turbo Boost, nhịp độ khoang, và **ai vừa vượt ai**.
- **Phong độ** — tỉ lệ đúng cao nhất là ai (kèm số câu), ai đang có chuỗi đúng liên tiếp từ 3 câu trở lên, ai là người đầu tiên tới HAN / SPC / SGN.
- **Giao thông & thời tiết** — điểm đang đông máy bay nhất, tình hình thời tiết hiện tại kèm luật đang áp dụng, còn bao nhiêu câu trong kho.

> **Ai vừa vượt ai** được suy ra từ `undoSnapshot` — bảng vị trí *trước* khi công bố đáp án mà admin ghi lại cho đúng vòng đó. Nhờ vậy không cần đồng bộ thêm dữ liệu nào.

Hai điểm về cách chạy:

- **Vòng lặp không có mối nối.** Danh sách tin được đặt **hai bản giống nhau** cạnh nhau rồi trượt đúng `-50%`, nên khi bản thứ nhất ra khỏi màn hình thì bản thứ hai đã ở đúng vị trí đó — không thấy điểm nối.
- **Không bao giờ đổi chữ giữa lúc đang chạy.** Mỗi giây bản tin chỉ được *đánh dấu là cũ*; nội dung mới chỉ được thay **đúng lúc vòng lặp quay vòng**, nơi mắt không nhìn thấy. Nếu thay ngay lúc có đáp án mới thì chữ sẽ nhảy giữa câu và không đọc được. Riêng **đổi ngôn ngữ** và **reset** thì thay ngay, vì chờ tới vòng sau có thể mất gần một phút.
- Tốc độ chạy cố định **~85 px/giây** bất kể dài ngắn, nên nhịp đọc luôn như nhau.

**Ô cờ bên trái kiêm luôn báo trạng thái đồng bộ.** Trên màn presenter, badge online/offline ở góc dưới phải **đã được bỏ** — nó nói đúng cùng một thứ với ô cờ, để hai cái trên một màn LED là thừa. Ô cờ giờ hiển thị:

| Trạng thái | Ô cờ |
|---|---|
| Online | 🔴 đỏ · **TRỰC TIẾP / LIVE** · *{n} người chơi* (điểm sáng nháy) |
| Offline | 🟠 hổ phách · **NGOẠI TUYẾN / OFFLINE** · *chỉ máy này* (điểm sáng ngừng nháy) |
| Đang kết nối | ⚪ xám · **ĐANG KẾT NỐI / CONNECTING** |

> Màu **phải** đổi theo trạng thái: một ô cờ đỏ ghi "TRỰC TIẾP" trong khi thực tế đang chạy offline sẽ nói với cả phòng điều ngược lại sự thật.

> **Màn player cũng đã bỏ badge.** Trên điện thoại không có góc nào trống thật sự — badge nổi đè lên dải thông tin vị trí ở đáy màn hình. Trạng thái kết nối giờ là một **chấm tròn 6px trên ô trạng thái** ở góc trên bên phải (xanh = đã đồng bộ, hổ phách = ngoại tuyến, xám = đang kết nối). Chỉ còn **màn admin và trang chủ** giữ badge ở góc.

> **Câu hỏi và đáp án không nằm trong ô cuộn cố định.** Đã từng thử ghim màn hình đúng một khung hình và cho riêng thẻ câu hỏi cuộn bên trong — dải vị trí luôn thấy được, nhưng trên iPhone thật thì câu dài phải kéo trong một ô hẹp và đáp án cuối bị cắt ngang chữ. Giờ **cả trang dài ra và cuộn như một khối**, nên mọi câu hỏi và cả bốn đáp án đều đọc trọn vẹn. Với những câu dài nhất, dải vị trí nằm dưới màn hình một chút — đánh đổi đúng, vì thứ người chơi đang nhìn khi đồng hồ chạy là đáp án.

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
