# Bài tập: Pipeline xử lý đơn hàng theo ngày (Order Processing Pipeline)

## 1. Mục tiêu

Xây một pipeline ETL hoàn chỉnh, chạy bằng dòng lệnh, xử lý dữ liệu đơn hàng
trong một ngày cụ thể, đối chiếu với log sự kiện thanh toán/vận chuyển, và
xuất ra báo cáo tổng hợp sạch cùng báo cáo các bản ghi lỗi.

Bài này buộc bạn phải:
- Dùng **generator** để đọc file log theo từng dòng (không load hết vào bộ nhớ).
- **Merge** dữ liệu từ 2 nguồn khác nhau (CSV có cấu trúc + log bán cấu trúc)
  dựa trên khóa chung `order_id`.
- Áp dụng **rule xử lý trạng thái** dựa trên chuỗi sự kiện theo thời gian —
  đây là dạng logic rất hay gặp trong data engineering thực tế (event sourcing).

## 2. Input files (đính kèm sẵn)

### `data/orders_2024-01-15.csv`

Danh sách đơn hàng trong ngày, có cột:
`order_id,customer_id,product_name,quantity,unit_price,order_date,payment_method`

File này **cố tình chứa lỗi**: thiếu giá trị, sai kiểu dữ liệu, số âm, sai định
dạng ngày, trùng `order_id`, khoảng trắng thừa quanh giá trị, và có cả một
dòng thuộc ngày khác (`2024-01-16`).

### `data/events_2024-01-15.log`

Log sự kiện dạng bán cấu trúc, mỗi dòng có dạng gần giống:

```
2024-01-15 08:02:11 INFO order_id=1001 event=PAYMENT_SUCCESS amount=300000
2024-01-15 08:10:02 ERROR order_id=1004 event=PAYMENT_FAILED reason=card_declined
```

Các `event` có thể gặp: `PAYMENT_SUCCESS`, `PAYMENT_FAILED`, `PAYMENT_RETRY`,
`SHIPPED`, `DELIVERED`, `ORDER_CANCELLED`.

File này **cố tình chứa**: dòng comment bắt đầu bằng `#`, dòng cảnh báo không
đúng cấu trúc sự kiện, dòng thiếu `order_id`, một dòng hoàn toàn không có
timestamp, và một `order_id` (`9999`) không hề tồn tại trong file CSV.

## 3. Yêu cầu chi tiết

### 3.1. Cấu trúc thư mục đề xuất

```
bt1/
├── data/
│   ├── orders_2024-01-15.csv
│   └── events_2024-01-15.log
├── output/
│   ├── dev/
│   └── prod/
├── logs/
├── extract.py
├── transform.py
├── load.py
└── main.py
```

Bạn không bắt buộc theo đúng tên file này, miễn là pipeline chạy được qua
một entry point duy nhất (ví dụ `main.py`).

### 3.2. EXTRACT

- Viết hàm đọc file CSV đơn hàng, trả về từng dòng dưới dạng `dict` (dùng
  `csv.DictReader`).
- Viết hàm đọc file log, **bắt buộc dùng `generator` (yield)** — mỗi lần
  `yield` một dict đã parse được từ 1 dòng log hợp lệ, ví dụ:
  `{"order_id": "1001", "event": "PAYMENT_SUCCESS", "timestamp": "...", ...}`.
  Dòng không đúng cấu trúc (comment, thiếu order_id, sai định dạng) thì bỏ
  qua — nhưng phải đếm được có bao nhiêu dòng bị bỏ qua.
- Gợi ý: dùng `regex` để trích `order_id=...`, `event=...` và các field tùy
  chọn (`reason=...`, `amount=...`, `carrier=...`) từ mỗi dòng log.

### 3.3. TRANSFORM

Phần này là trọng tâm bài tập. Bạn cần xử lý **theo đúng thứ tự** sau:

**Bước 1 — Validate & làm sạch từng đơn hàng từ CSV**, loại bỏ (và ghi lại lý
do) các trường hợp:
- `customer_id` rỗng
- `quantity` không parse được thành số nguyên dương (rỗng, chữ, số âm, số 0)
- `unit_price` không parse được thành số dương (rỗng, không phải số)
- `order_date` không đúng định dạng `YYYY-MM-DD`
- `order_id` bị trùng (giữ bản ghi xuất hiện đầu tiên, loại các bản ghi trùng
  sau đó)
- `order_date` khác với giá trị `--date` truyền vào khi chạy chương trình
  (không tính là "lỗi", nhưng phải bị loại khỏi tập dữ liệu xử lý — và bạn
  phải log riêng số lượng này)

Với các field có khoảng trắng thừa (`" C021 "`, `" 2 "`), bạn phải tự làm
sạch (`strip()`) chứ không được loại bỏ — đây không phải lỗi, là dữ liệu bẩn
cần chuẩn hóa.

**Bước 2 — Merge với dữ liệu log** theo `order_id`. Với mỗi đơn hàng hợp lệ,
xác định `final_status` theo đúng rule ưu tiên sau (áp dụng theo thứ tự, dừng
ở rule đầu tiên khớp):

1. Nếu có sự kiện `DELIVERED` → `"delivered"`
2. Nếu có sự kiện `SHIPPED` (và không có `DELIVERED`) → `"shipped"`
3. Nếu có sự kiện `ORDER_CANCELLED` → `"cancelled"`
4. Nếu sự kiện `PAYMENT_FAILED` gần nhất xảy ra **sau** sự kiện
   `PAYMENT_SUCCESS` gần nhất (hoặc không có `PAYMENT_SUCCESS` nào) →
   `"cancelled"`
