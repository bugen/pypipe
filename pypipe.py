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
import argparse
import atexit
import subprocess
import sys
from os import chmod, environ

__version__ = "0.3.1"


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

{re_compile}
{parse_header}
{pre}

for i, line in enumerate(sys.stdin, 1):
    line = line.rstrip("\r\n")
    {parse_line}
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

JSON_FUNC = r"""
def _json(v):
    if isinstance(v, (dict, list, tuple)):
        v = json.dumps(v)
    elif not isinstance(v, str):
        v = str(v)
    return v
"""

PRINT_FUNC = r"""
def _print(*args, sep='{sep}'):
    if len(args) == 1 and isinstance(args[0], (list, tuple)):
        print(sep.join(str(v) for v in args[0]))
    else:
        print(sep.join(str(v) for v in args))
"""

PRINT_FUNC_JSON = r"""
def _print(*args, sep='{sep}'):
    print(sep.join(_json(v) for v in args))
"""

PRINT_FUNC_NATIVE = r"_print = partial(print, sep='{sep}')"

FORMAT_PRINT_FUNC = {
    "default": PRINT_FUNC, "d": PRINT_FUNC,
    "json": PRINT_FUNC_JSON, "j": PRINT_FUNC_JSON,
    "native": PRINT_FUNC_NATIVE, "n": PRINT_FUNC_NATIVE,
}

COUNTER_POST = r"""
for v, c in counter.most_common():
    v = "\t".join(str(x) for x in v) if isinstance(v, (list, set, tuple)) else v
    print(f"{v}\t{c}")
""".lstrip()


VIEW_TMPL = r"""
CLEAR = '\033[0m'
GREEN = '\033[32m'
CYAN = '\033[36m'
BOLD = '\033[1m'

def color(s, color_code=CYAN, bold=False):
    if color_code is None:
        return s
    return f"{BOLD}{color_code}{s}{CLEAR}" if bold else f"{color_code}{s}{CLEAR}"

nocolor = partial(color, color_code=None)
cyan = partial(color, color_code=CYAN)
green = partial(color, color_code=GREEN)

class Viewer:

    def __init__(self, colored=True):
        self.num = 1
        self.color1, self.color2 = (cyan, green) if colored else (nocolor, nocolor)

    def wlen(self, w):
        return sum(2 if east_asian_width(c) in "FWA" else 1 for c in w)

    def ljust(self, w, length):
        return w + " " * max(length - self.wlen(w), 0)

    def format(self, val):
        if isinstance(val, (dict, list, tuple, set)):
            return pformat(val, indent=1, width=120)
        return str(val)

    def _view(self, vals):
        num_width = len(str(len(vals)))
        tmpl = rf"{{0:<{num_width}}}  {{1}}"
        for i, val in enumerate(vals, 1):
            for j, line in enumerate(self.format(val).split("\n")):
                if j == 0:
                    print(tmpl.format(i, self.color2(line)))
                else:
                    print(tmpl.format('.', self.color2(line)))

    def _view_with_headers(self, vals, headers):
        num_width = len(str(len(vals)))
        header_width = max(self.wlen(h) for h in headers)
        tmpl = rf"{{0:<{num_width}}} | {{1}} | {{2}}"
        for i, (header, val) in enumerate(zip(headers, vals), 1):
            for j, line in enumerate(self.format(val).split("\n")):
                if j == 0:
                    print(tmpl.format(i, self.ljust(header, header_width), self.color2(line)))
                else:
                    print(tmpl.format('', self.ljust('', header_width), self.color2(line)))

    def view(self, *args, recnum=None, headers=None):
        print(self.color1(f'[Record {recnum or self.num}]', bold=True))
        vals = args[0] if len(args) == 1 and isinstance(args[0], (list, tuple)) else args
        if headers and len(vals) == len(headers):
            self._view_with_headers(vals, headers)
        else:
            self._view(vals)
        print()
        self.num += 1
"""

