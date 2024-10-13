#!/usr/bin/env python3

import json
import sqlite3
from pathlib import Path
from argparse import ArgumentParser

def html_template(all_maps_html: str) -> str:
    return f'''
<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, Initial-scale=1">
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

/* The Modal (background) */
.modal {{
  display: none; /* Hidden by default */
  position: fixed; /* Stay in place */
  z-index: 1; /* Sit on top */
  padding-top: 100px; /* Location of the box */
  left: 0;
  top: 0;
  width: 100%; /* Full width */
  height: 100%; /* Full height */
  overflow: auto; /* Enable scroll if needed */
  background-color: rgb(0,0,0); /* Fallback color */
  background-color: rgba(0,0,0,0.4); /* Black w/ opacity */
}}

/* Modal Content */
.modal-content {{
  background-color: #fefefe;
  margin: auto;
  padding: 20px;
  border: 1px solid #888;
  width: 80%;
}}

/* The Close Button */
.close {{
  color: #aaaaaa;
  float: right;
  font-size: 28px;
  font-weight: bold;
}}

.close:hover,
.close:focus {{
  color: #000;
  text-decoration: none;
  cursor: pointer;
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

{all_maps_html}

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

Iclass = str
IclassDesc = list[sqlite3.Row]
OpcodeMapCell = dict[Iclass, IclassDesc]
OneOpcodeMap = list[OpcodeMapCell]
AllOpcodeMaps = list[OneOpcodeMap]
EmptyMaps = list[bool]
SdmUrls = dict[Iclass, str]

max_num_maps = 11

def html_cell(sdm_urls: SdmUrls, all_maps: AllOpcodeMaps, map_id: int, opcode: int) -> str:
    opcode_hex = f'{opcode:02X}'
    iclasses = sorted(all_maps[map_id][opcode].keys())
    insts = []
    for iclass in iclasses:
        url = sdm_urls.get(iclass, None)
        if url:
            insts.append(f'<div>&emsp;{iclass} <sup><a href="{url}" target="_blank">*</a></sup></div>')
        else:
            insts.append(f'<div>&emsp;{iclass}</div>')
    insts_html = '\n'.join(insts)
    return f'''
<td>
<b style="font-size: 120%">{opcode_hex}</b>
{insts_html}
</td>
'''

def html_row(sdm_urls: SdmUrls, all_maps: AllOpcodeMaps, map_id: int, row_id: int) -> str:
    all_cols_html = '\n'.join([ html_cell(sdm_urls, all_maps, map_id, 16 * row_id + col_id) for col_id in range(16) ])
    return f'''
<tr>
{all_cols_html}
</tr>
'''

def html_one_map(sdm_urls: SdmUrls, all_maps: AllOpcodeMaps, map_id: int) -> str:
    all_rows_html = '\n'.join([ html_row(sdm_urls, all_maps, map_id, row_id) for row_id in range(16) ])
    return f'''
<button class="collapsible">Map {map_id}</button>
<div class="content">
<br>
<table style="width:100%">
{all_rows_html}
</table>
<br>
</div>
'''

def html_all_maps(sdm_urls: SdmUrls, all_maps: AllOpcodeMaps, empty_maps: EmptyMaps) -> str:
    all_maps_html = '\n'.join([ html_one_map(sdm_urls, all_maps, map_id)
                               for map_id in range(max_num_maps) if not empty_maps[map_id] ])
    return html_template(all_maps_html)

def input_sdm_urls(sdm_urls_json) -> SdmUrls:
    with open(sdm_urls_json, 'r') as sdm_urls_json_fp:
        return json.load(sdm_urls_json_fp)

sql_query = '''
    SELECT DISTINCT * from Instructions
    order by map, opcode_int, iclass;
'''

def input_sqlite_db(db_file: str) -> sqlite3.Cursor:
    with sqlite3.connect(db_file) as db:
        db.row_factory = sqlite3.Row
        insts = db.execute(sql_query)
        return insts

def collect_all_maps(db: sqlite3.Cursor) -> tuple[AllOpcodeMaps, EmptyMaps]:
    all_maps = [ [ dict([]) for opcode in range(256) ] for map_id in range(max_num_maps) ]
    empty_maps = [ True for map_id in range(max_num_maps) ]
    for inst in db:
        map_id = inst['map']
        empty_maps[map_id] = False
        opcode = inst['opcode_int']
        iclass = inst['iclass']
        if inst['partial_opcode']:
            for i in range(8):
                iclass_desc = all_maps[map_id][opcode + i].get(iclass, [])
                iclass_desc.append(inst)
                all_maps[map_id][opcode + i][iclass] = iclass_desc
        else:
            iclass_desc = all_maps[map_id][opcode].get(iclass, [])
            iclass_desc.append(inst)
            all_maps[map_id][opcode][iclass] = iclass_desc
    return (all_maps, empty_maps)

def output_all_maps(sdm_urls: SdmUrls, all_maps: AllOpcodeMaps, empty_maps: EmptyMaps, out_file: str) -> None:
    with open(out_file, 'w') as out_fp:
        out_fp.write(html_all_maps(sdm_urls, all_maps, empty_maps))

this_dir = Path(__file__).resolve().parent
default_sdm_urls_json = str(this_dir / 'sdm_urls.json')

def main() -> None:
    parser = ArgumentParser(description='Make HTML opcopde map from SQLite database extracted from a XED build')
    parser.add_argument('xed_sqlite', type=str, help='input SQLite database extracted from a XED build')
    parser.add_argument('opcmap_html', type=str, help='output HTML opcode map')
    parser.add_argument('--sdm-urls-json', default=default_sdm_urls_json,
                        help=f'input JSON file containing SDM instruction reference URLs (default: {default_sdm_urls_json})')
    args = parser.parse_args()
    sdm_urls = input_sdm_urls(args.sdm_urls_json)
    xed_db = input_sqlite_db(args.xed_sqlite)
    all_maps, empty_maps = collect_all_maps(xed_db)
    output_all_maps(sdm_urls, all_maps, empty_maps, args.opcmap_html)

if __name__ == '__main__':
    main()