5. Nếu có ít nhất một `PAYMENT_SUCCESS` (và không rơi vào rule 4) →
   `"confirmed"`
6. Nếu đơn hàng không có bất kỳ sự kiện log nào khớp `order_id` →
   `"pending"`

(Đơn hàng `1004` trong dữ liệu mẫu được thiết kế riêng để test rule 4/5: có
`PAYMENT_FAILED` → `PAYMENT_RETRY` → `PAYMENT_SUCCESS`, tức thanh toán lại
thành công — bạn phải xử lý đúng thứ tự thời gian, không chỉ dựa vào "có tồn
tại event nào đó".)

**Bước 3 — Tính toán**: với mỗi đơn hàng hợp lệ, tính
`total_amount = quantity * unit_price` (dùng dữ liệu từ CSV, không dùng
`amount` trong log — log chỉ dùng để xác định `final_status`).

### 3.4. LOAD

- Ghi tập đơn hàng hợp lệ đã transform ra file **JSONL**, mỗi dòng 1 object
  gồm đúng các field: `order_id, customer_id, product_name, quantity,
  unit_price, total_amount, order_date, final_status`.
- Ghi tập bản ghi **bị loại ở bước validate CSV** (không tính các bản ghi bị
  loại do `date_mismatch`) ra file **CSV** riêng, gồm cột: `order_id, reason`.
  Nếu `order_id` gốc cũng lỗi/rỗng, dùng số thứ tự dòng trong file CSV thay
  thế.
- File output phải nằm trong `output/dev/` hoặc `output/prod/` tùy vào
  `--env` được truyền vào.

### 3.5. Logging

Dùng module `logging` (không dùng `print`). Log tối thiểu các mốc sau, có
timestamp:
- Pipeline bắt đầu, kèm `date` và `env` được truyền vào.
- Số lượng đơn hàng đọc được từ CSV.
- Số lượng dòng log hợp lệ / không hợp lệ đọc được từ file log.
- Số lượng đơn hàng bị loại ở bước validate, và số lượng bị loại do lệch
  ngày (`date_mismatch`) — **tách riêng hai con số này**.
- Số lượng đơn hàng transform thành công.
- Kết quả ghi file: đường dẫn và số dòng đã ghi cho cả 2 file output.
- Pipeline hoàn tất.

Khi `--env dev`: log thêm chi tiết breakdown lý do bị loại (bao nhiêu bị loại
vì `invalid_quantity`, bao nhiêu vì `invalid_price`, v.v. — dùng level
`DEBUG`).
Khi `--env prod`: chỉ log các mốc chính ở level `INFO`, không log chi tiết
breakdown.

### 3.6. Argparse

Bắt buộc có:
- `--date` (bắt buộc, không có default) — ví dụ `2024-01-15`
- `--env` (không bắt buộc, `default="dev"`, `choices=["dev", "prod"]`)

Pipeline phải dùng `--date` để: (a) chọn đúng file input theo tên
(`orders_<date>.csv`, `events_<date>.log`), và (b) lọc đơn hàng như mô tả ở
mục 3.3.

## 4. Expected Output

Sau khi chạy `python main.py --date 2024-01-15 --env dev`, bạn kỳ vọng có:

- `output/dev/orders_processed_2024-01-15.jsonl` — khoảng 16-17 dòng (tùy
  cách bạn xử lý rule ưu tiên trạng thái), mỗi dòng là 1 JSON object hợp lệ.
- `output/dev/orders_errors_2024-01-15.csv` — chứa các `order_id` bị loại do
  lỗi dữ liệu (không tính lệch ngày), kèm lý do.
- `logs/pipeline_2024-01-15.log` (hoặc log ra console, tùy bạn) thể hiện đầy
  đủ các mốc ở mục 3.5.

Gợi ý tự kiểm chứng: đơn `1001` phải có `final_status = "delivered"`, đơn
`1004` phải có `final_status = "confirmed"`, đơn `1013` và `1018` phải có
`final_status = "cancelled"`, đơn `1014` (quantity không hợp lệ) không được
xuất hiện trong output hợp lệ, đơn `1008` không được xuất hiện ở đâu cả (khác
ngày, không tính là lỗi).

## 5. Tiêu chí kiểm tra (tự chấm trước khi nộp)

- [ ] Pipeline chạy được bằng đúng 1 lệnh, không lỗi runtime.
- [ ] `--date` là bắt buộc; thiếu thì chương trình báo lỗi rõ ràng qua
      argparse (không phải traceback khó hiểu).
- [ ] `--env` nhận đúng 2 giá trị, sai giá trị thì argparse tự chặn.
- [ ] Đọc log file dùng generator thật sự (có `yield`), không đọc hết bằng
      `readlines()` rồi xử lý list.
- [ ] Có ít nhất 5 loại lỗi dữ liệu khác nhau được phát hiện và log riêng lý
      do (không gộp chung một câu "lỗi dữ liệu").
- [ ] `order_id` trùng chỉ giữ lại 1 bản ghi.
- [ ] Trạng thái `final_status` đúng với rule ưu tiên, đặc biệt xử lý đúng
      case `1004` (retry thành công).
- [ ] `total_amount` được tính từ CSV, không lấy nhầm từ `amount` trong log.
- [ ] Output JSONL và CSV lỗi đúng schema đã mô tả.
- [ ] Log thể hiện đủ các mốc bắt buộc, và có khác biệt rõ giữa `dev`/`prod`.
- [ ] Không dùng pandas, SQL, database, decorator, OOP nâng cao.

