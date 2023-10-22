#!/usr/bin/env python
"""
pypipe.py

Copyright 2023 bugen

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""
import sys
import argparse
from os import chmod


__version__ = "0.2.0"


INDENT = " " * 4

FIELD_TYPE_TMPL = {
    "i": r"int({})",
    "f": r"float({})",
    "b": r"bool({})",
    "j": r"json.loads({})",
}

TEMPLATE_LINE = r"""
{imp}

{pre}

for i, line in enumerate(sys.stdin, 1):
    line = line.rstrip("\r\n")
    l = line  # ABBREV
{loop_head}
{loop_filter}
{main}

{post}
"""

TEMPLATE_REC = r"""
{imp}

{parse_header}
{pre}

for i, line in enumerate(sys.stdin, 1):
    line = line.rstrip("\r\n")
    rec = line.split('{delimiter}')
    r = rec  # ABBREV
{loop_head}
{loop_filter}
{main}

{post}
"""

TEMPLATE_CSV = r"""
{imp}

def _write(*args, writer=None):
    if len(args) == 1 and isinstance(args[0], (list, tuple)):
        writer.writerow(args[0])
    else:
        writer.writerow(args)


reader = csv.reader(sys.stdin, {reader_opts})
writer = csv.writer(sys.stdout, {writer_opts})
_w = writer.writerow   # ABBREV
{parse_header}

{pre}

for i, rec in enumerate(reader, 1):
    r = rec  # ABBREV
{loop_head}
{loop_filter}
{main}

{post}
"""

TEMPLATE_TEXT = r"""
{imp}

{pre}

text = sys.stdin.read()
{pre_main}
{main}

{post}
"""

TEMPLATE_FILE = r"""
{imp}

def _open(path):
    if path.suffix == '.gz':
        return gzip.open(path, '{mode}')
    else:
        return open(path, '{mode}')

{pre}

for i, line in enumerate(sys.stdin, 1):
    path = Path(line.rstrip('\r\n'))
    with _open(path) as file:
        text = file.read()
{loop_head}
{loop_filter}
{main}

{post}
"""

PRINT_FUNC = r"""
def _print(*args, delimiter='\t'):
    if len(args) == 1 and isinstance(args[0], (list, tuple)):
        print(*args[0], sep=delimiter)
    else:
        print(*args, sep=delimiter)
"""

COUNTER_POST = r"""
for v, c in counter.most_common():
    v = "\t".join(str(x) for x in v) if isinstance(v, (list, set, tuple)) else v
    print(f"{v}\t{c}")
