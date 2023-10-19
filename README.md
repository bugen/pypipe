# pypipe

```sh
$ echo "pypipe" | ppp "line[::2]"
ppp
```

**pypipe** is a Python command-line tool for pipeline processing.


## Demo
![Alt text](docs/demo.svg)


## Quick links
- [pypipe](#pypipe)
  - [Demo](#demo)
  - [Quick links](#quick-links)
  - [Installation](#installation)
  - [Usage and Examples](#usage-and-examples)
    - [Line mode  `| ppp line`](#line-mode---ppp-line)
    - [Rec mode `| ppp rec`](#rec-mode--ppp-rec)
    - [Text mode `| ppp text`](#text-mode--ppp-text)
    - [File mode `| ppp file`](#file-mode--ppp-file)
    - [User custom mode `| ppp custom NAME`](#user-custom-mode--ppp-custom-name)
  - [pypipe is a code generator.](#pypipe-is-a-code-generator)
    - [Print generated code. `-p, --print`](#print-generated-code--p---print)
    - [Save generated code to a file. `-o PATH, --output PATH`](#save-generated-code-to-a-file--o-path---output-path)
    - [Default code](#default-code)
    - [Code wrappping](#code-wrappping)
      - [Disable code wrappping. `-n, --no-wrapper`](#disable-code-wrappping--n---no-wrapper)
  - [Other options](#other-options)
    - [Import modules. `-i, --import`](#import-modules--i---import)
  - [Misc](#misc)
    - [pypipe only supports standard input.](#pypipe-only-supports-standard-input)
    - [Performance](#performance)



## Installation
pypipe is a single Python file and uses only the standard libraries. You can use it by placing pypipe.py in a directory included in your PATH (e.g., ~/.local/bin). To make it easier to type, it's recommended to create a symbolic link as follows:
```sh
cd ~/.loca/bin/ && ln -s pypipe.py ppp
```

**Note:**
pypipe requires Python 3.7 or later.

## Usage and Examples

### Line mode  `| ppp line`

Processing line by line. You can get the line string as `"line"` and the line number as `"i"`.

```sh
$ cat /tmp/aaa.txt|ppp 'i, line.upper()'
1       ASIA    JAPAN   TOKYO   2014-08-01      1000
2       ASIA    KOREA   SEOUL   2022-03-23      2000
3       ASIA    CHINA   BEIJING 2022-09-10      3000
4       EUROPE  ENGLAND LONDON  1980-01-20      2000
5       EUROPE  GERMAN  BERLIN  1980-12-11      1300
6       EUROPE  SPAIN   MADRID  2000-12-20      5000
```

### Rec mode `| ppp rec`

Split each line by TAB. You can get the list includes splitted strings as `"rec"`.
```sh
$ cat /tmp/aaa.txt|ppp rec 'rec[1]'
japan
korea
china
england
german
Spain
```

### Text mode `| ppp text`



### File mode `| ppp file`


### User custom mode `| ppp custom NAME`


## pypipe is a code generator.
pypipe is a command-line tool for pipeline processing, but it can also be thought of as a code generator. It generates code internally using the given arguments and then executes the generated code using the `exec` function. Therefore, instead of executing the generated code, you have the option to print it to the standard output or save it to a file.

### Print generated code. `-p, --print`
To check the generated code, you can use the `-p, --print` option.
```sh
pppd rec -i math -b 'dups=set()'  -l5 -t 1:i,2:i,5:b  -e 'ok = f1 > 1000 or f5'  -f 'f1 not in dups' -f 'ok' 'dups.add(f2)' rec -a 'print(len(dups))' -p
```
The code is output as follows.
```python
import sys
from functools import partial
import math


def _write(*args, writer=None):
    if len(args) == 1 and isinstance(args[0], (list, tuple)):
        writer.writerow(args[0])
    else:
        writer.writerow(args)


# PRE
_p = partial(print, sep="\t")  #ABBREV
n, s, b, l, d, S = 0, "", False, [], {}, set()  #ABBREV

def _print(*args, delimiter='\t'):
    if len(args) == 1 and isinstance(args[0], (list, tuple)):
        print(*args[0], sep=delimiter)
    else:
        print(*args, sep=delimiter)

dups=set()


for i, line in enumerate(sys.stdin, 1):
    line = line.rstrip("\r\n")
    rec = line.split('\t')
    r = rec  # ABBREV
    # LOOP HEAD
    if len(rec) > 0 and rec[0]: rec[0] = int(rec[0])
    if len(rec) > 1 and rec[1]: rec[1] = int(rec[1])
    if len(rec) > 4 and rec[4]: rec[4] = bool(rec[4])
    f1, f2, f3, f4, f5 = r[:5]
    ok = f1 > 1000 or f5
    # LOOP FILTER
    if not (f1 not in dups): continue
    if not (ok): continue
    # LOOP BODY
    dups.add(f2)
    _print(rec, delimiter='\t')


# POST
print(len(dups))
```

### Save generated code to a file. `-o PATH, --output PATH`
For writing more complex code, it's a good practice to create a template code with pypipe and edit the templated code manually. Here's the process you can follow:

1 -  Create a template code with pypipe and save it to a file, for example:
```sh
ppp --output /tmp/pipe.py ...
```
2 - Edit the code in /tmp/pipe.py to suit your needs.
3 - Execute the modified code by piping input to it, for example:
```sh
cat sample.txt | /tmp/pipe.py
```

### Default code
If no code is specified in the arguments, pypipe adds a predefined default code. For example, the default code in Line mode is `'line'`.
```sh
ppp -pqr
```
```python
import sys
from functools import partial


def _print(*args, delimiter='\t'):
    if len(args) == 1 and isinstance(args[0], (list, tuple)):
        print(*args[0], sep=delimiter)
    else:
        print(*args, sep=delimiter)


for i, line in enumerate(sys.stdin, 1):
    line = line.rstrip("\r\n")
    _print(line)  # Default code with wrappping.
```


### Code wrappping
By default, pypipe wraps the last code specified in the arguments with a predefined wrapper. For example, in Line mode, it uses `'_print({})'` as the wrapper. However, if the `-c, --counter` option is specified, it uses `'counter[{}] += 1'` as the wrapper instead.
```sh
$ ppp line 'year = int(line)' year -pqr
```
```python
import sys
from functools import partial


def _print(*args, delimiter='\t'):
    if len(args) == 1 and isinstance(args[0], (list, tuple)):
        print(*args[0], sep=delimiter)
    else:
        print(*args, sep=delimiter)


for i, line in enumerate(sys.stdin, 1):
    line = line.rstrip("\r\n")
    year = int(line)
    _print(year)  # Wrapping
```
#### Disable code wrappping. `-n, --no-wrapper`
If you want to disable the wrapping of the last code specified in the arguments by a predefined wrapper, you can use the `-n, --no-wrapper` option.
```sh
ppp line -n 'n = max(len(line), n)' -a 'print(n)' -pqr
```
```python
import sys
from functools import partial


for i, line in enumerate(sys.stdin, 1):
    line = line.rstrip("\r\n")
    n = max(len(line), n)  # No wrapping

print(n)
```

## Other options

### Import modules. `-i, --import`
```sh
$ seq 3|ppp -i math 'math.sqrt(int(line))'
1.0
1.4142135623730951
1.7320508075688772
```

## Misc

### pypipe only supports standard input.
pypipe only supports standard input. You cannot specify input files as arguments, and there are no plans to implement this option. pypipe follows a policy of keeping the implementation as simple as possible and avoiding dependencies on libraries outside the standard library. Supporting input files would make the implementation more complex and increase the code size, which goes against this policy. For most use cases, input from standard input should be sufficient. If you need functionalities like rewind or seek, it's better to write plain Python code without using pypipe. If you strongly prefer not to connect through pipes, you can kind of get the feel of specifying an input file using redirection like this (+_+)!:
```sh
ppp line ... <input.txt
```

### Performance
pypipe prioritizes ease of use and doesn't focus on high performance (as Python itself is not particularly fast). If you require high performance, it's advisable to use other excellent commands like [awk](https://www.gnu.org/software/gawk/manual/gawk.html).