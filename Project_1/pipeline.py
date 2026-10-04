import argparse
import logging
import csv
def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date",required = True)
    parser.add_argument("--env",default="dev",choices=["dev","prod"])
    return parser.parse_args()

def read_file(fp):
    with open('fp',encoding='utf-8') as d:
        for line in d:
            yield d

def read_csvfile(fp):
    with open('fp',encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            yield row

def parse_log_line(lines):
    for line in lines:
        line = line.strip().split(maxsplit=3) 
        if len(line) < 4:
            continue
        yield {'timestamp':f'{line[0]} {line[1]}',
               'level': line[2],
               'message': line[3]}

def filter_error(lines):
    for line in lines:
        if line['level'] in ('ERROR','CRITICAL'):
            yield line
    
def calculate(rows):
    revenue = 0
    for row in rows:
        if row.get('status') != 'completed' or not row['amount']:
            continue
        revenue += rows['amount']
    return revenue

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


