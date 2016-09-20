#!/bin/sh

DIR=`dirname "$0"`

cd $DIR
export FLASK_APP=app.py

# clean environment
[ -e "$DIR/instance" ] && rm $DIR/instance -Rf
[ -e "$DIR/data" ] && rm $DIR/data/ -Rf
