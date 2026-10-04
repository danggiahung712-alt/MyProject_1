import csv
import argparse
import logging
import re

def parse_arg():
    parser = argparse.ArgumentParser()
    parser.add_argument('--date',required = True)
    parser.add_argument('--env',default = 'dev',choices = ['dev','prod'])
    return parser.parse_args()

def read_logfile(fp):
    with open(fp,encoding='utf-8') as f:
        for line in f:
            yield line

def parse_log_lines(lines):
    sum_invalidvalue=0
    for line in lines:
        core = re.search(r'order_id=(?P<order_id>\d+).*?event=(?P<event>\w+)',line)
        if core is None:
            sum_invalidvalue += 1
            continue
        event_data = re.findall(r'(\w+)=(\S+)',line)
        record = dict(event_data)
        timestamp_match = re.search(r'\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2}',line)
        if timestamp_match is None:
            sum_invalidvalue  += 1 
            continue
        record['timestamp']=timestamp_match.group()
        yield record
        
def read_csvfile(fp):
    with open(fp,encoding='utf-8') as f:
        rows=csv.DictReader(f)
        for row in rows:
            yield row
for record in parse_log_lines(read_logfile('data/events_2024-01-15.log')):
    print(record)
for row in read_csvfile('data/orders_2024-01-15.csv'):
    print(row)


        
