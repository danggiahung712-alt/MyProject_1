from extract import read_csvfile, read_logfile, parse_log_lines
import re

def validate_csvfile(rows, target_date=None):
    valid_order = []
    error_records = []
    seen_id = set()
    
    for idx, raw_row in enumerate(rows, start=1):
        # Làm sạch (strip) các khoảng trắng thừa cho tất cả thuộc tính dạng chuỗi
        row = {k: (v.strip() if isinstance(v, str) else v) for k, v in raw_row.items()}
        
        raw_order_id = row.get('order_id')
        order_id = raw_order_id if (raw_order_id and raw_order_id != '') else str(idx)
        quantity = row.get('quantity')
        unit_price = row.get('unit_price')  
        order_date = row.get('order_date') 
        customer_id = row.get('customer_id')
        reason = None  

        if not customer_id:
            reason = 'missing_customer_id'
        elif not quantity or not quantity.isdigit() or int(quantity) <= 0:
            reason = 'invalid_quantity'
        else:
            try:
                if not unit_price or float(unit_price) <= 0:
                    reason = 'invalid_unit_price'
            except ValueError:
                reason = 'invalid_unit_price'
        
        if not reason:
            if not order_date or re.fullmatch(r'\d{4}-\d{2}-\d{2}', order_date) is None:
                reason = 'invalid_order_date'
            elif target_date and order_date != target_date:
                reason = 'date_mismatch'

        if reason:
            error_records.append({'order_id': order_id, 'reason': reason})
            continue

        if order_id not in seen_id:
            seen_id.add(order_id)
            valid_order.append(row)
        else:
            reason = 'duplicate_order_id'
            error_records.append({'order_id': order_id, 'reason': reason})

    return valid_order, error_records 

def group_by_order_id(records):
    events_by_order = {}
    for record in records:
        order_id = record.get('order_id')
        if order_id not in events_by_order:
            events_by_order[order_id] = []
        events_by_order[order_id].append(record)
    return events_by_order

def merge_logfile(events):
    event_per_order = [e.get('event') for e in events]
    if 'DELIVERED' in event_per_order:
        return 'delivered'
    elif 'SHIPPED' in event_per_order:
        return 'shipped'
    elif 'ORDER_CANCELLED' in event_per_order:
        return 'cancelled'
    else:
        fail_events = [e for e in events if e.get('event') == 'PAYMENT_FAILED']
        success_events = [e for e in events if e.get('event') == 'PAYMENT_SUCCESS']

        fail_timestamps = [e.get('timestamp') for e in fail_events if e.get('timestamp')]
        success_timestamps = [e.get('timestamp') for e in success_events if e.get('timestamp')]
        
        if fail_timestamps and (not success_timestamps or max(fail_timestamps) > max(success_timestamps)):
            return 'cancelled'
        elif success_timestamps:
            return 'confirmed'
        else:
            return 'pending'

def cal_order(valid_order):
    for line in valid_order:
        line['total_amount'] = float(line.get('quantity')) * float(line.get('unit_price'))
    return valid_order

if __name__ == '__main__':
    valid_order, error_record = validate_csvfile(read_csvfile('data/orders_2024-01-15.csv'), '2024-01-15')
    print("Valid:", valid_order)
    print("Errors:", error_record)
    cal_order(valid_order)
    print("Calculated:", valid_order)

    event_by_order = group_by_order_id(parse_log_lines(read_logfile('data/events_2024-01-15.log')))
    for order in valid_order:
        oid = order['order_id']
        events = event_by_order.get(oid, [])
        order['final_status'] = merge_logfile(events)
        print(order)
