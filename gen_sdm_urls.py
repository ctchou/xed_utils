#!/usr/bin/env python3

import re
import json
import sqlite3
from pathlib import Path
from argparse import ArgumentParser
from urllib.request import urlopen
from typing import Dict, List, Optional

INST_DB = sqlite3.Connection

this_dir = Path(__file__).resolve().parent
default_json = str(this_dir / 'sdm_urls.json')

sdm_url_prefix = 'https://www.felixcloutier.com/x86/'

def input_sqlite_db(db_file: str) -> INST_DB:
    with sqlite3.connect(db_file) as db:
        db.row_factory = sqlite3.Row
        return db

def collect_iclasses(db: INST_DB) -> List[str]:
    sql_query = 'SELECT DISTINCT iclass from Instructions;'
    insts = db.execute(sql_query)
    return [ inst['iclass'] for inst in insts ]

cond_codes = '(o|no|b|nb|z|nz|be|nbe|s|ns|p|np|l|nl|le|nle)'

re_jcc = re.compile(f'^j{cond_codes}$')
re_setcc = re.compile(f'^set{cond_codes}$')
re_cmovcc = re.compile(f'^cmov{cond_codes}$')

re_lock = re.compile(r'^(?P<stem>.+)_lock$')
re_rep = re.compile(r'^(rep|repe|repne)_(?P<stem>.+)$')

def sdm_url_exists(name: str) -> bool:
    sdm_url = sdm_url_prefix + name
    print(f'Checking: {sdm_url}')
    try:
        urlopen(sdm_url)
    except Exception:
        return False
    else:
        return True

def get_sdm_name(iclass: str) -> Optional[str]:
    iclass = iclass.lower()
    if re_jcc.match(iclass):
        return 'jcc'
    if re_setcc.match(iclass):
        return 'setcc'
    if re_cmovcc.match(iclass):
        return 'cmovcc'
    m = re_lock.match(iclass)
    if m:
        iclass = m.group('stem')
    m = re_rep.match(iclass)
    if m:
        iclass = m.group('stem')
    if sdm_url_exists(iclass):
        return iclass
    if iclass.startswith('v'):
        iclass = iclass[1:]
        if sdm_url_exists(iclass):
            return iclass
    return None

def collect_sdm_urls(iclasses: List[str]) -> Dict[str, str]:
    sdm_urls = dict()
    for iclass in iclasses:
        name = get_sdm_name(iclass)
        if name:
            sdm_urls[iclass] = sdm_url_prefix + name
    return sdm_urls

def main() -> None:
    parser = ArgumentParser(description=f'Generate the mapping from iclasses to instruction reference URLs in {sdm_url_prefix}')
    parser.add_argument('sqlite', type=str, help='input SQLite database extracted from a XED build')
    parser.add_argument('--json', default=default_json, help=f'output JSON file (default: {default_json})')
    args = parser.parse_args()
    db = input_sqlite_db(args.sqlite)
    iclasses = collect_iclasses(db)
    sdm_urls = collect_sdm_urls(iclasses)
    with open(args.json, 'w') as json_fp:
        json.dump(sdm_urls, json_fp, indent=4)

if __name__ == '__main__':
    main()
