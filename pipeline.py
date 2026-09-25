import argparse
import logging
import csv
def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date",required = True)
    parser.add_argument("--env",default="dev",choices=["dev","prod"])
    return parser.parse_args()

def read_file(fp):
    with open(fp,encoding='utf-8') as f:
        for line in f:
            yield line

def read_csvfile(fp):
    with open(fp,encoding='utf-8') as f:
        row = csv.DictReader(f)
        for line in row:
            yield line

def parse_log_line(lines):
    for line in lines:
        part=line.strip().split(maxsplit=3)
        if len(part) < 4:
            continue
        yield {'timestamp':f'{part[0]} {part[1]}', 'level': part[2],'message':part[3]}

def filter_error(lines):
    for r in lines:
        if r['level'] in ('ERROR','CRITICAL'):
            yield r

def calculate(rows):
    sum_rev = 0
    for row in rows:
        if row.get('status') != 'completed':
            continue
        try: 
            sum_rev += float(row['amount'])
        except (ValueError,TypeError):
            continue
    return sum_rev

def link_file(*generator):
    for gen in generator:
        yield from gen

if __name__ == '__main__':
    args = parse_args()
    logging.basicConfig(level=logging.INFO,format='%(asctime)s [%(levelname)s] %(message)s')
    logger = logging.getLogger(__name__)
    logger.info("Job bắt đầu cho ngày %s,môi trường %s",args.date,args.env)

    log_records = parse_log_line(read_file('access_sample.log'))
    errors = list(filter_error(log_records))
    logger.info("Tìm thấy %d dòng lỗi: " ,len(errors))

    sales_rows = read_csvfile('sales_sample.csv')
    revenue = calculate(sales_rows)
    logger.info("Tổng doanh thu completed: %s",revenue)
    
    with open('pip.csv','w',encoding='utf-8') as f:
        rows = csv.DictWriter(f,fieldnames=['Date','env','error_count','TotalRevenue'])
        rows.writeheader()
        rows.writerow({
            'Date' : args.date,
            'env'  : args.env,
            'error_count' : len(errors),
            'TotalRevenue' : revenue,
        })


