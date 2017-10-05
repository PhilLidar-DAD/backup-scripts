import logging
import os

# Push config
# Unset DST_HOST (''/None) to perform local only rsync
DST_HOST = 'aquinas.local'
DST_REMOTE = 'aquinas'

SRC_BASE = '/mnt'
DST_BASE = '/mnt'

SRC_USER = DST_USER = 'root'

DST_USER_HOST = DST_USER + '@' + DST_HOST

# Notes:
#
# rsync from:
#
# CentOS 7 doesn't support '-A' (ACLs)
#
# rsync to:
#
# FreeNAS doesn't support progress2, and Compression=no -x
# '--info=progress2', -o Compression=no -x
#
# CentOS 7 doesn't support arcfour, use aes128-gcm@openssh.com
#
RSYNC_OPTS = ['-aiSsA',
              '--stats',
              '--timeout=300',
              '--ignore-errors',
              "-e'ssh -T -c aes128-gcm@openssh.com'"]

RCLONE_OPTS = ['--size only',
			   '--stats 1m',
			   '--timeout 30s',
			   '--skip-links',
			   '-v',
			   '--transfers 16'
				]

IS_UPDATE = True
if IS_UPDATE:
    RSYNC_OPTS += ['-u']
else:
    RSYNC_OPTS += ['--del']

LOG_LEVEL = logging.DEBUG
CONS_LOG_LEVEL = logging.INFO
FILE_LOG_LEVEL = logging.DEBUG

BASEDIR = os.path.dirname(os.path.abspath(__file__))

APP_DIRS = {
    'RSYNC_PRELOG_DIR': os.path.join(BASEDIR, 'rsync_prelog'),
    'RSYNC_CURLOG_DIR': os.path.join(BASEDIR, 'rsync_curlog'),
    'SIZETOBACKUP_DIR': os.path.join(BASEDIR, 'sizetobackup'),
    'TOTALSIZE_DIR': os.path.join(BASEDIR, 'totalsize'),
    'LOCK_DIR': os.path.join(BASEDIR, 'lock'),
    'LOG_DIR': os.path.join(BASEDIR, 'log'),
}

NICE_CMD = ['/usr/bin/nice', '-n', '19']

RSYNC_CMD = ['/usr/local/bin/rsync']

RCLONE_CMD = ['/usr/local/bin/rclone']

SSH_CMD = ['/usr/bin/ssh', DST_USER_HOST]

# Worker settings
# CPU_USAGE = .5
# WORKER_COUNT = int(multiprocessing.cpu_count() * CPU_USAGE)
WORKER_COUNT = 4
