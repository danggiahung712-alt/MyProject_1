from extract import parse_arg, read_logfile, parse_log_lines, read_csvfile
from transform import validate_csvfile, group_by_order_id, merge_logfile, cal_order
from load import write_jsonlfile, get_output_dir, write_error
import logging
import os

# ── Cấu hình logging ────────────────────────────────────────────────────────
args = parse_arg()
log_level = logging.DEBUG if args.env == 'dev' else logging.INFO

# Tạo thư mục logs/ nếu chưa có, ghi log ra cả console lẫn file
base_dir = os.path.dirname(os.path.abspath(__file__))
logs_dir = os.path.join(base_dir, '..', 'logs')
os.makedirs(logs_dir, exist_ok=True)
log_file = os.path.join(logs_dir, f'pipeline_{args.date}.log')

logging.basicConfig(
    level=log_level,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(log_file, encoding='utf-8'),
    ]
)
logger = logging.getLogger(__name__)
logger.info(f"Pipeline bắt đầu, date={args.date}, env={args.env}")

# ── Step 1: Đọc CSV đơn hàng ────────────────────────────────────────────────
rows = list(read_csvfile(os.path.join(base_dir, '..', 'data', f'orders_{args.date}.csv')))
logger.info(f"Đọc được {len(rows)} đơn hàng từ CSV")

# Validate và làm sạch — trả về đơn hợp lệ và danh sách lỗi (gồm cả date_mismatch)
valid_order, error_record = validate_csvfile(rows, args.date)

date_mismatch_count = sum(1 for err in error_record if err.get('reason') == 'date_mismatch')
data_error_records  = [err for err in error_record if err.get('reason') != 'date_mismatch']

logger.info(f"Số đơn bị loại do lỗi dữ liệu: {len(data_error_records)}")
logger.info(f"Số đơn bị loại do lệch ngày (date_mismatch): {date_mismatch_count}")
logger.info(f"Số đơn hợp lệ sau validate: {len(valid_order)}")

# Khi --env dev: Log thêm chi tiết phân loại các lý do bị loại ở level DEBUG
if args.env == 'dev':
    reason_counts = {}
    for err in data_error_records:
        r = err.get('reason')
        reason_counts[r] = reason_counts.get(r, 0) + 1
    logger.debug(f"Chi tiết phân loại lý do bị loại: {reason_counts}")

# ── Step 2: Đọc file log sự kiện (dùng generator) ──────────────────────────
# parse_log_lines yield (record, skipped_count) — tích lũy skipped giữa 2 record liên tiếp
valid_log_count   = 0
invalid_log_count = 0
parsed_log_records = []

try:
    for result in parse_log_lines(read_logfile(os.path.join(base_dir, '..', 'data', f'events_{args.date}.log'))):
        record, skipped = result
        invalid_log_count += skipped
        parsed_log_records.append(record)
        valid_log_count += 1
    logger.info(f"Số dòng log hợp lệ: {valid_log_count}, không hợp lệ (bỏ qua): {invalid_log_count}")
except FileNotFoundError:
    logger.warning(f"Không tìm thấy file events cho ngày {args.date}")

# ── Step 3: Transform & Merge dữ liệu ──────────────────────────────────────
# Tính total_amount cho từng đơn hàng hợp lệ
cal_order(valid_order)

# Nhóm sự kiện log theo order_id, sau đó gán final_status cho từng đơn
event_by_order = group_by_order_id(parsed_log_records)
for order in valid_order:
    oid = order.get('order_id')
    events = event_by_order.get(oid, [])
    order['final_status'] = merge_logfile(events)

logger.info(f"Transform hoàn tất: {len(valid_order)} đơn đã có final_status và total_amount")

# ── Step 4: Ghi kết quả ra file ─────────────────────────────────────────────
output_dir = get_output_dir(args.env)
jsonl_path = os.path.join(output_dir, f'orders_processed_{args.date}.jsonl')
csv_path   = os.path.join(output_dir, f'orders_errors_{args.date}.csv')

# Ghi file JSONL đơn hàng hợp lệ và nhận lại số dòng đã ghi
jsonl_count = write_jsonlfile(jsonl_path, valid_order)
logger.info(f"Đã ghi {jsonl_count} dòng vào {jsonl_path}")

# Ghi file CSV lỗi và nhận lại số dòng đã ghi
csv_count = write_error(csv_path, error_record)
logger.info(f"Đã ghi {csv_count} dòng lỗi vào {csv_path}")

logger.info("Pipeline hoàn tất")
