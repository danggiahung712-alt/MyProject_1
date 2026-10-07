import json
import csv
import os 

def write_jsonlfile(fp, valid_order):
    with open(fp, 'w', encoding='utf-8') as f:
        for line in valid_order:
            # Chuyển đổi sang đúng kiểu dữ liệu (số nguyên, số thực)
            record = {
                'order_id': line.get('order_id'),
                'customer_id': line.get('customer_id'),
                'product_name': line.get('product_name'),
                'quantity': int(line.get('quantity')),
                'unit_price': float(line.get('unit_price')),
                'total_amount': line.get('total_amount'),
                'order_date': line.get('order_date'),
                'final_status': line.get('final_status')
            }
            f.write(json.dumps(record, ensure_ascii=False) + '\n')


def get_output_dir(env):
    output_dir = f'output/{env}/'
    os.makedirs(output_dir, exist_ok=True)
    return output_dir

def write_error(fp, error_record):
    # Loại bỏ các bản ghi do date_mismatch ra khỏi file error CSV (theo mục 3.4)
    clean_errors = [e for e in error_record if e.get('reason') != 'date_mismatch']
    with open(fp, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['order_id', 'reason'])
        writer.writeheader()
        writer.writerows(clean_errors)


        