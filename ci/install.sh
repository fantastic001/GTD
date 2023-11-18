#!/bin/bash 

pacman -S --noconfirm mutt python python-pip python-virtualenv 

virtualenv ./env 
. env/bin/activate 

pip install -r requirements.txt 
mkdir -p ~/.config 

echo "
{
	\"url\": \"$my_jira_url\",
	\"username\": \"$my_jira_username\",
	\"password\": \"$my_jira_password\"
}


" > ~/.config/gtd.json