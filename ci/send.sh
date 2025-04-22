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

resolve_mutt_var() {
    local varname="$1"
    local config_file="${2:-$HOME/.muttrc}"

    # Find the first line that defines the variable
    local line
    line=$(grep -E "^\s*set\s+${varname}\s*=" "$config_file" | tail -n 1)

    # Extract the value
    local value
    value=$(echo "$line" | sed -E 's/.*=\s*"?([^"]+)"?/\1/')

    # Look for references to other variables (e.g., $foo)
    while [[ "$value" =~ \$([a-zA-Z0-9_]+) ]]; do
        local ref="${BASH_REMATCH[1]}"
        local ref_val
        ref_val=$(resolve_mutt_var "$ref" "$config_file")
        # Replace all occurrences of $ref with its resolved value
        value="${value//\$$ref/$ref_val}"
    done

    # Remove any surrounding quotes
    value=$(echo "$value" | sed -E 's/^["'\'']|["'\'']$//g')
    # Remove any surrounding whitespace
    value=$(echo "$value" | sed -E 's/^[[:space:]]+|[[:space:]]+$//g')

    echo "$value"
}

ATTACHMENTS_DIR=~/.gtd/attachments
mkdir -p $ATTACHMENTS_DIR

rename_and_echo() {
    newname=$(echo $1 | sed "s/ /_/g")
    mv "$1" $newname
    echo "$newname"
}

find $ATTACHMENTS_DIR -type f -name "*.html" | while read file; do
    rename_and_echo "$file"
done
# Example usage
my_email=$(resolve_mutt_var "from")
echo "Resolved email: $my_email"


content="In attachment you can find report for GTD

This email is sent from $(curl https://jsonip.com | jq ".ip")

" 

# do not attach files in attachments if directory is empty
if [ -z "$(ls $ATTACHMENTS_DIR/)" ]; then
    echo "No attachments found in $ATTACHMENTS_DIR"
    echo "$content" | mutt -s "GTD report" -a report.html -- $my_email
else
    echo "Attachments found in $ATTACHMENTS_DIR"
    echo "$content" | mutt -s "GTD report" -a report.html -a $ATTACHMENTS_DIR/* -- $my_email
fi



rm -rf $ATTACHMENTS_DIR/*