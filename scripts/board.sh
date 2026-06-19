#!/bin/bash

mypid=$$
tmpfile="/tmp/board_${mypid}.html"

OPEN_OPT=1

while [ $# -gt 0 ]; do
    case "$1" in
        --no-open)
            OPEN_OPT=0
            shift
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

function openit() {
    if [[ "$OSTYPE" == "darwin"* ]]; then
        open -nW "$1"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        xdg-open "$1"
    else
        echo "Unsupported OS: $OSTYPE"
        exit 1
    fi
}

python -m gtd service --name TrelloWeeklyBoard --format html  | \
    sed "s/<td>TODO<\/td>/<td bgcolor=\"#FFAAAA\">TODO<\/td>/g" | \
    sed "s/<td>Ready<\/td>/<td bgcolor=\"#FFFFAA\">Ready<\/td>/g" | \
    sed "s/<td>In Progress<\/td>/<td bgcolor=\"#AAAAFF\">In Progress<\/td>/g" | \
    sed "s/<td>Done<\/td>/<td bgcolor=\"#AAFFAA\">Done<\/td>/g" | \
    sed "s/<td>https:\/\/trello.com\/c\/\([a-zA-Z0-9]*\)<\/td>/<td><a href=\"https:\/\/trello.com\/c\/\1\">https:\/\/trello.com\/c\/\1<\/a><\/td>/g" | \
    sed "s/<td>PRIMARY/<td bgcolor=\"#FFAAAA\">/g" | \
    sed "s/<td>SECONDARY/<td bgcolor=\"#AAFFAA\">/g" | \
    sed "s/<td>COORDINATION/<td bgcolor=\"#AAAAFF\">/g" | \
    tee "$tmpfile"

if [[ "$OPEN_OPT" -eq 1 ]]; then
    openit "$tmpfile"
fi

rm "$tmpfile"