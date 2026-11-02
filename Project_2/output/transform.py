import re

# Validate và làm sạch từng đơn hàng đọc từ CSV
# Trả về (danh sách đơn hợp lệ, danh sách bản ghi lỗi kèm lý do)
def validate_csvfile(rows, date):
    valid_order = []
    error_records = []
    seen_id = []
    for row in rows:
        order_id   = row.get('order_id')
        quantity   = row.get('quantity', '')
        unit_price = row.get('unit_price', '')
        order_date = row.get('order_date', '')
        reason = None

        if not row.get('customer_id', '').strip():
            reason = 'missing_customer_id'

        # Kiểm tra quantity phải là số nguyên dương (không rỗng, không âm, không bằng 0)
        elif not quantity or not quantity.isdigit() or int(quantity) <= 0:
            reason = 'invalid_quantity'

        elif not unit_price:
            reason = 'invalid_unit_price'
        else:
            try:
                val = float(unit_price)
                if val <= 0:
                    reason = 'invalid_unit_price'
            except ValueError:
                reason = 'invalid_unit_price'

        # Kiểm tra định dạng ngày đúng YYYY-MM-DD
        if reason is None and re.fullmatch(r'\d{4}-\d{2}-\d{2}', order_date) is None:
            reason = 'invalid_order_date'

        if reason:
            error_records.append({'order_id': order_id, 'reason': reason})
            continue

        # Lọc đơn thuộc ngày khác (date_mismatch) — không tính là lỗi, log riêng
        if order_date != date:
            error_records.append({'order_id': order_id, 'reason': 'date_mismatch'})
            continue

        # Loại đơn trùng order_id — chỉ giữ bản ghi xuất hiện đầu tiên
        if order_id not in seen_id:
            seen_id.append(order_id)
            valid_order.append(row)
        else:
            error_records.append({'order_id': order_id, 'reason': 'duplicate_order_id'})

    return valid_order, error_records


# Nhóm danh sách sự kiện log theo order_id để tra cứu nhanh
# Trả về dict: {order_id: [danh sách event dict]}
def group_by_order_id(records):
    events_by_order = {}
    for record in records:
        order_id = record.get('order_id')
        if order_id not in events_by_order:
            events_by_order[order_id] = []
        events_by_order[order_id].append(record)
    return events_by_order


# Xác định final_status của đơn hàng dựa trên danh sách sự kiện log theo rule ưu tiên
# Rule: DELIVERED > SHIPPED > ORDER_CANCELLED > PAYMENT logic > pending
def merge_logfile(events):
    event_per_order = [e.get('event') for e in events]

    # Rule 1: có DELIVERED → delivered
    if 'DELIVERED' in event_per_order:
        return 'delivered'

    # Rule 2: có SHIPPED (và không có DELIVERED) → shipped
    elif 'SHIPPED' in event_per_order:
        return 'shipped'

    # Rule 3: có ORDER_CANCELLED → cancelled
    elif 'ORDER_CANCELLED' in event_per_order:
        return 'cancelled'

    else:
        fail_events    = [e for e in events if e.get('event') == 'PAYMENT_FAILED']
        success_events = [e for e in events if e.get('event') == 'PAYMENT_SUCCESS']

        fail_timestamp    = [e.get('timestamp') for e in fail_events]
        success_timestamp = [e.get('timestamp') for e in success_events]

        # Rule 4: PAYMENT_FAILED gần nhất xảy ra SAU PAYMENT_SUCCESS gần nhất → cancelled
        if fail_timestamp and (not success_timestamp or max(fail_timestamp) > max(success_timestamp)):
            return 'cancelled'

        # Rule 5: có ít nhất một PAYMENT_SUCCESS (và không rơi vào rule 4) → confirmed
        elif success_timestamp:
            return 'confirmed'

        # Rule 6: không có bất kỳ sự kiện nào khớp → pending
        else:
            return 'pending'


# Tính total_amount = quantity * unit_price cho từng đơn hàng hợp lệ
def cal_order(valid_order):
    for line in valid_order:
        line['total_amount'] = float(line.get('quantity')) * float(line.get('unit_price'))
