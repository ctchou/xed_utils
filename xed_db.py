#!/usr/bin/env python3

import sys
import csv
import json
import sqlite3
from pathlib import Path
from argparse import ArgumentParser, Namespace
from typing import Any, List, Tuple, Dict, Optional

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

def str_of_list(xs: List[Any]) -> str:
    return ' '.join([ str(x) for x in xs ])

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
    return str_of_list(pp)

def compute_eosz_list(rec: INST_REC) -> str:
    eosz_list = rec.get_eosz_list()
    if eosz_list:
        return str_of_list(eosz_list)
    else:
        return None

def attr_excluded(attr: str) -> bool:
    return attr in ['get_eosz_list'] or attr.startswith('__')

def fix_xed_db(xed_db: XED_DB) -> Tuple[XED_DB, List[str]]:
    inst_attrs = set([])
    for rec in xed_db.recs:
        rec.opcode_int = rec.opcode_base10
        rec.opcode_hex = compute_opcode_hex(rec.opcode_int)
        del rec.opcode_base10
        assert rec.real_opcode == 'Y'
        del rec.real_opcode
        rec.pp = compute_pp(rec)
        rec.eosz_list = compute_eosz_list(rec)
        rec.pattern = remove_extra_spaces(rec.pattern)
        rec.operands = remove_extra_spaces(rec.operands)
        assert str_of_list(rec.operand_list) == rec.operands
        del rec.operand_list
        del rec.parsed_operands
        rec.explicit_operands = str_of_list(rec.explicit_operands)
        rec.implicit_operands = str_of_list(rec.implicit_operands)
        if hasattr(rec, 'attributes'):
            rec.attributes = remove_extra_spaces(rec.attributes)
        if hasattr(rec, 'flags'):
            rec.flags = remove_extra_spaces(rec.flags)
        if hasattr(rec, 'comment'):
            rec.comment = remove_extra_spaces(rec.comment).replace('"', "''")
        rec.cpuid_fields = str_of_list([ str(r) for g in rec.cpuid_groups for r in g.get_records() ])
        del rec.cpuid_groups
        for attr in dir(rec):
            if not attr_excluded(attr):
                inst_attrs.add(attr)
    inst_attrs = sorted(list(inst_attrs))
    print(f'[INFO] number of instrunction defs: {len(xed_db.recs)}')
    print(f'[INFO] instruction attributes: {inst_attrs}')
    return (xed_db, inst_attrs)

def convert_xed_db(xed_db: XED_DB, inst_attrs: List[str]) -> XED_DATA:
    inst_list = []
    for rec in xed_db.recs:
        inst = {}
        for attr in inst_attrs:
            val = getattr(rec, attr, None)
            assert val is None or isinstance(val, bool) or isinstance(val, int) or isinstance(val, str)
            inst[attr] = val
        inst_list.append(inst)
    xed_data = {'Instructions': inst_list}
    return xed_data

def output_json(xed_data: XED_DATA, json_file: str) -> None:
    with open(json_file, 'w') as json_fp:
        json.dump(xed_data, json_fp, sort_keys=True, indent=4)

def output_csv(xed_data: XED_DATA, inst_attrs: List[str], csv_file: str) -> None:
    with open(csv_file, 'w') as csv_fp:
        csv_writer = csv.DictWriter(csv_fp, fieldnames=inst_attrs)
        csv_writer.writeheader()
        for inst in xed_data['Instructions']:
            csv_writer.writerow(inst)

def sql_create(table: str, keys: List[str]) -> str:
    keys_list = ','.join(keys)
    return f'CREATE TABLE {table} ({keys_list})'

def sql_insert(table: str, keys: List[str], vals: List[Any]) -> str:
    keys_list = ','.join(keys)
    vals_list = ','.join(vals)
    return f'INSERT INTO {table} ({keys_list}) VALUES ({vals_list})'

def sql_insert_inst(inst: Dict[str, Optional[int | str]], inst_attrs: List[str]) -> str:
    inst_vals = []
    for attr in inst_attrs:
        val = inst[attr]
        if isinstance(val, int):
            inst_vals.append(str(val))
        elif isinstance(val, str):
            inst_vals.append('"' + val + '"')
        else:
            assert val is None
            inst_vals.append('NULL')
    return sql_insert('Instructions', inst_attrs, inst_vals)

def output_sqlite(xed_data: XED_DATA, inst_attrs: List[str], sqlite_file: str) -> None:
    sqlite_path = Path(sqlite_file)
    sqlite_path.unlink(missing_ok=True)
    with sqlite3.connect(sqlite_path) as sqlite_db:
        create_cmd = sql_create('Instructions', inst_attrs)
        sqlite_db.execute(create_cmd)
        for inst in xed_data['Instructions']:
            insert_cmd = sql_insert_inst(inst, inst_attrs)
            sqlite_db.execute(insert_cmd)

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
    if args.json:
        output_json(xed_data, args.json)
    if args.csv:
        output_csv(xed_data, inst_attrs, args.csv)
    if args.sqlite:
        output_sqlite(xed_data, inst_attrs, args.sqlite)

if __name__ == '__main__':
    main()
