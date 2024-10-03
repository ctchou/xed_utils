#!/usr/bin/env python3

from argparse import (ArgumentParser, Namespace)
import sys
import re
import inspect
import csv
import json
import sqlite3
from pathlib import Path

def input_xed_dgen(dgen: str, pysrc: str, mbuild: str):
    sys.path.append(pysrc)
    sys.path.append(mbuild)
    import gen_setup
    args = Namespace(prefix=dgen)
    gen_setup.make_paths(args)
    xed_db = gen_setup.read_db(args)
    return xed_db

def remove_extra_spaces(s: str) -> str:
    return ' '.join(s.split())

def compute_opcode_hex(opcode_int: int) -> str:
    assert isinstance(opcode_int, int) and 0 <= opcode_int <= 255
    return f'{opcode_int:02X}'

def compute_pp(rec) -> str:
    pp = []
    if rec.no_prefixes_allowed:
        assert not (rec.osz_required or rec.f2_required or rec.f3_required)
        pp.append('NP')
    else:
        if rec.osz_required:
            pp.append('66')
        if rec.f2_required:
            pp.append('F2')
        if rec.f3_required:
            pp.append('F3')
    assert rec.space == 'legacy' or len(pp) == 1
    return ' '.join(pp)

def fix_xed_db(xed_db):
    for rec in xed_db.recs:
        rec.pattern = remove_extra_spaces(rec.pattern)
        rec.operands = remove_extra_spaces(rec.operands)
        rec.opcode_int = rec.opcode_base10
        del rec.opcode_base10
        rec.opcode_hex = compute_opcode_hex(rec.opcode_int)
        rec.pp = compute_pp(rec)

    print(f'[INFO] number of instrunction defs: {len(xed_db.recs)}')
    return xed_db

def output_csv(xed_db):
    pass

def output_json(xed_db):
    pass

def output_sqlite(xed_db):
    pass

default_root = Path(__file__).resolve().parent.parent
default_dgen = str(default_root / 'build/obj/dgen')
default_pysrc = str(default_root / 'xed/pysrc')
default_mbuild = str(default_root / 'mbuild')

def process_args() -> Namespace:
    parser = ArgumentParser(description='Extract a database from a XED build')
    parser.add_argument('--dgen', default=default_dgen, help=f'the dgen directory of a XED build (default: {default_dgen})')
    parser.add_argument('--pysrc', default=default_pysrc, help=f'pathname of xed/pysrc (default: {default_pysrc})')
    parser.add_argument('--mbuild', default=default_mbuild, help=f'pathname of mbuild (default: {default_mbuild})')
    parser.add_argument('-c', '--csv', type=str, help='output CSV file')
    parser.add_argument('-j', '--json', type=str, help='output JSON file')
    parser.add_argument('-s', '--sqlite', type=str, help='output SQLite database')
    args = parser.parse_args()
    # args.__dict__['prefix'] = args.__dict__.pop('dgen')
    if args.csv:
        assert Path(args.csv).suffix == '.csv'
    if args.json:
        assert Path(args.json).suffix == '.json'
    if args.sqlite:
        assert Path(args.sqlite).suffix == '.db'
    return args

def main() -> None:
    args = process_args()
    xed_db = input_xed_dgen(args.dgen, args.pysrc, args.mbuild)
    xed_db = fix_xed_db(xed_db)
    if args.csv:
        output_csv(xed_db)
    if args.json:
        output_json(xed_db)
    if args.sqlite:
        output_sqlite(xed_db)

if __name__ == '__main__':
    main()
