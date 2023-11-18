#!/bin/bash 

THIS_DIR=$(readlink -f $(dirname $0))

echo $THIS_DIR

cd $THIS_DIR/../

./ci/build.sh 
./ci/send.sh 