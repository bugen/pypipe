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
    enter "cat staff.txt"
    enter "cat staff.txt| ppp 'line.upper()'"
    enter "cat staff.txt| ppp rec 'r[0]'"
    enter "cat staff.txt| ppp rec -l 6 f6,f5,f1"
    enter "cat staff.txt| ppp rec -H -f 'dic[\"Class\"] != \"Mammal\"'"
    enter "cat staff.txt| ppp rec -H -l6 --counter f6"
    enter "cat staff.txt| ppp rec -H --view"
    prompt
    sleep 2
    type " "
    unset IFS
}

main
