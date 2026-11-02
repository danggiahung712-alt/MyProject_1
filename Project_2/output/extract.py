import csv
import argparse
import re

# Phân tích tham số dòng lệnh (--date bắt buộc, --env mặc định là 'dev')
def parse_arg():
    parser = argparse.ArgumentParser(description="Order Processing Pipeline")
    parser.add_argument('--date', required=True, help="Date in YYYY-MM-DD format")
    parser.add_argument('--env', default='dev', choices=['dev', 'prod'], help="Environment (dev/prod)")
    return parser.parse_args()

# Đọc từng dòng từ file log theo kiểu generator (không load hết vào bộ nhớ)
def read_logfile(fp):
    with open(fp, encoding='utf-8') as f:
        for line in f:
            yield line

# Phân tích từng dòng log hợp lệ thành dict, bỏ qua dòng lỗi/comment
# Trả về (generator các record hợp lệ, số dòng bị bỏ qua)
def parse_log_lines(lines):
    skipped = 0
    for line in lines:
        line_str = line.strip()

        # Bỏ qua dòng trống hoặc comment bắt đầu bằng #
        if not line_str or line_str.startswith('#'):
            skipped += 1
            continue

        # Kiểm tra có order_id và event không — dòng thiếu 2 trường này sẽ bị bỏ qua
        core = re.search(r'order_id=(?P<order_id>\d+).*?event=(?P<event>\w+)', line_str)
        if core is None:
            skipped += 1
            continue

        # Kiểm tra timestamp hợp lệ định dạng YYYY-MM-DD HH:MM:SS
        timestamp_match = re.search(r'\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2}', line_str)
        if timestamp_match is None:
            skipped += 1
            continue

        record = {
            'order_id': core.group('order_id'),
            'event':    core.group('event'),
            'timestamp': timestamp_match.group(),
        }


        yield record, skipped
        skipped = 0  # reset sau mỗi record hợp lệ (chỉ tích lũy giữa các record)

# Đọc từng dòng file CSV đơn hàng, strip khoảng trắng thừa ở mỗi field
def read_csvfile(fp):
    with open(fp, encoding='utf-8') as f:
        rows = csv.DictReader(f)
        for row in rows:
            yield {k: (v.strip() if v else v) for k, v in row.items()}
