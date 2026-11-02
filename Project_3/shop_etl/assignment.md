# Bài tập Level 2: Pipeline cửa hàng → SQL Server

## 1. Mục tiêu

Xây một pipeline ETL hoàn chỉnh, **kết thúc bằng việc nạp dữ liệu vào database SQL Server** thay vì ghi ra file như Project 1 và 2.

Phần Extract và Transform bạn đã làm quen ở Project 2 (generator, validate, join 2 nguồn), nên bài này cố tình để chúng **nhẹ hơn**. Điều mới và khó nằm ở bước **Load**:

- Kết nối database từ Python và gửi câu lệnh SQL an toàn (query có tham số).
- **Upsert**: dữ liệu danh mục sản phẩm đã có thì cập nhật, chưa có thì thêm.
- **Insert** dữ liệu giao dịch, không để bản ghi đã nạp từ lần chạy trước làm hỏng cả lô.
- **Transaction**: nhiều thao tác coi như một khối, lỗi giữa chừng thì **rollback** toàn bộ.
- Chạy lại cùng một ngày nhiều lần mà dữ liệu trong DB không bị nhân đôi.

## 2. Kiến thức mới cần tìm hiểu

Bài này cần những thứ bạn chưa học. Hãy tự đọc tài liệu hoặc hỏi mình khi vướng. Mình sẽ giải thích khái niệm, nhưng không viết sẵn lời giải.

| Chủ đề | Bạn cần biết |
|---|---|
| `pyodbc` | tạo kết nối, `cursor`, `execute`, `executemany`, `fetchone`/`fetchall`, `rowcount` |
| Query có tham số (`?`) | vì sao không được ghép chuỗi (f-string) vào câu SQL (nguy cơ SQL injection, lỗi kiểu dữ liệu) |
| Transaction | `commit`, `rollback`, và vì sao `pyodbc` mặc định không tự commit |
| `try` / `except` / `finally` | bạn chưa học phần này. Cần để bắt lỗi JSON hỏng và để rollback khi DB báo lỗi |
| Upsert trong T-SQL | hai cách: `UPDATE` rồi `INSERT` nếu `rowcount = 0`, hoặc `MERGE`. Chọn một |
| Lỗi ràng buộc của DB | PRIMARY KEY, FOREIGN KEY, CHECK, độ dài cột bị vi phạm thì Python nhận exception |
| `json.loads`, `JSONDecodeError` | đọc từng dòng JSONL và xử lý dòng hỏng |
| `sys.exit` | kết thúc chương trình với mã lỗi khác 0 |

## 3. Cấu trúc thư mục đề xuất

```
shop_etl/
├── data/                         # đính kèm sẵn
│   ├── products_2024-02-10.csv
│   ├── sales_2024-02-10.jsonl
│   ├── products_2024-02-11.csv
│   ├── sales_2024-02-11.jsonl
│   ├── products_2024-02-12.csv
│   └── sales_2024-02-12.jsonl
├── sql/
│   └── schema.sql                # bạn tự viết
├── output/
│   ├── dev/
│   └── prod/
├── logs/
├── db.py                         # hàm kết nối database
├── extract.py
├── transform.py
├── load.py
├── main.py
├── .gitignore
└── README.md
```

Tên file không bắt buộc, miễn là chạy được qua một entry point (`main.py`).

## 4. Input files (đính kèm sẵn)

Mỗi ngày có 2 file:

### `products_<date>.csv` — danh mục sản phẩm, dạng CSV

Cột: `product_id, product_name, category, unit_price, stock_qty`.

Đây là **bản chụp toàn bộ danh mục** đang bán vào ngày đó (không phải chỉ phần thay đổi). File ngày 10 cố tình chứa: tên rỗng, giá âm, giá không phải số, tồn kho không phải số, dòng có khoảng trắng thừa, `category` viết hoa thường lộn xộn, và một `product_id` xuất hiện hai lần.

### `sales_<date>.jsonl` — giao dịch bán hàng, dạng JSONL

