# pypipe <!-- omit from toc -->

```sh
$ echo "pypipe" | ppp "line[::2]"
ppp
```

**pypipe** is a Python command-line tool for pipeline processing.

## Demo <!-- omit from toc -->
![Alt text](docs/demo.svg)


## Quick links <!-- omit from toc -->
- [Installation](#installation)
- [Basic usage and Examples](#basic-usage-and-examples)
- [pypipe is a code generator.](#pypipe-is-a-code-generator)
- [Misc](#misc)



## Installation
pypipe is a single Python file and uses only the standard library. You can use it by placing pypipe.py in a directory included in your PATH (e.g., ~/.local/bin). If execute permission is not already present, please add it.
```sh
chmod +x pypipe.py
```
To make it easier to type, it's recommended to create a symbolic link.
```sh
ln -s pypipe.py ppp
```

> **Note**
> pypipe requires Python 3.6 or later.

## Basic usage and Examples

### `| ppp line`

Processing line by line. You can get the line string as `line` or `l` and the line number as `i`.

```sh
$ cat staff.txt |ppp 'i, line.upper()'
1       NAME    WEIGHT  BIRTH   AGE     SPECIES CLASS
2       SIMBA   250     1994-06-15      29      LION    MAMMAL
3       DUMBO   4000    1941-10-23      81      ELEPHANT        MAMMAL
4       GEORGE  20      1939-01-01      84      MONKEY  MAMMAL
5       POOH    1       1921-08-21      102     TEDDY BEAR      ARTIFACT
6       BOB     0       1999-05-01      24      SPONGE  DEMOSPONGE
```

### `| ppp rec`

Split each line by TAB. You can get the list includes splitted strings as `rec` or `r` and the record number as `i`..
```sh
cat staff.txt |ppp rec 'r[:3]'
Name    Weight  Birth
Simba   250     1994-06-15
Dumbo   4000    1941-10-23
George  20      1939-01-01
Pooh    1       1921-08-21
Bob     0       1999-05-01
```

Using the `-l LENGTH, --length LENGTH` option allows you to get the values of each field as `f1, f2, f3, ....`
```sh
$ tail -n +2 staff.txt |ppp rec -l5 'f"{f1} is {f4} years old"'
Simba is 29 years old
Dumbo is 81 years old
George is 84 years old
Pooh is 102 years old
Bob is 24 years old
```

When using the `-H, --header` option, it treats the first line as a header line and skips it. The header values can be obtained from a list named `header`, and you can access the values of each field using the format `dic["FIELD_NAME"]`.
```sh
$ cat staff.txt |ppp rec -H 'rec[0], dic["Birth"]'
Simba   1994-06-15
Dumbo   1941-10-23
George  1939-01-01
Pooh    1921-08-21
Bob     1999-05-01
```

You can change the delimiter by using the `-d DELIMITER, --delimiter DELIMITER` option.
```sh
$ cat staff.csv |ppp rec -d , -l6  f1
Name
Simba
Dumbo
George
Pooh
Bob
```

### `| ppp csv`
`csv` is similar to `rec`, but the difference is that while `rec` simply splits the line using the specified DELIMITER like this, `'line.split(DELIMITER))'`, `csv` uses the [csv](https://docs.python.org/3/library/csv.html) library for parsing. Furthermore, `rec` is tab-separated by default, whereas `csv` is comma-separated.

You can specify options to pass to csv.reader and csv.writer using the `-O NAME=VALUE, --csv-opt NAME=VALUE` option.
```sh
$ cat staff.csv |ppp csv -O 'quoting=csv.QUOTE_ALL'
"Name","Weight","Birth","Age","Species","Class"
"Simba","250","1994-06-15","29","Lion","Mammal"
"Dumbo","4000","1941-10-23","81","Elephant","Mammal"
"George","20","1939-01-01","84","Monkey","Mammal"
"Pooh","1","1921-08-21","102","Teddy bear","Artifact"
"Bob","0","1999-05-01","24","Sponge","Demosponge"
```


### `| ppp text`
In `ppp text`, the entire standard input is read as a single piece of text. You can access the read text as `text`.

```sh
$ cat staff.txt | ppp text 'len(text)'
231
```

For example, `ppp text` is particularly useful when working with a indented JSON file. Using the `-j, --json` option allows you to decode the text into JSON. The decoded data can be obtained as a `dic`.
```sh
$ cat staff.json |ppp text -j 'dic["data"][0]'
{'Name': 'Simba', 'Weight': 250, 'Birth': '1994-06-15', 'Age': 29, 'Species': 'Lion', 'Class': 'Mammal'}
```

> **Note**
> You can also use `-j, --json` option in `line` and `file`.

### `| ppp file`
In `ppp file`, it receives a list of file paths from standard input. It then opens each received file path, reads the contents of the file into `text`, and repeats this process for each received file path in a loop. The received paths can be obtained as `path`.

```sh
$ ls staff.txt staff.csv staff.json staff.xml |ppp file 'path, len(text)'
staff.csv       231
staff.json      1046
staff.txt       231
staff.xml       1042
```

For example, `ppp file` is usuful, especially when processing a large number of JSON files.
```sh
find . -name '*.json'| ppp file --json ...
```

### `| ppp custom -N NAME`
You can easily create custom commands using pypipe. First, you define custom commands. The definition file is, by default, located at `~/.config/pypipe/pypipe_custom.py`. You can change the path of this file using the `PYPIPE_CUSTOM` environment variable.

The following is an example of defining custom commands xpath and sum.

~/.config/pypipe/pypipe_custom.py
```python
TEMPLATE_XPATH = r"""
from lxml import etree
{imp}

def output(e):
    if isinstance(e, etree._Element):
        print(etree.tostring(e).decode().rstrip())
    else:
        _print(e)

{pre}

tree = etree.parse(sys.stdin)
for e in tree.xpath('{path}'):
{loop_head}
{loop_filter}
{main}

{post}
"""

TEMPLATE_SUM = r"""
import re
import sys
{imp}

ptn = re.compile(r'{pattern}')
s = 0

def add_or_print(*args):
    global s
    rec = args[0]
    if len(args) == 2:
        if isinstance(args[1], int):
            i = args[1]
            if len(rec) >= i:
                s += rec[i-1]
        else:
            print(args[1])
    else:
        print(*args[1:])


for line in sys.stdin:
    line = line.rstrip('\r\n')
    rec = [{type}(e) for e in ptn.findall(line)]
    if not rec:
        continue
{loop_head}
{loop_filter}
{main}

print(s)
"""

custom_command = {
    "xpath": {
        "template": TEMPLATE_XPATH,
        "code_indent": 1,
        "default_code": "e",
        "wrapper": 'output({})',
        "options": {
            "path": {"default": '/'}
        }
    },
    "sum": {
        "template": TEMPLATE_SUM,
        "code_indent": 1,
        "default_code": "1",
        "wrapper": 'add_or_print(rec, {})',
        "options": {
            "pattern": {"default": r'\d+'},
            "type": {"default": 'int'}
        }
    },
}
```

You can use them as follows:

```sh
$ cat staff.xml |ppp custom -N xpath -O path='./Animal/Age'
<Age>29</Age>
<Age>81</Age>
<Age>84</Age>
<Age>102</Age>
<Age>24</Age>
```

```sh
$ seq 10000| ppp c -Nsum -f 'rec[0] % 3 == 0'
16668333
```

### `-c, --counter`
Using the `-c, --counter` option allows for easy data aggregation. When you specify the `-c, --counter` option, it creates an instance of collections.Counter, which can be accessed as either `counter` or `c`. The `-c, --counter` option is available for use in all commands.

An example of aggregating data by the 'Gender' and 'Hobby' fields.
```sh
$ cat people.csv |ppp csv -H --counter 'dic["Gender"], dic["Hobby"]'| head -n10
Female  Cooking 4
Male    Hiking  3
Female  Reading 3
Male    Gardening       3
Female  Traveling       3
Male    Playing Music   3
Female  Dancing 3
Female  Hiking  3
Female  Painting        2
Male    Photography     2
```

This is an example to aggregate data based on whether female individuals are 30 years or older.
```sh
cat people.csv |ppp csv -H -c -f 'dic["Gender"] == "Female"' 'int(dic["Age"]) >= 30'
False   16
True    10
```

When using the `-c, --counter` option, it uses `counter[{}] += 1` as the wrapper. If you want to count in a different way, you can disable the wrapping by using the `-n, --no-wrapping` option and add your own counting code.

```sh
$ cat population.csv |ppp csv -H -c -n 'counter[dic["State"]] += int(dic["Population"])'
New York        8398748
Texas   7751480
California      7327731
Illinois        2705994
Arizona 1680992
Pennsylvania    1584138
Florida 903889
Ohio    892533
Indiana 876862
North Carolina  792862
Washington      753675
Michigan        673104
```

Information about [Code wrapping](#code-wrappping).


## pypipe is a code generator.
pypipe is a command-line tool for pipeline processing, but it can also be thought of as a code generator. It generates code internally using the given arguments and then executes the generated code using the `exec` function. Therefore, instead of executing the generated code, you have the option to print it to the standard output or save it to a file.

### Print generated code. `-p, --print`
To check the generated code, you can use the `-p, --print` option.
```sh
ppp file -m rb -i hashlib -b 'total = 0' -b '_p("PATH", "SIZE", "MD5")' -e 'size = len(text)' -f 'path.stem == "staff"' 'total += size' 'path, size, hashlib.md5(text).hexdigest()' -a 'print(f"Total size: {total}", file=sys.stderr)' -p
```
The generated code is output as follows.
```python
# IMPORT
import sys
from functools import partial
import gzip
from pathlib import Path
import hashlib

def _open(path):
    if path.suffix == '.gz':
        return gzip.open(path, 'rb')
    else:
        return open(path, 'rb')

# PRE
_p = partial(print, sep="\t")  # ABBREV
I, S, B, L, D, SET = 0, "", False, [], {}, set()  # ABBREV

def _print(*args, delimiter='\t'):
    if len(args) == 1 and isinstance(args[0], (list, tuple)):
        print(*args[0], sep=delimiter)
    else:
        print(*args, sep=delimiter)

total = 0
_p("PATH", "SIZE", "MD5")

for i, line in enumerate(sys.stdin, 1):
    path = Path(line.rstrip('\r\n'))
    with _open(path) as file:
        text = file.read()
        # LOOP HEAD
        size = len(text)
        # LOOP FILTER
        if not (path.stem == "staff"): continue
        # MAIN
        total += size
        _print(path, size, hashlib.md5(text).hexdigest())

# POST
print(f"Total size: {total}", file=sys.stderr)
```

Check that there are no issues with the generated code and execute it.
```sh
$ find . -type f |ppp file -m rb -i hashlib -b 'total = 0' -b '_p("PATH", "SIZE", "MD5")' -e 'size = len(text)' -f 'path.stem == "staff"' 'total += size' 'path, size, hashlib.md5(text).hexdigest()' -a 'print(f"Total size: {total}", file=sys.stderr)'
PATH    SIZE    MD5
my_zoo.csv      186     e091408cc9174f1da86b50ee8e2fba96
my_zoo.xml      888     9edd78d97e45eccbac2b80747bd9c70b
my_zoo.json     887     7f15b3b8a23b91b60184113a38fa3e19
my_zoo.txt      186     4581c312d81815c3662f785ba9e7bd50
Total size: 2147
```


### Save generated code to a file. `-o PATH, --output PATH`
For writing more complex code, it's a good practice to create a template code with pypipe and edit the templated code manually. Here's the process you can follow:

1.  Create a template code with pypipe and save it to a file, for example:
    ```sh
    ppp line --output /tmp/pipe.py ...
    ```
2. Edit the code in /tmp/pipe.py to suit your needs.
3. Execute the modified code by piping input to it, for example:
   ```sh
   cat sample.txt | /tmp/pipe.py
   ```

### Main codes
The main code is specified as positional arguments. You can specify multiple main codes. The placement of the main code varies depending on the command. In commands like `line`, `rec`, `csv`, and `file`, the main code is added within the loop processing with proper indentation. However, in the `text` command, where there is no loop processing, the main code is added without indentation.
In the `custom` command, the main code is added according to the definitions provided in the `pypipe_custom.py` file.

```sh
$ ppp text -pqrn "for word in text.split():"  "    print(word)"
```
```python
import sys
from functools import partial

text = sys.stdin.read()
for word in text.split():  # <- HERE
    print(word)            # <- HERE
```

You can also write it with line breaks in the terminal as follows:
```sh
$ ppp text -pqrn '
> for word in text.split():
>     print(word)
> '
```


### Default main code
If no main code is specified in the arguments, pypipe adds a predefined default code. For example, the default code in Line mode is `'line'`.
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
By default, pypipe wraps the last code specified in the arguments with a predefined wrapper. For example, in `ppp line`, it uses `'_print({})'` as the wrapper. However, if the `-c, --counter` option is specified, it uses `'counter[{}] += 1'` as the wrapper instead.
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
#### Disable code wrappping. `-n, --no-wrapping`
If you want to disable the wrapping of the last code specified in the arguments by a predefined wrapper, you can use the `-n, --no-wrapping` option.
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

### Pre and Post codes. `-b CODE, --pre CODE`,  `-a CODE, --post CODE`
The code specified with `-b CODE, --pre CODE` will be added before the loop processing or the main code. This can be useful for declaring variables or performing any necessary setup before entering a loop or executing the main code. The code specified with `-a CODE, --post CODE` will be added after the loop processing or the main code. This can be useful for displaying aggregated results or performing any additional actions after the loop or main code execution.

```sh
$ ppp rec --pqrn -b 'TOTAL = 0' -b 'MAX = 0'  'TOTAL += int(rec[0])' 'MAX = max(MAX, int(rec[0]))'  -a 'print(f"TOTAL: {TOTAL}")' -a 'print(f"MAX: {MAX}")'
```
```python
import sys
from functools import partial


TOTAL = 0   # PRE
MAX = 0     # PRE

for i, line in enumerate(sys.stdin, 1):
    line = line.rstrip("\r\n")
    rec = line.split('\t')
    TOTAL += int(rec[0])
    MAX = max(MAX, int(rec[0]))

print(f"TOTAL: {TOTAL}")  # POST
print(f"MAX: {MAX}")      # POST
```

### Inner loop. `-e CODE, --loop-head CODE`, `-f CODE, --filter CODE`
In the loop processing of `line`, `rec`, `csv`, and `file` commands, the code is added in the following positions:
```
for ... :
    {loop_head}  # Added with the -e CODE, --loop-head CODE option.
    {filter}     # Added with the -f CODE, --filter CODE option.
    {main}       # The main code is added here.
```
"loop_head" is added using the `-e CODE, --loop-head CODE` option, while "filter" is added using the `-f CODE, --filter CODE` option.
Please note that the "loop_head" code is added as-is, while the "loop_filter" is wrapped with `if not ({}): continue`.

```sh
$ ppp line -pqrn -e 'line = line.replace("foo", "bar")' -e 'line = line.upper()' -f '"BAR" in line' 'print(line)'
```
```python
import sys
from functools import partial

for i, line in enumerate(sys.stdin, 1):
    line = line.rstrip("\r\n")
    line = line.replace("foo", "bar")  # LOOP_HEAD
    line = line.upper()                # LOOP_HEAD
    if not ("BAR" in line): continue   # FILTER
    print(line)                        # MAIN
```

### Import modules. `-i MODULE, --import MODULE`

By using the `-i MODULE, --import MODULE` option, you can import any modules. If the value specified with `--import` is in the form of a sentence, like `import math` or `from math import sqrt`, it will be added as an import statement just as it is. If only the module name is provided, like `math`, it will automatically be given an import statement, such as `import math`.

ppp text -i zlib -i 'from base64 import b64encode' 'b64encode(zlib.compress(text.encode()))'

```sh
$ ppp text -pqrn -i zlib -i 'from base64 import b64encode' 'print(b64encode(zlib.compress(text.encode())))'
```
```python
import sys
from functools import partial
import zlib                    # <- HERE
from base64 import b64encode   # <- HERE

text = sys.stdin.read()
print(b64encode(zlib.compress(text.encode())))
```

Usage example.
```sh
$ seq 5 |ppp -i math 'line, math.sqrt(int(line))'
1       1.0
2       1.4142135623730951
3       1.7320508075688772
4       2.0
5       2.23606797749979
```
## Misc

### pypipe only supports standard input.
pypipe only supports standard input. You cannot specify input files as arguments, and there are no plans to implement this option. pypipe follows a policy of keeping the implementation as simple as possible and avoiding dependencies on libraries outside the standard library. Supporting input files would make the implementation more complex and increase the code size, which goes against this policy. For most use cases, input from standard input should be sufficient. If you need functionalities like rewind or seek, it's better to write plain Python code without using pypipe. If you strongly prefer not to connect through pipes, you can kind of get the feel of specifying an input file using redirection like this (+_+)!:
```sh
ppp line ... <input.txt
```

### Performance
pypipe prioritizes ease of use and doesn't focus on high performance (as Python itself is not particularly fast). If you require high performance, it's advisable to use other excellent commands like [awk](https://www.gnu.org/software/gawk/manual/gawk.html).