from extract import read_csvfile, read_logfile, parse_log_lines
import re
def validate_csvfile(rows):
    valid_order = []
    error_records = []
    seen_id = []
    for row in rows:
        order_id = row.get('order_id')
        quantity = row.get('quantity')
        unit_price = row.get('unit_price')  
        order_date = row.get('order_date') 
        reason = None  

        if row.get('customer_id') is None:
            reason = 'missing_customer_id'
        
        elif not quantity or not quantity.isdigit() or int(quantity) <= 0:
            reason = 'invalid_quantity'
        
        elif not unit_price or not unit_price.isdigit():
            reason = 'invalid_unit_price'
        
        elif re.fullmatch(r'\d{4}-\d{2}-\d{2}',order_date) is None:
            reason = 'invalid_order_date'

        if reason:
            error_records.append({'order_id':order_id,'reason':reason})
            continue
        if order_id not in seen_id:
            seen_id.append(order_id)
            valid_order.append(row)
        else:
            reason = 'duplicate_order_id'
    return valid_order,error_records 

def group_by_order_id(records):
    events_by_order={}
    for record in records:
        order_id = record.get('order_id')
        if order_id not in events_by_order:
            events_by_order[order_id]=[]
            events_by_order[order_id].append(record)
        else:
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
        fail_events = [e for e in events if e.get('event')=='PAYMENT_FAILED']
        success_events = [e for e in events if e.get('event')=='ORDER_CANCELLED']

        fail_timestamp = [e.get('timestamp') for e in fail_events]
        success_timestamp = [e.get('timestamp') for e in success_events]
        
        if fail_timestamp and (not success_timestamp or max(fail_timestamp) > max(success_timestamp)):
            return 'cancelled'
        elif success_timestamp:
            return 'confirmed'
        else:
            return 'pending'

def cal_order(valid_order):
    for line in valid_order:
        line['total_amount']=float(line.get('quantity')) * float(line.get('unit_price'))
        return valid_order

valid_order,error_record = validate_csvfile(read_csvfile('data/orders_2024-01-15.csv'))
print(valid_order)
print(error_record)
cal_order(valid_order)
print(valid_order)

event_by_order = group_by_order_id(parse_log_lines(read_logfile('data/events_2024-01-15.log')))
for order in valid_order:
    oid = order['order_id']
    events = event_by_order.get(oid, [])
    order['final_status'] = merge_logfile(events)
    print(order)