def enable_pager():
    if not sys.stdout.isatty():
        return False
    if environ.get('PYPIPE_PAGER_ENABLED', 'true').lower() == 'false':
        return False
    pager = environ.get('PYPIPE_PAGER', 'less -R -F -K')
    proc = None
    stdout_save = sys.stdout

    def on_exit():
        if proc:
            try:
                proc.stdin.close()
                proc.wait()
            except (BrokenPipeError, KeyboardInterrupt):
                pass
        sys.stdout = stdout_save

    proc = subprocess.Popen(
        pager.split(),
        stdin=subprocess.PIPE,
        universal_newlines=True,
    )
    sys.stdout = proc.stdin
    atexit.register(on_exit)
    return True


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


def is_json_needed(args):
    return ("json" in args and args.json or
            args.output_format in ("json", "j") or
            "field_type" in args and "j" in list(args.field_type.values()))


def gen_import(args):
    codes = ["# IMPORT"]
    codes.append("import sys")
    codes.append("from functools import partial")
    if args.view:
        codes.append("from pprint import pformat")
        codes.append("from unicodedata import east_asian_width")
    if is_json_needed(args):
        codes.append("import json")
    if args.counter:
        codes.append("from collections import Counter")
    # REC
    if args.command == "rec":
        if args.regex or (args.delimiter != r'\t' and len(args.delimiter) > 1):
            codes.append("import re")
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
    if args.view:
        codes.append(VIEW_TMPL)
        codes.append(rf"viewer = Viewer(colored={args.colored})")
        codes.append(r"view = viewer.view")
    if is_json_needed(args):
        codes.append(JSON_FUNC)
    codes.append(FORMAT_PRINT_FUNC[args.output_format].format(sep=args.output_delimiter))
    if args.counter:
        codes.append(r"counter = Counter()")
        codes.append(r"c = counter  #ABBREV")
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
        spaces = ""
        for c in codes[-1]:
            if c != " ":
                break
            spaces += c
        if args.counter:
            codes[-1] = spaces + r"counter[{}] += 1".format(codes[-1].lstrip())
        else:
            codes[-1] = spaces + wrapper.format(codes[-1].lstrip())
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
            loop_head_codes.append('d = dic  #ABBREV')
        loop_head_codes.extend(extend_codes(args.loop_heads))
        return "\n".join(indent(c) for c in loop_head_codes)

    wrapper = r"view({})" if args.view else r"_print({})"
    code = TEMPLATE_LINE.format(
        imp=gen_import(args),
        pre=gen_pre(args),
        loop_head=gen_loop_head(),
        loop_filter=gen_loop_filter(args),
        main=gen_main(args, "line", wrapper),
        post=gen_post(args),
    )
    exec_code(code, args)


def rec_handler(args):
    is_regex_delimiter = args.delimiter != r'\t' and len(args.delimiter) > 1
    if args.regex is not None:
        re_compile = rf"pattern = re.compile(r'{args.regex}')"
        parse_header = r"header = pattern.findall(next(sys.stdin).rstrip('\r\n'))" if args.header else ""
        parse_line = r"rec = pattern.findall(line)"
    elif is_regex_delimiter:
        re_compile = rf"pattern = re.compile(r'{args.delimiter}')"
        parse_header = r"header = pattern.split(next(sys.stdin).rstrip('\r\n'))" if args.header else ""
        parse_line = r"rec = pattern.split(line)"
    else:
        re_compile = ""
        parse_header = rf"header = next(sys.stdin).rstrip('\r\n').split('{args.delimiter}')" if args.header else ""
        parse_line = rf"rec = line.split('{args.delimiter}')"

    wrapper = r"_print({})"
    if args.view:
        wrapper = r"view({}, headers=header)" if args.header else r"view({})"
    code = TEMPLATE_REC.format(
        imp=gen_import(args),
        re_compile=re_compile,
        parse_header=parse_header,
        pre=gen_pre(args),
        parse_line=parse_line,
        loop_head=gen_loop_head_rec_csv(args),
        loop_filter=gen_loop_filter(args),
        main=gen_main(args, "rec", wrapper),
        post=gen_post(args),
    )
    exec_code(code, args)


