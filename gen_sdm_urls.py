#!/usr/bin/env python3

import re
import json
import sqlite3
from pathlib import Path
from argparse import ArgumentParser
from urllib.request import urlopen
from datetime import date
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

sql_query = '''
    SELECT DISTINCT iclass from Instructions;
'''

def collect_iclasses(db_file: str) -> List[str]:
    with sqlite3.connect(db_file) as db:
        db.row_factory = sqlite3.Row
        insts = db.execute(sql_query)
        return [ inst['iclass'] for inst in insts ]

cond_codes = '(o|no|b|nb|z|nz|be|nbe|s|ns|p|np|l|nl|le|nle)'
re_jcc = re.compile(f'^j{cond_codes}$')
re_setcc = re.compile(f'^set{cond_codes}$')
re_cmovcc = re.compile(f'^cmov{cond_codes}$')
re_fcmovcc = re.compile(r'^fcmov(b|nb|be|nbe|e|ne|u|nu)$')

re_prefix_1 = re.compile(r'^(?P<stem>vpshld|vpshldv|vpshrd|vpshrdv).$')
re_prefix_any = re.compile(r'^(?P<stem>pmovsx|pmovzx|vbroadcast|vmaskmov|vpmaskmov|vpopcnt).*$')
re_strip_prefix = re.compile(r'^(rep|repe|repne)_(?P<stem>.+)$')
re_strip_suffix = re.compile(r'^(?P<stem>.+)_(lock|near|far|xmm|sse4)$')
re_strip_64 = re.compile(r'^(?P<stem>fxsave|fxrstor|pcmpestri|pcmpestrm|pcmpistri|sysret|xrstor|xrstors|xsave|xsavec|xsaveopt|xsaves)64$')

misc_dict = {
    'int': 'intn:into:int3:int1',
    'jcxz': 'jcc',
    'jecxz': 'jcc',
    'jrcxz': 'jcc',
    'loope': 'loop:loopcc',
    'loopne': 'loop:loopcc',
    'mov_cr': 'mov-1',
    'mov_dr': 'mov-2',
    'prefetcht0': 'prefetchh',
    'prefetcht1': 'prefetchh',
    'prefetcht2': 'prefetchh',
    'prefetchnta': 'prefetchh',
    'scasq': 'scas:scasb:scasw:scasd',
    'ud0': 'ud',
    'ud1': 'ud',
    'ud2': 'ud',
}

def get_sdm_name(iclass: str, sdm_dict: Dict[str, str]) -> Optional[str]:
    iclass = iclass.lower()

    if re_jcc.match(iclass):
        return 'jcc'
    if re_setcc.match(iclass):
        return 'setcc'
    if re_cmovcc.match(iclass):
        return 'cmovcc'
    if re_fcmovcc.match(iclass):
        return 'fcmovcc'
    m = re_prefix_1.match(iclass)
    if m:
        return m.group('stem')
    m = re_prefix_any.match(iclass)
    if m:
        return m.group('stem')
    m = re_strip_prefix.match(iclass)
    if m:
        iclass = m.group('stem')
    m = re_strip_suffix.match(iclass)
    if m:
        iclass = m.group('stem')
    m = re_strip_64.match(iclass)
    if m:
        iclass = m.group('stem')
    name = misc_dict.get(iclass, None)
    if name:
        return name
    name = sdm_dict.get(iclass, None)
    if name:
        return name
    if iclass.startswith('v'):
        return sdm_dict.get(iclass[1:], None)
    return None

def collect_sdm_urls(iclasses: List[str], sdm_dict: Dict[str, str]) -> Dict[str, str]:
    sdm_urls = dict()
    cur_date = date.today()
    sdm_urls['_COMMENT'] = f'generated on {cur_date}'
    missing = []
    for iclass in iclasses:
        name = get_sdm_name(iclass, sdm_dict)
        if name:
            sdm_urls[iclass] = sdm_root_url + name
        else:
            missing.append(iclass)
    print('Missing iclasses:')
    for iclass in sorted(missing):
        print(iclass)
    return sdm_urls

this_dir = Path(__file__).resolve().parent
default_sdm_urls_json = str(this_dir / 'sdm_urls.json')

def main() -> None:
    parser = ArgumentParser(description=f'Generate the mapping from iclasses to SDM instruction reference URLs in {sdm_root_url}')
    parser.add_argument('sqlite', type=str, help='input SQLite database extracted from a XED build')
    parser.add_argument('--sdm-urls-json', default=default_sdm_urls_json, help=f'output JSON file (default: {default_sdm_urls_json})')
    args = parser.parse_args()
    sdm_dict = collect_sdm_dict()
    iclasses = collect_iclasses(args.sqlite)
    sdm_urls = collect_sdm_urls(iclasses, sdm_dict)
    with open(args.sdm_urls_json, 'w') as sdm_urls_json_fp:
        json.dump(sdm_urls, sdm_urls_json_fp, indent=4)

if __name__ == '__main__':
    main()
