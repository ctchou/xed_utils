
# xed_utils

--------------------------------

`xed_utils` provides several Python scripts for organizing and displaying
the x86 instruction encoding information contained in Intel&reg; XED:

https://intelxed.github.io

including an x86 opcode map generator.

## Requirements

The minimum requirement is Python 3.10 or above.
But if you want to build XED as well, you will also need a C compiler.

## Installation

Check out the following git repos:

* https://github.com/ctchou/xed_utils.git

* https://github.com/intelxed/xed

* https://github.com/intelxed/mbuild

and place them as sibling directories:
```
 |- build
 |
 |- mbuild
-|
 |- xed
 |
 |- xed_utils
```
where `build` is an empty directory in which XED datafiles will be collected.

## Collecting XED datafiles

The second command below collects XED datafiles:
```
cd build
../xed/mfile.py just-prep
```
The argument `just-prep` tells the XED build script to collect XED datafiles
without building XED.
The collected XED datafiles are put in the directory `build/obj/dgen`
and are the ultimate inputs to all scripts in `xed_utils`.
Of course, you can also drop the `just-prep` argument or replace it with other
allowed arguments (see: https://intelxed.github.io/build-manual/ for details).

Without any options, `xed/mfile.py` collects all instruction definitions in XED,
which include Xeon Phi, AMD-specific, VIA-specific, and deprecated features.
One can optionally choose to leave out various features.
For how to do so, run "`mfile.py -h`" to see the options.
Different feature selections will cause `xed_utils` scripts
to generate different outputs.

## Extracting a database from XED datafiles

Assuming the current directory is `build`, the following command
extracts a JSON, a CSV, and an SQLite databases from a XED build.
```
../xed_utils/xed_db.py -j test.json -c test.csv -s test.db
```
The script `xed_db.py` takes its input from `build/obj/dgen` and
imports some scripts in `xed/pysrc`.
If the directory structure is as described above,
there is no need to specify them explicitly.
(Run "`xed_db.py -h`" to see how to change those locations.)
Any or all of the `-j`, `-c`, and `-s` arguments are optional.
(If they are all left out, `xed_db.py` simply inputs the XED datafiles
without outputting anything.)
Note that the `.json`, `.csv`, and `.db` filename extensions are mandatory.

## Generating an x86 opcode map in HTML

Again assuming the current directory is `build`, the following command
generates an x86 opcode map in a single HTML file from the SQLite database
produced in the last step:
```
../xed_utils/xed_opcode_map.py test.db test.html
```
The script `xed_opcode_map.py` needs the JSON file `sdm_urls.json` in the same directory.
For how to change the location of that file, run `xed_opcode_map.py -h` to see the option.

The file `sdm_urls.json` contains a mapping from x86 instruction mnemonics to
URLs of x86 instruction reference pages at:

https://www.felixcloutier.com/x86/

which are extracted from Intel&reg; SDM by Félix Cloutier.
The following command generates `sdm_urls.json` anew:
```
../xed_utils/gen_sdm_urls.py test.db
```
But this step is needed only when the above website changes.

## Example x86 opcode map

An example x86 opcode map generated from a full build of
XED external release v2025.03.02 (commit id: 1bdc793f5f64cf207f6776f4c0e442e39fa47903)
can be found at:

https://ctchou.github.io/x86_opcode_map.html

Please read its "Legend" section for how to use the opcode map.

--------------------------------

&copy; 2024-present &emsp; Ching-Tsun Chou &emsp; <chingtsun.chou@gmail.com>