Mỗi dòng là một object, ví dụ có các field: `sale_id`, `product_id`, `quantity`, `sold_at`, `customer` (**object lồng nhau** gồm `id`, `city`), `payment`.

File ngày 10 cố tình chứa: một dòng JSON bị cắt dở, một dòng trống, thiếu `product_id`, `quantity` bằng 0 hoặc âm, `quantity` ở dạng chuỗi số (`"3"`), `sold_at` sai định dạng, một giao dịch của ngày hôm trước, `sale_id` trùng, `product_id` không tồn tại, và một khách hàng không có `city`.

File ngày 11 và 12 dùng để test chạy tiếp theo ngày, cập nhật sản phẩm và rollback (xem mục 6).

## 5. Yêu cầu chi tiết

**Làm theo từng giai đoạn. Xong giai đoạn nào, gửi mình xem giai đoạn đó trước khi sang giai đoạn sau.**

### Giai đoạn 1: Database và kết nối

1. Tạo **hai database** trong SQL Server: `shop_dev` và `shop_prod`.
2. Tự viết `sql/schema.sql` tạo 3 bảng bên dưới, rồi chạy script đó trên **cả hai** database.
3. Viết hàm kết nối trong `db.py`. Không viết mật khẩu hay thông tin nhạy cảm trực tiếp trong code. Tên server lấy từ biến môi trường (có giá trị mặc định hợp lý). Chạy thử in ra "Kết nối OK".

**Bảng `products`**

| Cột | Kiểu | Ràng buộc |
|---|---|---|
| `product_id` | `NVARCHAR(10)` | PRIMARY KEY |
| `product_name` | `NVARCHAR(100)` | NOT NULL |
| `category` | `NVARCHAR(50)` | cho phép NULL |
| `unit_price` | `DECIMAL(12,2)` | NOT NULL, phải lớn hơn 0 |
| `stock_qty` | `INT` | NOT NULL, không âm |
| `last_loaded_date` | `DATE` | NOT NULL |

**Bảng `sales`**

| Cột | Kiểu | Ràng buộc |
|---|---|---|
| `sale_id` | `NVARCHAR(20)` | PRIMARY KEY |
| `product_id` | `NVARCHAR(10)` | NOT NULL, FOREIGN KEY tới `products` |
| `customer_id` | `NVARCHAR(20)` | cho phép NULL |
| `city` | `NVARCHAR(50)` | cho phép NULL |
| `quantity` | `INT` | NOT NULL, phải lớn hơn 0 |
| `unit_price` | `DECIMAL(12,2)` | NOT NULL (giá tại thời điểm bán) |
| `total_amount` | `DECIMAL(14,2)` | NOT NULL |
| `payment_method` | `NVARCHAR(20)` | cho phép NULL |
| `sold_at` | `DATETIME2(0)` | NOT NULL |
| `load_date` | `DATE` | NOT NULL (= `--date` của lần chạy) |

**Bảng `pipeline_runs`** (nhật ký chạy)

| Cột | Kiểu | Ràng buộc |
|---|---|---|
| `run_id` | `INT IDENTITY` | PRIMARY KEY |
| `run_date` | `DATE` | NOT NULL |
| `started_at` | `DATETIME2(0)` | NOT NULL |
| `finished_at` | `DATETIME2(0)` | NOT NULL |
| `status` | `NVARCHAR(10)` | NOT NULL |
| `products_upserted` | `INT` | NOT NULL |
| `sales_inserted` | `INT` | NOT NULL |
| `rejected_total` | `INT` | NOT NULL |

### Giai đoạn 2: Argparse và Extract

**Argparse**
- `--date` (bắt buộc), định dạng `YYYY-MM-DD`.
- `--env` (`default="dev"`, `choices=["dev", "prod"]`). Giá trị này quyết định: database nào được kết nối (`shop_dev` hay `shop_prod`) và thư mục `output/dev/` hay `output/prod/`.
- File input chọn theo `--date` (`products_<date>.csv`, `sales_<date>.jsonl`).

