
# xed_utils

--------------------------------

`xed_utils` provides several Python scripts for organizing and displaying
the x86 instruction encoding information contained in Intel&reg; XED:

https://intelxed.github.io

including an x86 opcode map generator.

## Requirements

Python 3.10 or above and a C compiler,
the latter of which is needed only for building XED.

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
where `build` is an empty directory in which XED will be built.

## Building XED

The following commands build XED:
```
cd build
../xed/mfile.py
```
Without any arguments, `xed/mfile.py` builds XED with all instruction definitions in XED,
which include Xeon Phi, AMD-specific, VIA-specific, and deprecated features.
One can optionally choose to leave out various features when building XED.
For how to do so, run "`mfile.py -h`" to see the options.
The ultimate input to all scripts in `xed_utils` described below is the files
that the XED build process collects in `build/obj/dgen`.
Thus different XED build configurations will generate different results.

## Extracting a database from a XED build

Assuming the current directory is `build`, the following command
extracts a JSON, a CSV, and an SQLite databases from a XED build.
```
../xed_utils/xed_db.py -j test.json -c test.csv -s test.db
```
The script `xed_db.py` takes its input from `build/obj/dgen` and
imports some scripts in `xed/pysrc`.
But if the directory structure is as described above,
there is no need to specify them explicitly.
(Run "`xed_db.py -h`" to see how to change those locations.)
Any or all of the `-j`, `-c`, and `-s` arguments are optional.
(If they are all left out, `xed_db.py` simply inputs the XED build
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
XED external release v2024.09.09 (commit id: b86dd5014463d954bc8898d2376b14852d26facd)
can be found at:

https://ctchou.github.io/x86_opcode_map.html

Please read its "Legend" section for how to use the opcode map.

--------------------------------

&copy; 2024-present  Ching-Tsun Chou (<chingtsun.chou@gmail.com>)
