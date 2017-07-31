import logging
import os
import multiprocessing

# Used for push config
# DST_HOST = 'aquinas.prd.dream.upd.edu.ph'
DST_HOST = 'localhost'

# SRC_BASE = '/mnt/FTP'
# DST_BASE = '/mnt/backup_pool/FTP'
SRC_BASE = '/root/backup_tests/a_dir/'
DST_BASE = '/root/backup_tests/b_dir/'

SRC_USER = DST_USER = 'root'

DST_USER_HOST = DST_USER + '@' + DST_HOST

RSYNC_OPTS = ['-lptgoDiSA', '--stats', '--timeout=300', '--ignore-errors',
              '--info=progress2',
              "-e'ssh -T -c aes128-gcm@openssh.com -o Compression=no -x'"]
# "-e'ssh -T -c arcfour -o Compression=no -x'"]

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

RSYNC_CMD = ['/usr/bin/rsync']

SSH_CMD = ['/usr/bin/ssh', DST_USER_HOST]

# Worker settings
# CPU_USAGE = .5
# WORKER_COUNT = int(multiprocessing.cpu_count() * CPU_USAGE)
WORKER_COUNT = 4
