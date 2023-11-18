#!/bin/bash 

pacman -S --noconfirm mutt python python-pip python-virtualenv 

virtualenv ./env 
. env/bin/activate 

pip install -r requirements.txt 