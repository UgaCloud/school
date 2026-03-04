# Backup Setup

This project supports both manual and automatic backups.

## 0) Configure from Admin UI

Use either:

- App UI: `School Settings` -> `Backups` tab
- Django admin UI: `/admin` -> `Backup Configuration`

From there you can set:

- enabled flag
- method (`json`/`native`/`hybrid`)
- database alias (from `settings.DATABASES`, e.g. `default`)
- schedule type (`daily`/`weekly`/`monthly`)
- schedule time (24-hour)
- backup directory
- retention days
- include media
- compression
- mysqldump binary path (MySQL/MariaDB)
- pg_dump binary path (PostgreSQL)
- psql binary path (PostgreSQL restore)

You can also run a manual backup from `School Settings` -> `Backups`.

## 1) Manual backup

Run from project root:

```bash
schoolenv/bin/python manage.py create_backup --compress --retention-days 14
```

Optional flags:

- `--with-media`: include `MEDIA_ROOT` as `media.tar.gz`
- `--label before_upgrade`: add label to backup name
- `--output-dir /path/to/backups`: override backup directory
- `--database default`: target database alias for dumpdata/native dump
- `--no-native-db-dump`: skip SQLite copy / MySQL SQL dump / PostgreSQL SQL dump
- `--mysqldump-bin /usr/bin/mysqldump`: custom mysqldump binary path
- `--pg-dump-bin /usr/bin/pg_dump`: custom pg_dump binary path

### Native dump behavior by engine

When native dump is enabled, command behavior is:

- MySQL/MariaDB: `database_dump.sql.gz` via `mysqldump`
- PostgreSQL: `database_dump.sql.gz` via `pg_dump`
- SQLite: file copy of the configured SQLite DB file

When JSON mode is enabled (`json` or `hybrid`), it also creates `database_dump.json`.

## 2) Automatic backup (cron)

Use the helper script:

```bash
./scripts/run_backup.sh
```

Add cron entry (daily at 2:00 AM):

```bash
crontab -e
```

```cron
0 2 * * * /home/wmisaac/Desktop/school/scripts/run_backup.sh
```

### Optional cron environment controls

- `BACKUP_WITH_MEDIA=1` to include media files
- `BACKUP_RETENTION_DAYS=14` retention window override
- `BACKUP_FORCE_COMPRESS=1` force compression regardless of DB config
- `BACKUP_LOG_FILE=/path/to/logfile.log` custom log file

Example:

```cron
0 2 * * * BACKUP_WITH_MEDIA=1 BACKUP_RETENTION_DAYS=21 BACKUP_FORCE_COMPRESS=1 /home/wmisaac/Desktop/school/scripts/run_backup.sh
```

## 3) Manual restore

Restore from backup folder or archive:

```bash
schoolenv/bin/python manage.py restore_backup \
  --backup-source backups/backup_20260226_054840_smoke_test.tar.gz \
  --yes-i-understand
```

Optional flags:

- `--restore-media`: restore media archive (`media.tar.gz`) into `MEDIA_ROOT`
- `--use-json-only`: skip native DB restore and use `database_dump.json`
- `--database default`: target database alias for restore
- `--mysql-bin /usr/bin/mysql`: custom mysql client path for MySQL restore
- `--psql-bin /usr/bin/psql`: custom psql path for PostgreSQL restore

From UI:

- `School Settings` -> `Backups` -> `Manual Restore`
- Enter backup source path, type `RESTORE`, and run.

## 4) Dashboard backup status

Backup status is shown in Reports > System Health.

Priority order for config:

1. `Backup Configuration` model values (set via School Settings > Backups or `/admin`)
2. `.env` fallback values (`BACKUP_*`, `MYSQLDUMP_BIN`, `PG_DUMP_BIN`, `PSQL_BIN`)

If backups are enabled but no file exists in the configured backup directory, status will show "No backup file detected".

## 5) Backup run history

Every backup/restore run writes a `BackupLog` row with:

- operation (`backup`/`restore`)
- status (`running`/`success`/`failed`)
- source/output path
- start/end timestamps
- duration (seconds)
- file size (backup runs)
- message/details
