"""
Program used to monitor the operation of eth-proxy and restart it when needed.
"""

import os
import time
import sys
import subprocess
import signal

# SETTINGS
# --------
# location of eth-proxy log file
LOG_FILE = 'eth-proxy/log/proxy.log'
# location of eth-proxy pid file
PID_FILE = 'eth-proxy/eth-proxy.pid'
# location of a script starting the eth-proxy
PROXY_SCRIPT_PATH = 'bin/ethproxy.sh'

# number of allowed REJECTED messages in the past 10 minutes
NUM_REJECTED = 2

SLEEP_DURATION = 30  # [s]


def tail(f, lines=20):
    total_lines_wanted = lines

    BLOCK_SIZE = 1024
    f.seek(0, 2)
    block_end_byte = f.tell()
    lines_to_go = total_lines_wanted
    block_number = -1
    blocks = []  # blocks of size BLOCK_SIZE, in reverse order starting
    # from the end of the file
    while lines_to_go > 0 and block_end_byte > 0:
        if block_end_byte - BLOCK_SIZE > 0:
            # read the last block we haven't yet read
            f.seek(block_number * BLOCK_SIZE, 2)
            blocks.append(f.read(BLOCK_SIZE))
        else:
            # file too small, start from beginning
            f.seek(0, 0)
            # only read what was not read
            blocks.append(f.read(block_end_byte))
        lines_found = blocks[-1].count('\n')
        lines_to_go -= lines_found
        block_end_byte -= BLOCK_SIZE
        block_number -= 1
    all_read_text = ''.join(reversed(blocks))
    return '\n'.join(all_read_text.splitlines()[-total_lines_wanted:])


def check_exists(filepath):
    if not os.path.exists(filepath):
        print 'File <{}> does not exist'.format(filepath)
        sys.exit(1)


def check_running(process_pid):
    if process_pid is None:
        raise ValueError

    try:
        os.kill(process_pid, 0)
    except OSError:
        return False
    else:
        return True


def restart_proxy(pid):
    # kill the proxy
    print 'Killing pid {}'.format(pid)
    os.kill(pid, signal.SIGTERM)

    # empty the log file
    print 'Emptying log file'
    open(LOG_FILE, 'w').close()

    # start the proxy
    print 'Starting the proxy script {}'.format(PROXY_SCRIPT_PATH)
    subprocess.call([PROXY_SCRIPT_PATH])
    break



if __name__ == "__main__":

    # check if files exist
    check_exists(LOG_FILE)
    # checkExists(PID_FILE)  # this file might not exist in the beginning
    check_exists(PROXY_SCRIPT_PATH)

    # run forever
    while True:
        log_contents, pid = None, None
        n_rejected = 0

        if os.path.exists(PID_FILE):
            with open(PID_FILE, 'r') as pidfile:
                pid = int(pidfile.read())

        with open(LOG_FILE, 'r') as logfile:
            log_contents = tail(logfile, lines=50)

        # I assume proxy app will spam to restart it, so no special checks are needed here
        for line in log_contents.splitlines():
            if 'Please restart proxy' in line:
                print line

                restart_proxy(pid)

            # count the rejected shares and restart the proxy if the number exceeds a certain threshold
            if 'REJECTED' in line:
                n_rejected += 1

                print line

                if n_rejected == NUM_REJECTED:
                    restart_proxy(pid)
                    n_rejected = 0


        # start proxy if its not running by some chance
        if pid is None or check_running(pid) is False:
            subprocess.call([PROXY_SCRIPT_PATH])

        time.sleep(SLEEP_DURATION)
