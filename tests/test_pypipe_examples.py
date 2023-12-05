import io
import sys
from pathlib import Path

import pytest

from pypipe import main

TEST_DATA_DIR = Path(__file__).resolve().parent / 'data'


@pytest.mark.parametrize('input_text_file_name, expected_text_file_name, command', [
    ('staff.txt', 'ppp_line_1.txt', ['i, line.upper()', ]),
    ('staff.jsonlines.txt', 'ppp_line_2.txt', ['-j', 'dic["Name"]']),
    ('echo_line_1.txt', 'ppp_line_3.txt', ['line, math.sqrt(int(line))',]),
    ('echo_line_2.txt', 'ppp_line_4.txt', ['urllib.parse.urlparse(line)',]),
    ('staff.txt', 'ppp_rec_1.txt', ['rec', 'r[:3]']),
    ('staff.txt', 'ppp_rec_2.txt', ['rec', '-l5', 'f"{f1} is {f4} years old"']),
    ('staff.txt', 'ppp_rec_3.txt', ['rec', '-H', 'rec[0], dic["Birth"]']),
    ('echo_rec_1.txt', 'ppp_rec_4.txt', ['rec', '-l5', '--type', '2:i,3:f,4:b,5:j',
                                         "type(f1),type(f2),type(f3),type(f4),type(f5)"]),
    ('staff.csv', 'ppp_rec_5.txt', ['rec', '-d', ',', '-l6', 'f1']),
    ('echo_rec_2.txt', 'ppp_rec_6.txt', ['rec', '-d', r'\s+', 'rec[2]']),
    ('staff.txt', 'ppp_rec_7.txt', ['rec', '-D' ',']),
    ('echo_rec_3.txt', 'ppp_rec_8.txt', ['rec', '-m', r'\d+', 'r[1]']),
    ('staff.txt', 'ppp_rec_9.txt', ['rec', '-Fd']),
    ('staff.txt', 'ppp_rec_10.txt', ['rec', '-Fj']),
    ('staff.txt', 'ppp_rec_11.txt', ['rec', '-Fn']),
    ('staff.txt', 'ppp_rec_12.txt', ['rec', '-D', ',']),
    ('staff.txt', 'ppp_rec_13.txt', ['rec', '-D', '||']),
    ('staff.txt', 'ppp_rec_14.txt', ['rec', '-d', r'\s+']),
    ('staff.txt', 'ppp_rec_15.txt', ['rec', '-m', r'\w+']),
    ('staff.txt', 'ppp_rec_16.txt', ['rec', '-v', '-H', '-knever']),
    ('staff.txt', 'ppp_rec_17.txt', ['rec', 'f3,f2,f1']),
    ('echo_rec_4.txt', 'ppp_rec_18.txt', ['rec', '--view', '-t', '[(v, type(v)) for v in rec]']),
    ('staff.txt', 'ppp_rec_19.txt', ['rec', 'print(f1,f2,f3)']),
    ('staff.txt', 'ppp_rec_20.txt', ['rec', '-H', '-t', '-c', 'counter["TOTAL WEIGHT"] += f2']),
    ('staff.csv', 'ppp_csv_1.txt', ['csv', '-O', 'quoting=csv.QUOTE_ALL']),
    ('staff.csv', 'ppp_csv_2.txt', ['csv', '-D', r'\t']),
    ('staff.csv', 'ppp_csv_3.txt', ['csv', '-H', '-f', 'int(f2) > 100']),
    ('staff.csv', 'ppp_csv_4.txt', ['csv', '-t', '[type(v) for v in rec]']),
    ('staff.txt', 'ppp_text_1.txt', ['text', "len(text)"]),
    ('staff.json', 'ppp_text_2.txt', ['text', '-j', 'dic["data"][0]']),
    ('staff.json', 'ppp_text_3.txt', ['text', '-j', '-L', '-Fj', '*dic["data"]']),
    ('staff.json', 'ppp_text_4.txt', ['text', '-j', '-v', '-knever', 'dic']),
    ('staff.json', 'ppp_text_5.txt', ['text', '--convert', '-Fj', 'text["number_of_records"]']),
])
def test_ppp_common(input_text_file_name, expected_text_file_name, command, capsys):
    ex_data: str
    try:
        sys.stdin = open(TEST_DATA_DIR / 'input' / input_text_file_name)
        with open(TEST_DATA_DIR / 'expect' / expected_text_file_name) as file:
            ex_data = file.read()

        main(command)
        out, err = capsys.readouterr()
        assert out.replace("\r\n", "\n") == ex_data.replace("\r\n", "\n")
    finally:
        sys.stdin.close()


def test_ppp_file(capsys):
    f = io.StringIO()
    f.write(str(TEST_DATA_DIR / 'input' / 'staff.json')+"\n")
    f.write(str(TEST_DATA_DIR / 'input' / 'staff.txt')+"\n")
    f.seek(0)
    sys.stdin = f

    main(['file', 'path, len(text)'])
    out, err = capsys.readouterr()
    expect = [
        str(TEST_DATA_DIR / 'input' / 'staff.json') + "\t" + "1046\n",
        str(TEST_DATA_DIR / 'input' / 'staff.txt') + "\t" + "231\n"
    ]
    assert out == ''.join(expect)
