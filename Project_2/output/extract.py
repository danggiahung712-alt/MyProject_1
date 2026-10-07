import csv
import argparse
import re

def parse_arg():
    parser = argparse.ArgumentParser(description="Order Processing Pipeline")
    parser.add_argument('--date', required=True, help="Date in YYYY-MM-DD format")
    parser.add_argument('--env', default='dev', choices=['dev', 'prod'], help="Environment (dev/prod)")
    return parser.parse_args()

def read_logfile(fp):
    with open(fp, encoding='utf-8') as f:
        for line in f:
            yield line

def parse_log_lines(lines):
    for line in lines:
        line_str = line.strip()
        if not line_str or line_str.startswith('#'):
            continue
        core = re.search(r'order_id=(?P<order_id>\d+).*?event=(?P<event>\w+)', line_str)
        if core is None:
            continue
        event_data = re.findall(r'(\w+)=(\S+)', line_str)
        record = dict(event_data)
        timestamp_match = re.search(r'\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2}', line_str)
        if timestamp_match is None:
            continue
        record['timestamp'] = timestamp_match.group()
        yield record

def read_csvfile(fp):
    with open(fp, encoding='utf-8') as f:
        rows = csv.DictReader(f)
        for row in rows:
            yield row


