#!/bin/bash 

THIS_DIR="$(dirname $0)/../"
THIS_DIR="$(readlink -f "$THIS_DIR")"

cd $THIS_DIR

. env/bin/activate
BACKUP_FILE="/data/trello-backup-$(date +%Y-%m-%d).json"
python -m gtd.trello backup $BACKUP_FILE

# zip the backup file
gzip $BACKUP_FILE

# crontab schedule to run every week on Sunday at 20:00
# 0 20 * * 0 /path/to/backup.sh
