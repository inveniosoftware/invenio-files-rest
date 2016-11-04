#!/bin/sh

DIR=`dirname "$0"`

cd $DIR
export FLASK_APP=app.py

# clean environment
[ -e "instance" ] && rm -Rf instance
[ -e "data" ] && rm -Rf data