**Extract**
- Đọc `products_<date>.csv` từng dòng và **ghi nhận được số dòng trong file** (dòng tiêu đề là dòng 1).
- Đọc `sales_<date>.jsonl` **bằng generator, từng dòng một**. Dòng trống bỏ qua, không tính vào số đã đọc. Dòng JSON hỏng **không được làm chương trình crash**: pipeline phải ghi nhận dòng đó là lỗi `malformed_json` và đọc tiếp. Cách thiết kế (generator trả về cái gì cho dòng hỏng) do bạn tự quyết.
- Extract chỉ đọc và tách dữ liệu thô. Chưa quyết định đúng sai về nghiệp vụ.

### Giai đoạn 3: Transform

**3a. Products.** Làm sạch và validate theo đúng thứ tự ưu tiên này (gặp lỗi đầu tiên thì dừng, ghi lý do đó):

| # | Điều kiện | Lý do loại |
|---|---|---|
| 1 | `product_id` rỗng | `missing_product_id` |
| 2 | `product_name` rỗng | `missing_product_name` |
| 3 | `unit_price` không phải số lớn hơn 0 | `invalid_price` |
| 4 | `stock_qty` không phải số nguyên không âm | `invalid_stock` |

Làm sạch: bỏ khoảng trắng thừa ở mọi field, đổi `category` về chữ thường, đổi `unit_price` và `stock_qty` sang kiểu số.

Trùng `product_id` trong cùng file: **dòng xuất hiện sau thắng**. Các dòng trước bị thay thế được tính là `superseded` (đếm riêng, **không phải lỗi**, không ghi vào file rejects).

**3b. Sales.** Validate theo thứ tự ưu tiên:

| # | Điều kiện | Kết quả |
|---|---|---|
| 1 | Dòng JSON hỏng | lỗi `malformed_json` |
| 2 | `sale_id` thiếu hoặc rỗng | lỗi `missing_sale_id` |
| 3 | `product_id` thiếu hoặc rỗng | lỗi `missing_product_id` |
| 4 | `quantity` không phải số nguyên lớn hơn 0 (chấp nhận số hoặc chuỗi số như `"3"`) | lỗi `invalid_quantity` |
| 5 | `sold_at` sai định dạng `YYYY-MM-DDTHH:MM:SS` | lỗi `invalid_sold_at` |
| 6 | Ngày của `sold_at` khác `--date` | **không phải lỗi**: đếm riêng là `date_mismatch`, không ghi vào rejects |
| 7 | `product_id` không có trong products **hợp lệ của cùng ngày** | lỗi `unknown_product` |
| 8 | `sale_id` đã xuất hiện trước đó trong file | lỗi `duplicate_sale_id` (giữ dòng đầu) |

Với dòng hợp lệ, tạo bản ghi phẳng để nạp DB:
- Tách object lồng nhau `customer` thành `customer_id` và `city`. Nếu thiếu `city` thì để `None` (sẽ thành NULL trong DB).
- `unit_price` lấy từ danh mục sản phẩm của ngày đó.
- `total_amount = quantity * unit_price`.

**Lưu ý quan trọng:** đừng thêm kiểm tra độ dài `customer_id` vào Transform. Giao dịch cuối trong file ngày 12 cố tình hợp lệ với mọi rule ở trên, để **chỉ database mới từ chối nó**. Mục đích là để bạn test rollback ở giai đoạn 5.

### Giai đoạn 4: Load vào database

Toàn bộ việc ghi vào DB nằm trong **một transaction duy nhất**, theo thứ tự:

1. **Upsert products.** Sản phẩm đã có thì cập nhật `product_name`, `category`, `unit_price`, `stock_qty`, `last_loaded_date`. Chưa có thì thêm mới. Đếm riêng số `inserted` và số `updated`.
2. **Xác định các `sale_id` đã có sẵn trong DB** (từ lần chạy trước). Những giao dịch đó **bỏ qua**, đếm là `skipped_existing`. Không được để lỗi trùng khóa chính làm hỏng cả lô.
3. **Insert các giao dịch mới** vào `sales`.
4. **Ghi một dòng vào `pipeline_runs`** với `status = 'success'`.
5. **Commit.**

