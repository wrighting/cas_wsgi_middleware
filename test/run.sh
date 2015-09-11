#!/bin/bash -e
#-e means quit if a child fails

VIRTUALENV=cas_test
SETUP=false
if [ ! -d build ]
then
	mkdir build
	SETUP=true
fi
cd build
if [ ${SETUP} = true ]
then
  virtualenv ${VIRTUALENV}
fi
cd ${VIRTUALENV}
source bin/activate
cp -pr ../../../cas .
cp -pr ../../../REQUIREMENTS .
cp ../../config.py .
cp ../../test.py .
cp -pr ../../static .
if [ ${SETUP} = true ]
then
  cat ../../REQUIREMENTS >> REQUIREMENTS
  pip install -q -r REQUIREMENTS
fi

python test.py
