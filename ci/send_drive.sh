#!/bin/bash

echo "Copying to $DRIVE"
rclone copy report.html $DRIVE

if [ -n "$WEEK_REPORTS" ]; then
    echo "Copying to $WEEK_REPORTS"
    CURRENT_YEAR=$(date +%Y)
    CALENDAR_WEEK=$(date +%V)
    rclone mkdir "$WEEK_REPORTS/$CURRENT_YEAR-$CALENDAR_WEEK"
    rclone copy report.html "$WEEK_REPORTS/$CURRENT_YEAR-$CALENDAR_WEEK"
    if [ -d ~/.gtd/attachments ] && [ "$(ls -A ~/.gtd/attachments)" ]; then
        rclone copy ~/.gtd/attachments/*  \
            "$WEEK_REPORTS/$CURRENT_YEAR-$CALENDAR_WEEK/Attachments"
    fi
fi
if [ -d ~/.gtd/attachments ] && [ "$(ls -A ~/.gtd/attachments)" ]; then
    echo "Copying attachments to $DRIVE"
    rclone copy ~/.gtd/attachments/* $DRIVE/Attachments
fi