""".lstrip()


def indent(code, level=1):
    return INDENT * level + code


def format_code(code, remove_comments=False, remove_abbrevs=False):
    code = code.strip("\n")
    if remove_comments:
        code = "\n".join(
            line for line in code.split("\n")
            if not line.strip().startswith("#")
        )
    if remove_abbrevs:
        code = "\n".join(
            line for line in code.split("\n")
            if not line.endswith("# ABBREV")
        )
    return code


def _exec_code(code, args):
    if args.output or args.print:
        code = format_code(
            code,
            remove_comments=args.no_comments,
            remove_abbrevs=args.no_abbrevs,
        )
    if args.output:
        with open(args.output, "w") as outfile:
            print('#!/usr/bin/env python', file=outfile)
            print(code, file=outfile)
        chmod(args.output, 0o755)
    elif args.print:
        print(code)
    else:
        _globals = {
            '__name__': '__exec__',
            '__builtins__': globals()['__builtins__']
        }
        exec(compile(code, '<string>', 'exec'), _globals)


def exec_code(code, args):
    try:
        _exec_code(code, args)
    except (BrokenPipeError, KeyboardInterrupt):
        exit(0)


def extend_codes(codes, comment=None):
    not_empty_codes = []
    if comment:
        not_empty_codes.append(f"# {comment}")
    if codes:
        for _codes in codes:
            not_empty_codes.extend(c.rstrip() for c in _codes.split("\n") if c.rstrip())
    return not_empty_codes


def gen_import(args):
    codes = ["# IMPORT"]
    codes.append("import sys")
    codes.append("from functools import partial")

    if "json" in args and args.json:
        codes.append("import json")

    if "field_type" in args and "j" in [args.field_type.values()]:
        codes.append("import json")

    if args.counter:
        codes.append("from collections import Counter")

    # CSV
    if args.command == "csv":
        codes.append("import csv")

    # FILE
    if args.command == "file":
        codes.append("import gzip")
        codes.append("from pathlib import Path")

    if args.import_codes:
        for i in args.import_codes:
            if i.startswith('import ') or i.startswith('from '):
                codes.append(i)
            else:
                codes.append(f"import {i}")
    return "\n".join(codes)


def gen_pre(args):
    codes = ["# PRE"]
    codes.append(r'_p = partial(print, sep="\t")  # ABBREV')
    codes.append(r'I, S, B, L, D, SET = 0, "", False, [], {}, set()  # ABBREV')

    if not args.no_wrapping:
        codes.append(PRINT_FUNC)

    if args.counter:
        codes.append(r"counter = Counter()")
        codes.append(rf"c = counter  #ABBREV")

    if args.pre_codes:
        codes.extend(extend_codes(args.pre_codes))
    return "\n".join(codes)


def gen_post(args):
    if args.post_codes:
        return "\n".join(extend_codes(args.post_codes, "POST"))

    codes = ["# POST"]
    if args.counter:
        codes.append(COUNTER_POST)
    return "\n".join(codes)


def gen_main(args, default_code, wrapper, level=1):
    codes = extend_codes(args.codes, "MAIN")
    if len(codes) == 1:
        codes.append(default_code)  # set default code
    if not args.no_wrapping:
        if args.counter:
            codes[-1] = r"counter[{}] += 1".format(codes[-1])
        else:
            codes[-1] = wrapper.format(codes[-1])
    return "\n".join(indent(c, level=level) for c in codes)


def gen_loop_filter(args, level=1):
    filters = ["# LOOP FILTER"]
    if args.filters:
        for f in args.filters:
            if not f.strip():
                continue
            filters.append('if not ({}): continue'.format(f.strip()))
    return "\n".join(indent(c, level=level) for c in filters)


def gen_loop_head_rec_csv(args):
    loop_head_codes = ["# LOOP HEAD"]
    if args.field_type:
        # ex) if len(rec) > 16 and rec[16]: rec[16] = int(rec[16])
        for f, t in args.field_type.items():
            loop_head_codes.append(
                "if len(rec) > {0} and rec[{0}]: rec[{0}] = {1}".format(
                    f - 1, FIELD_TYPE_TMPL[t].format(f"rec[{f-1}]"))
            )
    if args.field_length:
        # ex) f1, f2, f3, f4 = r[:4]
        loop_head_codes.append("{} = {}".format(
            ", ".join(f"f{i+1}" for i in range(args.field_length)),
            f"r[:{args.field_length}]",
        ))
    if args.header:
        loop_head_codes.append("dic = dict(zip(header, rec))")
        loop_head_codes.append("d = dic # ABBREV")

    loop_head_codes.extend(extend_codes(args.loop_heads))
    return "\n".join(indent(c) for c in loop_head_codes)


def line_handler(args):

    def gen_loop_head():
        loop_head_codes = ["# LOOP HEAD"]
        if args.json:
            loop_head_codes.append('dic = json.loads(line)')
            loop_head_codes.append(f'd = dic  #ABBREV')
        loop_head_codes.extend(extend_codes(args.loop_heads))
        return "\n".join(indent(c) for c in loop_head_codes)

    code = TEMPLATE_LINE.format(
        imp=gen_import(args),
        pre=gen_pre(args),
        loop_head=gen_loop_head(),
        loop_filter=gen_loop_filter(args),
        main=gen_main(args, "line", r"_print({})"),
        post=gen_post(args),
    )
    exec_code(code, args)


def rec_handler(args):
    if args.header:
        parse_header = r"header = next(sys.stdin).rstrip('\r\n').split('{}')".format(args.delimiter)
    else:
        parse_header = ""

    code = TEMPLATE_REC.format(
        imp=gen_import(args),
        parse_header=parse_header,
        pre=gen_pre(args),
        delimiter=args.delimiter,
        loop_head=gen_loop_head_rec_csv(args),
        loop_filter=gen_loop_filter(args),
        main=gen_main(args, "rec", "_print({{}}, delimiter='{}')".format(args.delimiter)),
        post=gen_post(args),
    )
    exec_code(code, args)


def csv_handler(args):
    csv_opts = [("delimiter", f"'{args.delimiter}'")]
    if args.csv_opts:
        csv_opts.extend(args.csv_opts)
    reader_opts = ", ".join(f'{k}={v}' for k, v in  csv_opts)
    writer_opts = ", ".join(f'{k}={v}' for k, v in  csv_opts)
    parse_header = "header = next(reader)" if args.header else ""

    code = TEMPLATE_CSV.format(
        imp=gen_import(args),
        reader_opts=reader_opts,
        writer_opts=writer_opts,
        parse_header=parse_header,
        pre=gen_pre(args),
        loop_head=gen_loop_head_rec_csv(args),
        loop_filter=gen_loop_filter(args),
        main=gen_main(args, "rec", "_write({}, writer=writer)"),
        post=gen_post(args),
    )
    exec_code(code, args)


def text_handler(args):

    def gen_pre_main():
        codes = []
        if args.json:
            codes.append("dic = json.loads(text)")
            codes.append(f'd = dic  #ABBREV')
        return "\n".join(codes)

    code = TEMPLATE_TEXT.format(
        imp=gen_import(args),
        pre=gen_pre(args),
        pre_main=gen_pre_main(),
        main=gen_main(args, "text", "_print({})", level=0),
        post=gen_post(args),
    )
    exec_code(code, args)


def file_handler(args):

    def gen_loop_head():
        loop_head_codes = extend_codes(args.loop_heads, "LOOP HEAD")
        if args.json:
            loop_head_codes.append("dic = json.loads(text)")
        return "\n".join(indent(c, 2) for c in loop_head_codes)

    code = TEMPLATE_FILE.format(
        imp=gen_import(args),
        pre=gen_pre(args),
        mode=args.mode,
        loop_head=gen_loop_head(),
        loop_filter=gen_loop_filter(args, 2),
        main=gen_main(args, "text", r"_print({})", level=2),
        post=gen_post(args),
    )
    exec_code(code, args)


def load_custom_command(name):
    from os import environ
    from pathlib import Path
    custom_path = Path(environ.get("PYPIPE_CUSTOM", '~/.config/pypipe/pypipe_custom.py'))
    _globals = {
        '__name__': '__exec__',
        '__builtins__': globals()['__builtins__']
    }
    # load custom configuration from the user custom file
    with open(custom_path.expanduser()) as f:
        exec(f.read(), _globals)
    custom_mode = _globals["custom_command"]
    return custom_mode[name]


def custom_handler(args):
    config = load_custom_command(args.name)
    template = config["template"]
    code_indent = config.get("code_indent", 0)
    wrapper = config.get("wrapper")
    default_code = config.get("default_code")
    opt_configs = config.get("options", {})

    def gen_loop_head():
        loop_head_codes = extend_codes(args.loop_heads, "LOOP HEAD")
        return "\n".join(indent(c, code_indent) for c in loop_head_codes)

    params = {
        "imp": gen_import(args),
        "pre": gen_pre(args),
        "loop_head": gen_loop_head(),
        "loop_filter": gen_loop_filter(args, code_indent),
        "main": gen_main(args, default_code, wrapper, level=code_indent),
        "post": gen_post(args),
    }
    opts = {k: v  for k, v in args.opts}
    opt_params = {
        k: opts.get(k) or opt_configs[k].get("default")
        for k in opt_configs
    }
    params.update(opt_params)
    code = template.format(**params)
    exec_code(code, args)


if __name__ == "__main__":

    def key_value(s):
        kv = s.split("=", 1)
        return kv[0], kv[1]

    def field_type(s):
        ret = {}
        for ft in s.split(","):
            f, t = ft.split(":", 1)
            ret[int(f)] = t
        return ret

    parser = argparse.ArgumentParser(
        description='Python PiPe command line tool')

    parser.add_argument(
        '-V', '--version',
        action='version',
        version=f'pypipe {__version__}'
    )

    ## COMMON OPTIONS
    common_parser = argparse.ArgumentParser(add_help=False)
    common_parser.add_argument(
        "-p", '--print',
        action="store_true",
        help="Only prints the generated code."
    )
    common_parser.add_argument(
        "-o", '--output',
        help="Output file"
    )
    common_parser.add_argument(
        "-q", '--no-comments',
        dest="no_comments",
        action="store_true",
    )
    common_parser.add_argument(
        "-r", '--no-abbrevs',
        dest="no_abbrevs",
        action="store_true",
    )
    common_parser.add_argument(
        "-n", '--no-wrapping',
        dest="no_wrapping",
        action="store_true"
    )
    common_parser.add_argument(
        "-i", '--import',
        dest="import_codes",
        action="append",
    )
    common_parser.add_argument(
        "-b", '--pre',
        dest="pre_codes",
        action="append",
    )
    common_parser.add_argument(
        "-a", '--post',
        dest="post_codes",
        action="append",
    )
    common_parser.add_argument(
        '-c', '--counter',
        action="store_true"
    )

    ## LOOP OPTIONS
    loop_parser = argparse.ArgumentParser(add_help=False)
    loop_parser.add_argument(
        "-e", "--loop-head",
        dest="loop_heads",
        default=[],
        action="append",
    )
    loop_parser.add_argument(
        "-f", "--filter",
        dest="filters",
        action="append",
    )

    ## REC AND CSV OPTIONS
    rec_csv_parser = argparse.ArgumentParser(add_help=False)
    rec_csv_parser.add_argument(
        '-l', '--field-length',
        dest="field_length",
        type=int,
    )
    rec_csv_parser.add_argument(
        '-t', '--field-type',
        dest="field_type",
        type=field_type,
        default={},
        help="ex) 1:i,3:j,5:b"
    )
    rec_csv_parser.add_argument(
        '-H', '--header',
        action="store_true",
    )

    # SUB COMMANDS
    subparsers = parser.add_subparsers(
        title="subcommands",
        help="show subcommands help: %(prog)s subcommand -h"
    )

    ## LINE
    line_parser = subparsers.add_parser(
        "line", aliases=['l'], parents=[common_parser, loop_parser])
    line_parser.add_argument(
        '-j', '--json',
        action="store_true"
    )
    line_parser.add_argument("codes", nargs='*')
    line_parser.set_defaults(handler=line_handler, command="line")

    ## REC
    rec_parser = subparsers.add_parser(
        "rec", aliases=['r', 'record'], parents=[common_parser, loop_parser, rec_csv_parser])
    rec_parser.add_argument("codes", nargs='*')
    rec_parser.add_argument(
        '-d', '--delimiter',
        default=r'\t'
    )
    rec_parser.add_argument(
        '-C', '--csv',
        action='store_const',
        dest="delimiter",
        const=',',
    )
    rec_parser.set_defaults(handler=rec_handler, command="rec")

    ## CSV
    csv_parser = subparsers.add_parser(
        "csv", parents=[common_parser, loop_parser, rec_csv_parser])
    csv_parser.add_argument("codes", nargs='*')
    csv_parser.add_argument(
        '-d', '--delimiter',
        default=','
    )
    csv_parser.add_argument(
        '-O', '--csv-opt',
        dest="csv_opts",
        type=key_value,
        default=[],
        action="append",
    )
    csv_parser.add_argument(
        '-T', '--tsv',
        action='store_const',
        dest="delimiter",
        const=r'\t',
    )
    csv_parser.set_defaults(handler=csv_handler, command="csv")

    ## TEXT
    text_parser = subparsers.add_parser(
        "text", aliases=['t'], parents=[common_parser])
    text_parser.add_argument("codes", nargs='*')
    text_parser.add_argument(
        '-j', '--json',
        action="store_true"
    )
    text_parser.set_defaults(handler=text_handler, command="text")

    ## FILE
    file_parser = subparsers.add_parser(
        "file", aliases=['f'], parents=[common_parser, loop_parser])
    file_parser.add_argument("codes", nargs='*')
    file_parser.add_argument(
        "-m", "--mode",
        default='rt',
    )
    file_parser.add_argument(
        '-j', '--json',
        action="store_true"
    )
    file_parser.set_defaults(handler=file_handler, command="file")

   ## CUSTOM
    custom_parser = subparsers.add_parser(
        "custom", aliases=['c'], parents=[common_parser, loop_parser])
    custom_parser.add_argument(
        '-O', '--opt',
        action="append",
        dest="opts",
        default=[],
        type=key_value,
    )
    # custom_parser.add_argument("name")
    custom_parser.add_argument(
        "-N", "--name",
        required=True,
    )
    custom_parser.add_argument("codes", nargs='*')
    custom_parser.set_defaults(handler=custom_handler, command="custom")


    expected_1st_args = (
        "line", "l", "rec", "r", "csv", "text", "t", "file", "f", "custom", "c",
        "-h", "--help", "-V", "--version"
    )
    if len(sys.argv) == 1 or sys.argv[1] not in expected_1st_args:
        sys.argv.insert(1, "line")

    args = parser.parse_args()
    args.handler(args)
