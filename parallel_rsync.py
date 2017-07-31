#!/usr/bin/env python2

import argparse
import errno
import fcntl
import logging
import logging.handlers
import multiprocessing
import os
import subprocess
import sys

from pprint import pprint

from settings import *

logger = logging.getLogger()


def parse_arguments():
    """Parse arguments.

    Returns:
        args from parse_args()
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('-v', '--verbose', action="store_true")
    parser.add_argument('src_dir')
    args = parser.parse_args()
    return args


def setup_logging(logfile, is_verbose=False):
    """ Setup logging.

    Args:
        logfile (str): Path to the log file
        is_verbose (bool, optional): If logging would be verbose or not
    """

    logger.setLevel(LOG_LEVEL)
    formatter = logging.Formatter('[%(asctime)s] \
(%(levelname)s,%(lineno)d)\t: %(message)s')

    # Check verbosity for console
    if is_verbose:
        global CONS_LOG_LEVEL
        CONS_LOG_LEVEL = logging.DEBUG

    # Setup console logging
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(CONS_LOG_LEVEL)
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    # Setup file logging
    fh = logging.handlers.RotatingFileHandler(logfile, backupCount=5)
    fh.doRollover()
    fh.setLevel(FILE_LOG_LEVEL)
    fh.setFormatter(formatter)
    logger.addHandler(fh)


def acquire_lock(lockfile_path):
    """Try acquiring lock.

    Args:
        lockfile_path (str): Path to the lock file

    Returns:
        file object: Lock file
    """
    lockfile = open(lockfile_path, 'w')
    try:
        fcntl.lockf(lockfile, fcntl.LOCK_EX | fcntl.LOCK_NB)
        print 'Lock acquired!'
    except IOError:
        print 'Cannot acquire lock! Script might already be running.'
        print 'Exiting...'
        exit(1)
    return lockfile


def release_lock(lockfile, lockfile_path):
    """Release lock.

    Args:
        lockfile (:obj:`File`): Lock file object
        lockfile_path (str): Path to the lock file
    """
    logger.info('Releasing lock...')
    lockfile.close()
    if os.path.isfile(lockfile_path):
        # Delete lock file
        os.remove(lockfile_path)


def escape_dirpath(dir_path):
    return dir_path.replace(' ', '\ ')


def sanitize_dirpath(dir_path):
    return dir_path.replace(os.sep, '_').replace(' ', '_')


def prepare_app_dirs(args):
    """Prepare directories to be used by the script.

    Args:
        args (:obj:`Namespace`): Script arguments

    Returns:
        dictionary of application file paths
    """

    # Create app dirs if they don't exist
    for opt_dir, opt_dir_path in APP_DIRS.viewitems():
        if not os.path.isdir(opt_dir_path):
            mkdir_p(opt_dir_path)

    # Get app paths
    esc_src_dir = sanitize_dirpath(args.src_dir)
    logger.debug('esc_src_dir: %s', esc_src_dir)

    app_paths = {
        'rsync_prelog': os.path.join(APP_DIRS['RSYNC_PRELOG_DIR'],
                                     esc_src_dir + '.log'),
        'rsync_curlog': os.path.join(APP_DIRS['RSYNC_CURLOG_DIR'],
                                     esc_src_dir + '.log'),
        'sizetobackup_path': os.path.join(APP_DIRS['SIZETOBACKUP_DIR'],
                                          esc_src_dir),
        'totalsize_path': os.path.join(APP_DIRS['TOTALSIZE_DIR'],
                                       esc_src_dir),
        'lockfile_path': os.path.join(APP_DIRS['LOCK_DIR'], esc_src_dir),
        'logfile': os.path.join(APP_DIRS['LOG_DIR'], esc_src_dir + '.log')
    }

    return app_paths


def mkdir_p(path):
    """mkdir -p <path>.

    Args:
        path: Directory path
    """
    try:
        os.makedirs(path)
    except OSError as exc:  # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise


def get_srcdst_dirs(src_dir):
    """Get source and destination directory paths.

    Args:
        src_dir (str): Source directory

    Returns:
        Source and destination directory paths

    """
    src_dirpath = os.path.join(SRC_BASE, src_dir)
    if not os.path.isdir(src_dirpath):
        logger.error('%s does not exist! Exiting.', src_dirpath)
        exit(1)
    dst_dirpath = os.path.join(DST_BASE, src_dir)
    logger.info('Source dir path: %s', src_dirpath)
    logger.info('Dest dir path: %s', dst_dirpath)
    return src_dirpath, dst_dirpath


def mk_dstdir(dst_dirpath):
    """Create remote directory.

    Args:
        dst_dirpath (str): Remote destination directory
    """
    ssh_cmd = SSH_CMD + ["'mkdir -p " + escape_dirpath(dst_dirpath) + "'"]
    logger.debug('ssh_cmd: %s', ' '.join(ssh_cmd))
    try:
        subprocess.call(' '.join(ssh_cmd), shell=True)
    except subprocess.CalledProcessError:
        logger.exception('Error creating remote directory! Exiting.')
        exit(1)


def backup_old_logfile(logfile_path):
    if os.path.isfile(logfile_path):
        os.rename(logfile_path, logfile_path + '.old')


def get_backup_sizes(src_dirpath, dst_dirpath, rsync_prelog):
    """Get size to backup and total size.

    Args:
        src_dirpath (str): Source directory path
        dst_dirpath (str): Remote directory path
        rsync_prelog (str): The path to the rsync prelog file
    """

    def get_size(line, size_path):
        """Get size from line and output to file.

        Args:
            line (str): Line from rsync output
            size_path (str): Path to the size file
        """
        size_bytes = int(line.split()[-2].replace(',', ''))
        with open(size_path, 'w') as open_file:
            open_file.write(str(size_bytes))
        return size_bytes

    # Backup old log file
    backup_old_logfile(rsync_prelog)

    rsync_cmd = (NICE_CMD + RSYNC_CMD + RSYNC_OPTS +
                 ['-rn',
                  '--log-file=' + rsync_prelog,
                  escape_dirpath(src_dirpath + os.sep),
                  DST_USER_HOST + ":'" + escape_dirpath(dst_dirpath + os.sep)
                  + "'"])
    logger.debug('rsync_cmd: %s', ' '.join(rsync_cmd))
    try:
        rsync_out = subprocess.check_output(' '.join(rsync_cmd), shell=True)
    except subprocess.CalledProcessError:
        logger.exception('Error running rsync -n! Exiting.')
        exit(1)
    for l in rsync_out.split('\n'):
        if 'Total file size' in l:
            size_bytes = get_size(l, APP_PATHS['totalsize_path'])
            logger.info('Total size: %.2e GB', size_bytes / (1024. ** 3))
        elif 'Total transferred file size' in l:
            size_bytes = get_size(l, APP_PATHS['sizetobackup_path'])
            logger.info('Size to backup: %.2e TB', size_bytes / (1024. ** 4))
            break


def start_backup(srcbase_dirpath, dstbase_dirpath):
    """Starts concurrent backup using workers.

    Args:
        srcbase_dirpath (str): Base source directory path (the script argument)
        dstbase_dirpath (str): Base dest. directory path
    """

    # Traverse source dir path concurrently
    manager = multiprocessing.Manager()
    pool = multiprocessing.Pool(processes=WORKER_COUNT)
    src_dirpaths = manager.Queue()

    # Traverse directories
    counter = 1
    dir_count = 1
    pool.apply_async(backup_worker, (srcbase_dirpath, srcbase_dirpath,
                                     dstbase_dirpath, src_dirpaths))

    while counter > 0:
        src_dirpath = src_dirpaths.get()
        if src_dirpath == 'no-dir':
            counter -= 1
        else:
            counter += 1
            dir_count += 1
            pool.apply_async(backup_worker, (srcbase_dirpath, src_dirpath,
                                             dstbase_dirpath, src_dirpaths))

    pool.close()
    pool.join()
    logger.info('dir_count: %s', dir_count)


def backup_worker(srcbase_dirpath, src_dirpath, dstbase_dirpath, src_dirpaths):
    """Backup worker: backups directory from source to destination.

    Also adds subdirectories to queue.

    Args:
        srcbase_dirpath (str): Base source directory path (the script argument)
        src_dirpath (str): Source directory path for rsync
        dstbase_dirpath (str): Base dest. directory path
        src_dirpaths (str): Source directory paths queue
    """

    # Find directories within source directory and add them to queue
    try:
        for i in sorted(os.listdir(src_dirpath)):
            # logger.debug('i: %s', i)
            i_path = os.path.join(src_dirpath, i)
            # logger.debug('i_path: %s', i_path)
            if os.path.isdir(i_path):
                src_dirpaths.put(i_path)
    except Exception:
        logger.exception('Error finding directories within %s!', src_dirpath)
    finally:
        src_dirpaths.put('no-dir')

    # Start backup of source to destination directory
    dst_dirpath = src_dirpath.replace(srcbase_dirpath, dstbase_dirpath)
    logger.info('rsync %s %s', src_dirpath, dst_dirpath)

    # Create remote destination directory
    mk_dstdir(dst_dirpath)

    # Get rsync log path
    rsync_curlog = os.path.join(APP_DIRS['RSYNC_CURLOG_DIR'],
                                sanitize_dirpath(src_dirpath
                                                 .replace(SRC_BASE, ''))
                                + '.log')
    # Backup old log file
    backup_old_logfile(rsync_curlog)

    # Get rsync cmd
    rsync_cmd = (NICE_CMD + RSYNC_CMD + RSYNC_OPTS +
                 ['--log-file=' + rsync_curlog,
                  escape_dirpath(os.path.join(src_dirpath, '*')),
                  DST_USER_HOST + ":'" + escape_dirpath(dst_dirpath + os.sep)
                  + "'"])
    logger.debug('rsync_cmd: %s', ' '.join(rsync_cmd))

    # Run rsync
    try:
        rsync_out = subprocess.check_output(' '.join(rsync_cmd), shell=True)
    except subprocess.CalledProcessError:
        logger.exception('Error backing up: %s to %s!',
                         src_dirpath, dst_dirpath)


if __name__ == "__main__":

    # Parse arguments
    args = parse_arguments()

    # Prepare app dirs/paths
    APP_PATHS = prepare_app_dirs(args)

    # Acquire lock
    lockfile = acquire_lock(APP_PATHS['lockfile_path'])

    # Setup logging
    setup_logging(APP_PATHS['logfile'], args.verbose)

    # Get src & dst dirs
    src_dirpath, dst_dirpath = get_srcdst_dirs(args.src_dir)

    # Get backup sizes
    get_backup_sizes(src_dirpath, dst_dirpath, APP_PATHS['rsync_prelog'])

    # Start backup
    start_backup(src_dirpath, dst_dirpath)

    # Release lock
    release_lock(lockfile, APP_PATHS['lockfile_path'])
