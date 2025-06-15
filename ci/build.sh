#!/bin/bash 

THIS_DIR=$(dirname "$0")

cd $THIS_DIR/..

. $THIS_DIR/../env/bin/activate 

python -m gtd report > report.html