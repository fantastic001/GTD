#!/bin/bash

echo "Copying to $DRIVE"
rclone copy report.html $DRIVE
rclone copy ~/.gtd/attachments/* $DRIVE/Attachments