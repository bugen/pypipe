#!/bin/bash

# HOW TO USE
# 1. Install termtosvg https://github.com/nbedos/termtosvg
# 2. termtosvg -c ./create_demo.sh demo.svg

set -e
set -u

PROMPT="$"

enter() {
    INPUT=$1
    DELAY=1

    prompt
    sleep "$DELAY"
    type "$INPUT"
    sleep 0.5
    printf '%b' "\\n"
    eval "$INPUT"
    type "\\n"
}

prompt() {
    printf '%b ' "$PROMPT" | pv -q
}

type() {
    printf '%b' "$1" | pv -qL $((10+(-2 + RANDOM%5)))
}

main() {
    IFS='%'
    enter "cat sample.txt"
    enter "cat sample.txt| ppp 'line.upper()'"
    enter "cat sample.txt| ppp rec 'r[0]'"
    enter "cat sample.txt| ppp rec -l 5 'f3, f2, f1'"
    enter "cat sample.txt| ppp rec -l 5 -f 'f2 != \"Asia\"' line"
    enter "cat sample.txt| ppp rec -l 5 --counter f2"
    prompt
    sleep 3
    unset IFS
}

main
