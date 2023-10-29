import sys
from pathlib import Path

import pytest

from pypipe import main

TEST_DATA_DIR = Path(__file__).resolve().parent / 'data'


@pytest.mark.parametrize('input_text_file_name, expected_text_file_name, command', [
    ('staff.txt', 'ppp_line_1.txt', ['i, line.upper()', ]),
    ('staff.jsonlines.txt', 'ppp_line_2.txt', ['-j', 'dic["Name"]']),
    ('staff.txt', 'ppp_rec_1.txt', ['rec', 'r[:3]']),
    ('staff.txt', 'ppp_rec_2.txt', ['rec', '-l5', 'f"{f1} is {f4} years old"']),
    ('staff.txt', 'ppp_rec_3.txt', ['rec', '-H', 'rec[0], dic["Birth"]']),
])
def test_ppp_line(input_text_file_name, expected_text_file_name, command,capsys):
    ex_data: str
    with open(TEST_DATA_DIR / 'input' / input_text_file_name) as file:
        sys.stdin = (_l for _l in file.readlines())
    with open(TEST_DATA_DIR / 'expect' / expected_text_file_name) as file:
        ex_data = file.read()

    main(command)
    out, err = capsys.readouterr()
    assert out == ex_data
