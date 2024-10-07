#!/usr/bin/env python3

import sys
import csv
import json
import sqlite3
from pathlib import Path
from argparse import ArgumentParser, Namespace
from typing import Any, List, Tuple

XED_DB = Any
INST_REC = Any
XED_DATA = Any

def input_xed_db(dgen: str, pysrc: str) -> XED_DB:
    sys.path.append(pysrc)
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

def compute_pp(rec: INST_REC) -> str:
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
    return pp

def attr_excluded(attr: str) -> bool:
    return attr in ['get_eosz_list'] or attr.startswith('__')


def fix_xed_db(xed_db: XED_DB) -> Tuple[XED_DB, List[str]]:
    inst_attrs = set([])
    for rec in xed_db.recs:
        rec.opcode_int = rec.opcode_base10
        rec.opcode_hex = compute_opcode_hex(rec.opcode_int)
        del rec.opcode_base10
        rec.pp = compute_pp(rec)
        rec.eosz_list = rec.get_eosz_list()
        rec.pattern = remove_extra_spaces(rec.pattern)
        rec.operands = remove_extra_spaces(rec.operands)
        assert ' '.join(rec.operand_list) == rec.operands
        del rec.operand_list
        del rec.parsed_operands
        if hasattr(rec, 'attributes'):
            rec.attributes = rec.attributes.split()
        else:
            rec.attributes = []
        if hasattr(rec, 'flags'):
            rec.flags = remove_extra_spaces(rec.flags)
        rec.cpuid_fields = [ str(r) for g in rec.cpuid_groups for r in g.get_records() ]
        del rec.cpuid_groups
        for attr in dir(rec):
            if not attr_excluded(attr):
                inst_attrs.add(attr)
                val = getattr(rec, attr)
    inst_attrs = sorted(list(inst_attrs))
    print(f'[INFO] number of instrunction defs: {len(xed_db.recs)}')
    print(f'[INFO] instruction attributes: {inst_attrs}')
    return (xed_db, inst_attrs)

def convert_xed_db(xed_db: XED_DB, inst_attrs: List[str]) -> XED_DATA:
    inst_list = []
    for rec in xed_db.recs:
        inst = {}
        for attr in inst_attrs:
            inst[attr] = getattr(rec, attr, None)
        inst_list.append(inst)
    xed_data = {'Instructions': inst_list}
    return xed_data

def output_csv(xed_data: XED_DATA) -> None:
    pass

def output_json(xed_data: XED_DATA, json_file: str) -> None:
    with open(json_file, 'w') as json_fp:
        json.dump(xed_data, json_fp, sort_keys=True, indent=4)

def output_sqlite(xed_data: XED_DATA) -> None:
    pass

default_root = Path(__file__).resolve().parent.parent
default_dgen = str(default_root / 'build/obj/dgen')
default_pysrc = str(default_root / 'xed/pysrc')

def process_args() -> Namespace:
    parser = ArgumentParser(description='Extract a database from a XED build')
    parser.add_argument('--dgen', default=default_dgen, help=f'the dgen directory of a XED build (default: {default_dgen})')
    parser.add_argument('--pysrc', default=default_pysrc, help=f'pathname of xed/pysrc (default: {default_pysrc})')
    parser.add_argument('-c', '--csv', type=str, help='output CSV file')
    parser.add_argument('-j', '--json', type=str, help='output JSON file')
    parser.add_argument('-s', '--sqlite', type=str, help='output SQLite database')
    args = parser.parse_args()
    if args.csv:
        assert Path(args.csv).suffix == '.csv'
    if args.json:
        assert Path(args.json).suffix == '.json'
    if args.sqlite:
        assert Path(args.sqlite).suffix == '.db'
    return args

def main() -> None:
    args = process_args()
    xed_db = input_xed_db(args.dgen, args.pysrc)
    (xed_db, inst_attrs) = fix_xed_db(xed_db)
    xed_data = convert_xed_db(xed_db, inst_attrs)
    if args.csv:
        output_csv(xed_data)
    if args.json:
        output_json(xed_data, args.json)
    if args.sqlite:
        output_sqlite(xed_data)

if __name__ == '__main__':
    main()
