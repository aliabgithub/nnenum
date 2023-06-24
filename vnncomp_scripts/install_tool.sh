#!/bin/bash
# install_tool.sh script for VNNCOMP for nnenum
# Stanley Bak

TOOL_NAME=nnenum
VERSION_STRING=v1

# check arguments
if [ "$1" != ${VERSION_STRING} ]; then
	echo "Expected first argument (version string) '$VERSION_STRING', got '$1'"
	exit 1
fi

echo "Installing $TOOL_NAME"
DIR=$(dirname $(dirname $(realpath $0)))

# apt-get update &&
# apt-get install -y python3.8 python3-pip &&
# apt-get install -y psmisc && # for killall, used in prepare_instance.sh script
# pip3 install -r "$DIR/requirements.txt"


sudo apt-get update

sudo apt-get remove -y python2.7 python3.6
sudo apt-get autoremove -y
sudo apt-get install -y python3.8 python3.8-dev gfortran python3-pip bc

python3.8 -m pip install pip
sudo -H python3.8 -m pip install -U pipenv
pipenv install python 3.8
pipenv install -r "$DIR/requirements.txt"
pipenv_python=`pipenv run which python`

# Gurobi
cd ~/
wget https://packages.gurobi.com/9.1/gurobi9.1.2_linux64.tar.gz
tar -xzvf gurobi9.1.2_linux64.tar.gz 
rm gurobi9.1.2_linux64.tar.gz 
sudo mv gurobi912/ /opt/ 
cd /opt/gurobi912/linux64/
$pipenv_python setup.py install
