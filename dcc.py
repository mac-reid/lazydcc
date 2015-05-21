#!/usr/bin/env python

'''
Usage:

    dcc.py filename address port filesize

    where address is a 32 bit integer representing the ip address of the client
          port is the listening port on the remote client
          filesize if the number of bytes to read from the remote client
          filename is the name of the file to write on the local disk
          signalpid is the pid to send SIGUSR1 when completed
'''

import os
import sys
import time
import socket
import struct


def get_columns():
    'why is this so hard - http://stackoverflow.com/a/566752'
    env = os.environ

    def ioctl_gwinsz(fd):
        try:
            import fcntl
            import termios
            cr = struct.unpack('hh', fcntl.ioctl(fd, termios.TIOCGWINSZ,
                               '1234'))
        except:
            return
        return cr
    cr = ioctl_gwinsz(0) or ioctl_gwinsz(1) or ioctl_gwinsz(2)
    if not cr:
        try:
            fd = os.open(os.ctermid(), os.O_RDONLY)
            cr = ioctl_gwinsz(fd)
            os.close(fd)
        except:
            pass
    if not cr:
        cr = (env.get('LINES', 24), env.get('COLUMNS', 80))
    return int(cr[1])


def int2ip(addr):
    'convert 32 bit addr into dotted quad ip address string'
    return socket.inet_ntoa(struct.pack("!I", addr))


def sizeof_fmt(num):
    'Print file size in human readable form'
    for size in ['By', 'KB', 'MB', 'GB', 'TB']:
        if num < 1000.0:
            return '%3.1f %s' % (num, size)
        num /= 1000.0


def format_eta(total_bytes, bytes_received, speed):
    'format time till download complete'
    time_left = (total_bytes - bytes_received) // speed
    ret = 'ETA %02d sec' % time_left
    return ret


def print_progress(bytes_received, total_bytes, start):
    'This is not pretty'

    time_so_far = time.time() - start
    if time_so_far <= 0:
        time_so_far = 0.1
    bps = bytes_received // time_so_far

    percent = bytes_received / float(total_bytes)
    strpercent = str(int(percent * 100)) + '%'
    strpercent = strpercent.ljust(4)
    form_bts_rcvd = sizeof_fmt(bytes_received)
    speed = sizeof_fmt(bps)
    speed += '/s'
    eta = format_eta(total_bytes, bytes_received, bps)
    total_bts_len = len(str(sizeof_fmt(total_bytes)))

    # minus 7 for spaces and square brackets
    bar_len = get_columns() - len(strpercent) - total_bts_len - len(speed) - \
        len(eta) - len(str(time_so_far)) - 8
    equals = '=' * int(bar_len * percent)
    spaces = ' ' * (bar_len - len(equals))

    prog_bar = '[%s%s]' % (equals, spaces)
    newbar = "{}{} {}  {}  {} {}".format(strpercent, prog_bar,
                                         form_bts_rcvd.rjust(total_bts_len),
                                         speed, eta, time_so_far)
    print newbar
    sys.stdout.flush()


def signal_parent():
    'because signals are neat'
    try:
        os.kill(os.getppid(), 10)    # 10 -> sigusr1
    except OSError as err:
        if err.errno == 3:
            print 'Parent is dead?'
        else:
            raise err


def begin():
    'Connects to remote client and downloads the given file'
    if len(sys.argv) < 5:
        print 'not enough arguments'
        sys.exit(1)

    filename = sys.argv[1].replace(' ', '_')
    remote_address = sys.argv[2]
    remote_port = sys.argv[3]
    filesize = sys.argv[4]

    dcc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    dcc.settimeout(60)

    intip = int(remote_address)
    server = int2ip(intip)

    dcc.connect((server, int(remote_port)))

    if os.path.isfile(filename):
        print '%s exists on disk.' % os.path.basename(filename)
        signal_parent()
        dcc.close()
        sys.exit(0)

    bytes_received = 0
    total_bytes = int(filesize)

    # maybe print every 2 seconds?
    with open(filename, 'w') as out:
        start = time.time()
        print 'Downloading %s' % os.path.basename(filename)
        data = dcc.recv(4096)
        count = 50
        while True:
            bytes_received += len(data)
            out.write(data)
            if count == 1000:
                print_progress(bytes_received, total_bytes, start)
                count = 0
            else:
                count += 1
            if bytes_received == total_bytes:
                if count != 0:
                    print_progress(bytes_received, total_bytes, start)
                signal_parent()
                dcc.close()
                print ''
                break
            try:
                data = dcc.recv(min(total_bytes - bytes_received, 4096))
            except socket.timeout:
                signal_parent()
                print >> sys.stderr, 'Timeout downloading %s' % filename


if __name__ == '__main__':
    begin()