Quy tắc bắt buộc:
- **Mọi câu SQL có giá trị truyền vào phải dùng tham số `?`**. Không ghép chuỗi.
- Products phải được nạp **trước** sales (vì khóa ngoại).
- Nếu có **bất kỳ lỗi nào** trong khối này: **rollback toàn bộ** (products, sales và `pipeline_runs`), ghi log nội dung lỗi, kết thúc chương trình với mã lỗi khác 0. Không được nuốt lỗi âm thầm.
- Kết nối luôn được đóng, dù thành công hay thất bại.

**Ghi file rejects (Load thứ hai, giống Level 1):** ghi các bản ghi **bị loại do lỗi** (cả products và sales, không gồm `superseded` và `date_mismatch`) ra `output/<env>/rejects_<date>.csv` với các cột: `source` (`products` hoặc `sales`), `line_no`, `key` (`product_id` hoặc `sale_id`, để trống nếu không xác định được), `reason`.

### Giai đoạn 5: Logging và kiểm thử toàn diện

Dùng `logging` (không dùng `print`), có timestamp, ghi ra console và file `logs/pipeline_<date>.log`. Tối thiểu log các mốc:

- Pipeline bắt đầu, kèm `date` và `env`.
- Products: số dòng đọc, số bị loại do lỗi, số `superseded`, số hợp lệ.
- Sales: số dòng đọc, số bị loại do lỗi, số `date_mismatch`, số hợp lệ.
- Kết quả load: products `inserted`/`updated`, sales `inserted`/`skipped_existing`.
- `COMMIT` thành công, hoặc `ROLLBACK` kèm lý do.
- Pipeline kết thúc.

Khi `--env dev`: log thêm (level `DEBUG`) breakdown số lượng theo từng lý do bị loại. Khi `--env prod`: chỉ log các mốc chính ở level `INFO`.

Sau đó chạy lần lượt các kịch bản ở mục 6.

## 6. Expected Output

Các số dưới đây đã được kiểm tra trước với bộ dữ liệu đính kèm. Dùng chúng để tự đối chiếu.

**Lần 1: `python main.py --date 2024-02-10 --env dev` (DB còn trống)**

| | Kết quả |
|---|---|
| Products | đọc 16, loại 4 (`missing_product_name` 1, `invalid_price` 2, `invalid_stock` 1), `superseded` 1, hợp lệ 11 → `inserted` 11, `updated` 0 |
| Sales | đọc 20, loại 8 (`unknown_product` 2, `invalid_quantity` 2, `malformed_json` 1, `missing_product_id` 1, `duplicate_sale_id` 1, `invalid_sold_at` 1), `date_mismatch` 1, hợp lệ 11 → `inserted` 11 |
| File rejects | 12 dòng (4 products + 8 sales) |
| Trạng thái DB | `products` = 11 dòng, `sales` = 11 dòng, `pipeline_runs` = 1 dòng |

Gợi ý tự kiểm chứng trong DB: `S1004` có `total_amount = 1197000` (vì `P002` lấy dòng sau, giá 399000, không phải 420000). `S1016` có `city` là NULL. `S1006`, `S1019` không có trong bảng `sales`.

**Lần 2: chạy lại y hệt lần 1 (kiểm tra chạy lặp)**

| | Kết quả |
|---|---|
| Products | `inserted` 0, `updated` 11 |
| Sales | `inserted` 0, `skipped_existing` 11 |
| Trạng thái DB | `products` vẫn 11, `sales` vẫn 11 (**không bị nhân đôi**), `pipeline_runs` = 2 dòng |

**Lần 3: `--date 2024-02-11` (sản phẩm đổi giá, có sản phẩm mới)**

| | Kết quả |
|---|---|
| Products | đọc 14, loại 1 (`invalid_price`), hợp lệ 13 → `inserted` 2 (`P016`, `P017`), `updated` 11 |
| Sales | đọc 8, loại 2 (`unknown_product` 1, `invalid_quantity` 1), hợp lệ 6 → `inserted` 6 |
| Trạng thái DB | `products` = 13, `sales` = 17, `pipeline_runs` = 3. `P001` giá 330000, `P008` giá 299000 |

