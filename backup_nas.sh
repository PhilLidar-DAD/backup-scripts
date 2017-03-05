#!/bin/bash

# Check arguments
case "$1" in
    push|pull)
        DIRECTION="$1"
        ;;
    *)
        echo 'rsync direction must be set (push/pull)! Exiting.'
        exit 1
        ;;
esac


# Load variables from config file
source settings.sh

SRC_USER="root"
SRC_DIR="$2"
SRC_PATH="${SRC_BASE}/${SRC_DIR}/"

DST_USER="root"
DST_PATH="${DST_BASE}/${SRC_DIR}/"

ESC_SRC=${SRC_DIR//\//_}
BASE_PATH="$( cd "$( dirname "$0" )" ; pwd -P )"
PRELOG_PATH="${BASE_PATH}/rsync_prelog/${ESC_SRC}.log"
CURLOG_PATH="${BASE_PATH}/rsync_curlog/${ESC_SRC}.log"
SIZETOBACKUP_PATH="${BASE_PATH}/sizetobackup/${ESC_SRC}"
TOTALSIZE_PATH="${BASE_PATH}/totalsize/${ESC_SRC}"
LOCK_FILE="${BASE_PATH}/lock/${ESC_SRC}"

RSYNC_OPTS=(-aiPSA --delete --stats --timeout=300 --ignore-errors \
--info=progress2)


# Check if filter file exists
FILTER_FILE="${BASE_PATH}/filter_${ESC_SRC}"
if [ -f "$FILTER_FILE" ]; then
    echo "FILTER_FILE: $FILTER_FILE"
    RSYNC_OPTS=(--include-from="$FILTER_FILE" "${RSYNC_OPTS[@]}")
fi


checkresult() {
    if [ $1 -ne 0 ]; then
        (>&2 echo "Error backing up $SRC_PATH"; >&2 echo; >&2 echo "$OUTPUT")

        # Send e-mail
        # (echo "Subject: Error backing up $SRC_PATH"; echo; echo "$OUTPUT") | sendmail server-admins@dream.upd.edu.ph

        rm $LOCK_FILE
        exit 1
    fi
}


echo "DIRECTION: $DIRECTION"
case $DIRECTION in
    push)
        RSYNC_ARGS="${SRC_PATH} ${DST_USER}@${DST_HOST}:${DST_PATH}"
        ;;
    pull)
        RSYNC_ARGS="${SRC_USER}@${SRC_HOST}:${SRC_PATH} ${DST_PATH}"
        ;;
esac

echo "RSYNC_ARGS: $RSYNC_ARGS"
echo "PRELOG_PATH: $PRELOG_PATH"
echo "CURLOG_PATH: $CURLOG_PATH"
echo "SIZETOBACKUP_PATH: $SIZETOBACKUP_PATH"
echo "TOTALSIZE_PATH: $TOTALSIZE_PATH"
echo "LOCK_FILE: $LOCK_FILE"


# Create dirs
mkdir -p "$( dirname "$PRELOG_PATH" )"
mkdir -p "$( dirname "$CURLOG_PATH" )"
mkdir -p "$( dirname "$SIZETOBACKUP_PATH" )"
mkdir -p "$( dirname "$TOTALSIZE_PATH" )"
mkdir -p "$( dirname "$LOCK_FILE" )"


# Backup previous logs
mv -f ${PRELOG_PATH} ${PRELOG_PATH}.old
mv -f ${CURLOG_PATH} ${CURLOG_PATH}.old


# Check lock
if [ -f $LOCK_FILE ]; then
    echo "Lock file exists! Exiting."
    exit 1
fi


# Temporarily disable script
#exit 1


echo Getting lock...
touch $LOCK_FILE


echo Getting size to backup and total size...
RSYNC_CMD="/usr/bin/nice -n 19 \
rsync "${RSYNC_OPTS[@]}" -n --log-file=$PRELOG_PATH "${RSYNC_ARGS}""
echo "RSYNC_CMD: $RSYNC_CMD"
OUTPUT=$( eval "${RSYNC_CMD}" )
checkresult $?

SIZETOBACKUP=`echo "$OUTPUT" | grep "Total transferred file size" | \
awk '{print $5}' | sed 's/,//g'`
echo "SIZETOBACKUP: $SIZETOBACKUP"
echo $SIZETOBACKUP >$SIZETOBACKUP_PATH

TOTALSIZE=`echo "$OUTPUT" | grep "Total file size" | awk '{print $4}' | \
sed 's/,//g'`
echo "TOTALSIZE: $TOTALSIZE"
echo $TOTALSIZE >$TOTALSIZE_PATH


echo Starting actual backup using rsync...
RSYNC_CMD="/usr/bin/nice -n 19 \
rsync "${RSYNC_OPTS[@]}" --log-file=$PRELOG_PATH "${RSYNC_ARGS}""
echo "RSYNC_CMD: $RSYNC_CMD"
OUTPUT=$( eval "${RSYNC_CMD}" )
checkresult $?


echo Releasing lock...
rm $LOCK_FILE