def csv_handler(args):
    output_delimiter = args.output_delimiter or args.delimiter
    csv_reader_opts = [("delimiter", f"'{args.delimiter}'")]
    csv_writer_opts = [("delimiter", f"'{output_delimiter}'")]
    if args.csv_opts:
        csv_reader_opts.extend(args.csv_opts)
        csv_writer_opts.extend(args.csv_opts)
    reader_opts = ", ".join(f'{k}={v}' for k, v in csv_reader_opts)
    writer_opts = ", ".join(f'{k}={v}' for k, v in csv_writer_opts)
    parse_header = "header = next(reader)" if args.header else ""

    wrapper = r"_write({}, writer=writer)"
    if args.view:
        wrapper = r"view({}, headers=header)" if args.header else r"view({})"
    code = TEMPLATE_CSV.format(
        imp=gen_import(args),
        reader_opts=reader_opts,
        writer_opts=writer_opts,
        parse_header=parse_header,
        pre=gen_pre(args),
        loop_head=gen_loop_head_rec_csv(args),
        loop_filter=gen_loop_filter(args),
        main=gen_main(args, "rec", wrapper),
        post=gen_post(args),
    )
    exec_code(code, args)


def text_handler(args):

    def gen_pre_main():
        codes = []
        if args.json:
            codes.append("dic = json.loads(text)")
            codes.append('d = dic  #ABBREV')
        return "\n".join(codes)

    wrapper = r"view({})" if args.view else r"_print({})"
    code = TEMPLATE_TEXT.format(
        imp=gen_import(args),
        pre=gen_pre(args),
        pre_main=gen_pre_main(),
        main=gen_main(args, "text", wrapper, level=0),
        post=gen_post(args),
    )
    exec_code(code, args)


def file_handler(args):

    def gen_loop_head():
        loop_head_codes = extend_codes(args.loop_heads, "LOOP HEAD")
        if args.json:
            loop_head_codes.append("dic = json.loads(text)")
        return "\n".join(indent(c, 2) for c in loop_head_codes)

    wrapper = r"view({})" if args.view else r"_print({})"
    code = TEMPLATE_FILE.format(
        imp=gen_import(args),
        pre=gen_pre(args),
        mode=args.mode,
        loop_head=gen_loop_head(),
        loop_filter=gen_loop_filter(args, 2),
        main=gen_main(args, "text", wrapper, level=2),
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

    wrapper = r"view({})" if args.view else wrapper
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


def main(argv=sys.argv[1:]):
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
        "-v", '--view',
        action="store_true",
    )
    common_parser.add_argument(
        "-k", '--color',
        choices=['always', 'auto', 'never'],
        default='auto',
    )
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
    common_parser.add_argument(
        '-D', '--output-delimiter',
        dest="output_delimiter",
    )
    common_parser.add_argument(
        '-L', '--linebreak',
        action='store_const',
        const=r'\n',
        dest="output_delimiter",
    )
    common_parser.add_argument(
        '-F', '--output-format',
        choices=FORMAT_PRINT_FUNC.keys(),
        default='default',
        dest="output_format",
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
        '-m', '--regex-match',
        dest="regex",
    )
    rec_parser.add_argument(
        '-C', '--csv',
        action='store_const',
        dest="delimiter",
        const=',',
    )
    rec_parser.add_argument(
        '-S', '--spaces',
        action='store_const',
        dest="delimiter",
        const=r'\s+',
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
    if len(argv) == 0 or argv[0] not in expected_1st_args:
        argv.insert(0, "line")

    args = parser.parse_args(argv)

    if args.output_delimiter is None:
        if 'delimiter' in args and args.delimiter and len(args.delimiter) == 1:
            args.output_delimiter = args.delimiter
        else:
            args.output_delimiter = r'\t'

    args.colored = args.color == 'always' or (args.color == 'auto' and sys.stdout.isatty())
    if not args.print and not args.output:
        enable_pager()

    args.handler(args)


if __name__ == '__main__':
    main()