**Lần 4: `--date 2024-02-12` (kiểm thử rollback)**

Giao dịch `S3003` có `customer_id` dài hơn 20 ký tự, DB sẽ từ chối giữa chừng (sau khi `S3001`, `S3002` đã được insert trong transaction). Kỳ vọng:

- Chương trình log lỗi, rollback, kết thúc với mã lỗi khác 0.
- DB **y nguyên như sau lần 3**: `sales` vẫn 17, `P001` vẫn giá **330000** (không phải 340000), `pipeline_runs` vẫn 3 dòng.

**Lần 5 (tùy chọn): sửa tay `customer_id` của `S3003` cho ngắn lại (không quá 20 ký tự) rồi chạy lại `--date 2024-02-12`**

- Products: `inserted` 0, `updated` 13. Sales: `inserted` 5.
- `products` = 13, `sales` = 22, `pipeline_runs` = 4, `P001` giá 340000.

## 7. Tiêu chí kiểm tra (tự chấm trước khi nộp)

- [ ] Chạy được bằng một lệnh; thiếu `--date` hoặc sai `--env` thì argparse báo lỗi rõ ràng.
- [ ] `schema.sql` chạy được trên cả hai database, đúng kiểu cột và ràng buộc như mục 5.
- [ ] Không có mật khẩu hay thông tin nhạy cảm trong code hoặc trong Git.
- [ ] Đọc `sales` bằng generator thật sự (có `yield`), dòng JSON hỏng không làm crash.
- [ ] Transform xử lý đúng thứ tự ưu tiên lỗi; `superseded` và `date_mismatch` được đếm riêng, không bị gộp vào lỗi.
- [ ] Không có câu SQL nào ghép chuỗi giá trị bằng f-string hoặc `+`.
- [ ] Upsert products hoạt động đúng: lần chạy lặp không tạo dòng trùng, giá và tồn kho được cập nhật.
- [ ] Chạy lại cùng một ngày: số dòng trong `sales` không đổi.
- [ ] Toàn bộ ghi DB nằm trong một transaction; lần chạy thứ 4 rollback sạch (kiểm tra `P001` giữ giá cũ, `sales` không đổi).
- [ ] Sau lỗi DB: có log nguyên nhân, rollback xong, kết nối đóng, mã thoát khác 0.
- [ ] Log đủ các mốc ở giai đoạn 5; `dev` và `prod` khác nhau rõ ràng.
- [ ] File rejects đúng schema, không chứa `superseded` hay `date_mismatch`.
- [ ] Không dùng pandas, ORM (SQLAlchemy), decorator, Docker.

## 8. Thử thách thêm (không bắt buộc)

- Thêm cờ `--dry-run`: chạy hết quy trình nhưng **rollback ở cuối** thay vì commit.
- Khi load thất bại, vẫn ghi được một dòng `status = 'failed'` vào `pipeline_runs`. Gợi ý: dòng này phải nằm ngoài transaction vừa bị rollback.
- Thay vòng lặp từng dòng bằng `executemany` hoặc chia lô (batch).
- Tra các `sale_id` đã tồn tại bằng **một** câu truy vấn, không phải mỗi giao dịch một câu.
- Làm `schema.sql` chạy lại nhiều lần không lỗi (không lỗi khi bảng đã tồn tại).

## 9. Cách làm việc với mình

Giống hai bài trước: bạn tự code, gửi code (hoặc ảnh) theo từng giai đoạn. Mình sẽ không viết lại hộ. Mình sẽ soát logic, chỉ ra lỗi và giải thích tại sao sai, gợi ý hướng sửa, và đánh giá bạn đã tách Extract, Transform, Load đúng chưa. Chỉ khi bạn thực sự bí, mình mới đưa code sửa mẫu.

Làm xong bài này, bài tiếp theo (Level 3) sẽ đi sâu vào incremental load, chạy lặp an toàn có chủ đích (idempotency), batch loading và xử lý lỗi nâng cao.
