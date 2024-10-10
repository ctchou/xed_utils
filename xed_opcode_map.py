#!/usr/bin/env python3

import sqlite3
from argparse import ArgumentParser
from typing import List, Optional

INST_DB = sqlite3.Connection

def sql_query(map_id: int, opcode: int, iclass: Optional[str] = None) -> str:
    if iclass:
        iclass_cond = f'iclass = {iclass}'
        more_attrs = ', space, pp'
    else:
        iclass_cond = 'TRUE'
        more_attrs = ''
    return f'''
        SELECT DISTINCT iclass {more_attrs}
        FROM Instructions
        WHERE map == {map_id}
        AND ( opcode_int == {opcode} OR
              (partial_opcode == 1 AND {opcode} BETWEEN opcode_int AND opcode_int + 7) )
        AND {iclass_cond};
'''

# def pprint_inst(inst: sqlite3.Row) -> str:
#     iclass = inst['iclass']
#     space = inst['space'].upper()
#     pp = inst['pp'].replace(' ', '/')
#     return f'{iclass} {space}:{pp}'

def collect_insts(db: INST_DB, map_id: int, opcode: int) -> List[str]:
    insts = db.execute(sql_query(map_id, opcode))
    iclasses = [ inst['iclass'] for inst in insts ]
    return iclasses

def html_cell(db: INST_DB, map_id: int, row_id: int, col_id: int) -> str:
    opc_int = 16 * row_id + col_id
    opc_hex = f'{opc_int:02X}'
    opc_insts = '<br>\n&emsp;'.join(collect_insts(db, map_id, opc_int))
    return f'''
<td>
<b style="font-size: 120%">{opc_hex}</b><br>
&emsp;{opc_insts}
</td>
'''

def html_row(db: INST_DB, map_id: int, row_id: int) -> str:
    all_cols = '\n'.join([ html_cell(db, map_id, row_id, col_id) for col_id in range(16) ])
    return f'''
<tr>
{all_cols}
</tr>
'''

def html_map(db: INST_DB, map_id: int) -> str:
    all_rows = '\n'.join([ html_row(db, map_id, row_id) for row_id in range(16) ])
    return f'''
<button class="collapsible">Map {map_id}</button>
<div class="content">
<br>
<table style="width:100%">
{all_rows}
</table>
<br>
</div>
'''

def html_final(db: INST_DB) -> str:
    all_maps = '\n'.join([ html_map(db, map_id) for map_id in range(8) ])
    return f'''
<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>

.collapsible {{
  background-color: #777;
  color: white;
  cursor: pointer;
  padding: 18px;
  width: 100%;
  border: none;
  text-align: center;
  outline: none;
  font-weight: bold;
  font-size: 24px;
}}

.active, .collapsible:hover {{
  background-color: #555;
}}

.collapsible:after {{
  content: '\\002B';
  color: white;
  font-weight: bold;
  float: right;
  margin-left: 5px;
}}

.active:after {{
  content: "\\2212";
}}

.content {{
  padding: 0 18px;
  max-height: 0;
  overflow: hidden;
  transition: max-height 0.2s ease-out;
}}

table, tr, td {{
  border:1px solid black;
  text-align: left;
  vertical-align: text-top;
}}

</style>
</head>
<body>

<h1 style="text-align: center">
x86 opcode map
</h1>

<button class="collapsible">Legend</button>
<div class="content">
  <p>Legend here</p>
</div>

{all_maps}

<script>
var coll = document.getElementsByClassName("collapsible");
var i;
for (i = 0; i < coll.length; i++) {{
  coll[i].addEventListener("click", function() {{
    this.classList.toggle("active");
    var content = this.nextElementSibling;
    if (content.style.maxHeight){{
      content.style.maxHeight = null;
    }} else {{
      content.style.maxHeight = content.scrollHeight + "px";
    }} 
  }});
}}
</script>

</body>
</html>
'''

def input_sqlite_db(db_file: str) -> INST_DB:
    with sqlite3.connect(db_file) as db:
        db.row_factory = sqlite3.Row
        return db

def output_opcode_map(db: INST_DB, out_file: str) -> None:
    with open(out_file, 'w') as out_fp:
        out_fp.write(html_final(db))

def main() -> None:
    parser = ArgumentParser(description='Make HTML opcopde map from SQLite database extracted from a XED build')
    parser.add_argument('sqlite', type=str, help='input SQLite database')
    parser.add_argument('html', type=str, help='output HTML opcode map')
    args = parser.parse_args()
    db = input_sqlite_db(args.sqlite)
    output_opcode_map(db, args.html)

if __name__ == '__main__':
    main()
