import json
import csv
import os

# Ghi danh sách đơn hàng hợp lệ ra file JSONL (mỗi dòng 1 JSON object)
# Trả về số dòng đã ghi để log ở main.py
def write_jsonlfile(fp, valid_order):
    count = 0
    with open(fp, 'w', encoding='utf-8') as f:
        for line in valid_order:
            record = {
                'order_id':     line.get('order_id'),
                'customer_id':  line.get('customer_id'),
                'product_name': line.get('product_name'),
                'quantity':     int(line.get('quantity')),
                'unit_price':   float(line.get('unit_price')),
                'total_amount': line.get('total_amount'),
                'order_date':   line.get('order_date'),
                'final_status': line.get('final_status'),
            }
            f.write(json.dumps(record, ensure_ascii=False) + '\n')
            count += 1
    return count


# Xác định và tạo thư mục output theo môi trường (dev/prod)
def get_output_dir(env):
    base_dir   = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(base_dir, '..', 'output', env)
    os.makedirs(output_dir, exist_ok=True)
    return output_dir + os.sep


# Ghi các bản ghi lỗi dữ liệu ra file CSV (loại bỏ date_mismatch vì không phải lỗi)
# Trả về số dòng đã ghi để log ở main.py
def write_error(fp, error_record):
    clean_errors = [e for e in error_record if e.get('reason') != 'date_mismatch']
    with open(fp, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['order_id', 'reason'])
        writer.writeheader()
        writer.writerows(clean_errors)
    return len(clean_errors)