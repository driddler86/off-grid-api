#!/bin/bash
# Database backup script for Render free tier (ephemeral storage)
# This script should be scheduled via cron or Render Cron Jobs

set -e

# Configuration
DB_FILE="offgridscout.db"
BACKUP_DIR="/tmp/offgridscout_backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/offgridscout_$TIMESTAMP.db"

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Backup the database
if [ -f "$DB_FILE" ]; then
    echo "Backing up database to $BACKUP_FILE"
    cp "$DB_FILE" "$BACKUP_FILE"
    
    # Also backup WAL and SHM files if they exist
    if [ -f "$DB_FILE-wal" ]; then
        cp "$DB_FILE-wal" "$BACKUP_FILE-wal"
    fi
    if [ -f "$DB_FILE-shm" ]; then
        cp "$DB_FILE-shm" "$BACKUP_FILE-shm"
    fi
    
    # Compress the backup to save space
    gzip -f "$BACKUP_FILE" 2>/dev/null || true
    
    echo "Backup completed: $BACKUP_FILE.gz"
    
    # Keep only last 7 days of backups
    find "$BACKUP_DIR" -name "offgridscout_*.db*" -mtime +7 -delete
    
    # Count backups
    BACKUP_COUNT=$(ls -1 "$BACKUP_DIR" | wc -l)
    echo "Total backups in directory: $BACKUP_COUNT"
else
    echo "ERROR: Database file $DB_FILE not found!"
    exit 1
fi

# Optional: Upload to cloud storage (example for AWS S3)
# if [ -n "$AWS_ACCESS_KEY_ID" ] && [ -n "$AWS_SECRET_ACCESS_KEY" ]; then
#     aws s3 cp "$BACKUP_FILE.gz" "s3://your-bucket/backups/offgridscout_$TIMESTAMP.db.gz"
# fi
