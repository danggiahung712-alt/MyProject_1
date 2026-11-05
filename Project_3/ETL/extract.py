import argparse
import json
import csv 

def parse_arg():
    parser = argparse.ArgumentParser(description="Order Processing Pipline")
    parser.add_argument('--date',require=True,help='YYYY-MM-DD format')
    parser.add_argument('--env', default ='dev',choices=['dev','prod'],help='Enviroment (dev/prod)')

def read_csvfile(fp):
    with open(fp,encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            yield {k: (v.strip() if v else v) for k,v in row.items()}

def read_jsonlfile(fp):
    with open(fp,encoding='utf-8') as f:
        for line in f:
            if line.strip():
                yield json.load(line)