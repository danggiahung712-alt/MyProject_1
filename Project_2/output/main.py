from extract import parse_arg, read_logfile, parse_log_lines, read_csvfile
from transform import validate_csvfile, group_by_order_id, merge_logfile, cal_order
from load import write_jsonlfile, get_output_dir, write_error
import logging

args = parse_arg()
log_level = logging.DEBUG if args.env == 'dev' else logging.INFO
logging.basicConfig(level=log_level, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)
logger.info(f"Pipeline bắt đầu, date={args.date}, env={args.env}")

# Step 1: Đọc và Validate CSV đơn hàng
rows = read_csvfile(f'data/orders_{args.date}.csv')
rows = list(rows)
logger.info(f"Đọc được {len(rows)} đơn hàng từ CSV")

valid_order, error_record = validate_csvfile(rows, args.date)

date_mismatch_count = sum(1 for err in error_record if err.get('reason') == 'date_mismatch')
data_error_records = [err for err in error_record if err.get('reason') != 'date_mismatch']

logger.info(f"Số đơn bị loại do lỗi dữ liệu: {len(data_error_records)}")
logger.info(f"Số đơn bị loại do lệch ngày: {date_mismatch_count}")
logger.info(f"Số đơn hợp lệ sau validate: {len(valid_order)}")

# Khi --env dev: Log thêm chi tiết phân loại các lý do bị loại ở level DEBUG
if args.env == 'dev':
    reason_counts = {}
    for err in data_error_records:
        r = err.get('reason')
        reason_counts[r] = reason_counts.get(r, 0) + 1
    logger.debug(f"Chi tiết phân loại lý do bị loại: {reason_counts}")

# Step 2: Đọc và Validate Log sự kiện (dùng generator)
valid_log_count = 0
invalid_log_count = 0
parsed_log_records = []

try:
    for raw_line in read_logfile(f'data/events_{args.date}.log'):
        parsed = list(parse_log_lines([raw_line]))
        if parsed:
            parsed_log_records.append(parsed[0])
            valid_log_count += 1
        else:
            invalid_log_count += 1
    logger.info(f"Số lượng dòng log hợp lệ: {valid_log_count}, không hợp lệ (bỏ qua): {invalid_log_count}")
except FileNotFoundError:
    logger.warning(f"Không tìm thấy file events cho ngày {args.date}")

# Step 3: Transform & Merge dữ liệu
cal_order(valid_order)

event_by_order = group_by_order_id(parsed_log_records)
for order in valid_order:
    oid = order.get('order_id')
    events = event_by_order.get(oid, [])
    order['final_status'] = merge_logfile(events)

logger.info(f"Transform hoàn tất: {len(valid_order)} đơn đã có final_status và total_amount")

# Step 4: Ghi kết quả ra File
output_dir = get_output_dir(args.env)
jsonl_path = f"{output_dir}orders_processed_{args.date}.jsonl"
csv_path = f"{output_dir}orders_errors_{args.date}.csv"

write_jsonlfile(jsonl_path, valid_order)
logger.info(f"Đã ghi {len(valid_order)} dòng vào {jsonl_path}")

write_error(csv_path, error_record)
clean_errors_count = len([e for e in error_record if e.get('reason') != 'date_mismatch'])
logger.info(f"Đã ghi {clean_errors_count} dòng lỗi vào {csv_path}")

logger.info("Pipeline hoàn tất")


