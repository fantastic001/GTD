#!/bin/bash 

THIS_DIR=$(dirname "$0")

. $THIS_DIR/../env/bin/activate 

python -m gtd report > report.html