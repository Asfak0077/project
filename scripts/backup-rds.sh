#!/usr/bin/env bash
# ==============================================================================
# VersusAI - Automated AWS RDS MySQL Backup Script (to AWS S3 or Local)
# Usage: ./scripts/backup-rds.sh
# ==============================================================================

set -e

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_DIR="./backups"
BACKUP_FILE="$BACKUP_DIR/versusai_backup_$TIMESTAMP.sql.gz"

mkdir -p "$BACKUP_DIR"

if [ -f ".env" ]; then
    export $(grep -v '^#' .env | xargs)
fi

echo "📦 Creating compressed MySQL database backup from $DB_HOST..."

mysqldump -h "$DB_HOST" -P "${DB_PORT:-3306}" -u "$DB_USER" -p"$DB_PASSWORD" \
    --single-transaction \
    --quick \
    --default-character-set=utf8mb4 \
    "$DB_NAME" | gzip > "$BACKUP_FILE"

echo "✅ Backup successfully created at: $BACKUP_FILE ($(du -h "$BACKUP_FILE" | cut -f1))"

# Optional S3 Upload if S3_BACKUP_BUCKET is configured
if [ -n "$S3_BACKUP_BUCKET" ] && command -v aws &> /dev/null; then
    echo "☁️ Uploading backup to S3 bucket: s3://$S3_BACKUP_BUCKET/backups/..."
    aws s3 cp "$BACKUP_FILE" "s3://$S3_BACKUP_BUCKET/backups/"
    echo "✓ S3 upload completed."
fi
