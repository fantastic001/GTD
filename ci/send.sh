#!/bin/bash 

if [ -f ~/.muttrc ]; then 
    echo "There is already muttrc file"
else 
    echo " 
    set record = +Sent
    set realname = '$my_realname'
    set from = \"$my_email\"
    set use_from = yes

    set smtp_pass = '$my_pass'
    set smtp_url='smtps://$my_user@$my_smtp'
    set ssl_force_tls = yes

    " > ~/.muttrc
fi 

echo "In attachment you can find report for GTD

This email is sent from $(curl https://jsonip.com | jq ".ip")

" | mutt -s "GTD report" stefan@lugons.org -a report.html