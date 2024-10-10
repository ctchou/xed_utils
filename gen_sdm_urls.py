#!/usr/bin/env python3

import re
import json
import sqlite3
from pathlib import Path
from argparse import ArgumentParser
from urllib.request import urlopen
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Dict, List, Optional

sdm_root_url = 'https://www.felixcloutier.com/x86/'

re_href = re.compile(r"<a href='/x86/([^']+)'>")

def collect_sdm_dict() -> Dict[str, str:]:
    with urlopen(sdm_root_url) as sdm_root:
        charsets = sdm_root.info().get_charsets()
        sdm_top = sdm_root.read().decode(charsets[0])
        matches = re_href.findall(sdm_top)
        sdm_dict = dict()
        for match in matches:
            for name in match.split(':'):
                sdm_dict[name] = match
        return sdm_dict

sql_query = 'SELECT DISTINCT iclass from Instructions;'

def collect_iclasses(db_file: str) -> List[str]:
    with sqlite3.connect(db_file) as db:
        db.row_factory = sqlite3.Row
        insts = db.execute(sql_query)
        return [ inst['iclass'] for inst in insts ]

cond_codes = '(o|no|b|nb|z|nz|be|nbe|s|ns|p|np|l|nl|le|nle)'

re_jcc = re.compile(f'^j{cond_codes}$')
re_setcc = re.compile(f'^set{cond_codes}$')
re_cmovcc = re.compile(f'^cmov{cond_codes}$')

re_lock = re.compile(r'^(?P<stem>.+)_lock$')
re_rep = re.compile(r'^(rep|repe|repne)_(?P<stem>.+)$')

def get_sdm_name(iclass: str, sdm_dict: Dict[str, str]) -> Optional[str]:
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
    return sdm_dict.get(iclass, None)

def collect_sdm_urls(iclasses: List[str], sdm_dict: Dict[str, str]) -> Dict[str, str]:
    sdm_urls = dict()
    cur_time = datetime.now(ZoneInfo('US/Pacific'))
    sdm_urls['_COMMENT'] = f'generated at {cur_time}'
    for iclass in iclasses:
        name = get_sdm_name(iclass, sdm_dict)
        if name:
            sdm_urls[iclass] = sdm_root_url + name
    return sdm_urls

this_dir = Path(__file__).resolve().parent
default_json = str(this_dir / 'sdm_urls.json')

def main() -> None:
    parser = ArgumentParser(description=f'Generate the mapping from iclasses to instruction reference URLs in {sdm_root_url}')
    parser.add_argument('sqlite', type=str, help='input SQLite database extracted from a XED build')
    parser.add_argument('--json', default=default_json, help=f'output JSON file (default: {default_json})')
    args = parser.parse_args()
    sdm_dict = collect_sdm_dict()
    iclasses = collect_iclasses(args.sqlite)
    sdm_urls = collect_sdm_urls(iclasses, sdm_dict)
    with open(args.json, 'w') as json_fp:
        json.dump(sdm_urls, json_fp, indent=4)

if __name__ == '__main__':
    main()
