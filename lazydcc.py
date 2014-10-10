#!/usr/bin/env python

'''
Automatically downloads wanted pack from irc xdcc bots.

Should probably clean this up and use a config file or something because
this source is bad... but that would require effort.
'''

import os
import re
import sys
import time
import shlex
import socket
import signal
import subprocess
from datetime import datetime

DOWNLOADING = False


def usage():
    '''usage: python lazydcc.py server channel botname file

Download files from xdcc bot based on file. File must be a quoted space
delimited string in which each word must be in the pack name before
lazydcc will download it.'''
    print usage.__doc__


def leave_irc(irc):
    'Sends a quit command to the server and exits'
    irc.send('QUIT :bye')
    sys.exit(0)


def child_died(*_):
    'Signal from subprocess that the current file is down being downloaded'
    global DOWNLOADING
    DOWNLOADING = False


def initiate_download(irc, log, xdccbot, download_queue):
    'Send a private message to the bot to initiate a download'

    if download_queue:
        pack = download_queue[0]
        del download_queue[0]
    else:
        leave_irc(irc)

    msg = 'PRIVMSG %s :xdcc send %d' % (xdccbot, pack)
    log.write('SENDING MSG: %s\n' % msg)
    irc.send(msg + '\r\n')


def acquire_packlist(irc, xdccbot, file_name, log):
    'Acquires a list of packs a bot and search for files'

    time.sleep(2)
    irc.send('PRIVMSG %s :xdcc send -1\r\n' % xdccbot)
    text = ''
    while True:
        text = irc.recv(4096)
        log.write(text)
        if '\x01DCC SEND' in text:
            break
        elif 'No such nick/channel' in text:
            print >> sys.stderr, 'Bot %s not found.' % xdccbot
            sys.exit(1)
    args = create_args_for_subprocess(text)
    try:
        subprocess.check_output(args)
    except subprocess.CalledProcessError as err:
        print >> sys.stderr, 'Fatal Error. See log.'
        log.write(str(err))
        sys.exit(0)
    with open(args[1], 'r') as packlist:
        file_name_split = file_name.split()
        download_queue = []
        for line in packlist:
            if all(word.lower() in line.lower() for word in file_name_split):
                pack_number = re.search('#([0-9]+) ', line).group(1)
                download_queue.append(int(pack_number))
    os.remove(args[1])
    if not download_queue:
        log.write('nothing found')
        print 'Nothing found'
        sys.exit(0)
    return download_queue


def pong(irc, text):
    'The "heartbeat" letting the server know we are still alive'
    irc.send('PONG ' + text.split()[1] + '\r\n')


def create_args_for_subprocess(data):
    '''
    Data (hopefully) comes in with the form of:

        :botname!botmsg PRIVMSG mynick :\x01DCC SEND file addr port size\x01

    The subprocess requires the file name, remote address, remote port, file
    size, process to notify when completed, and obviously the process to run.
    '''

    file_prefix = './'
    start = data.index('SEND') + 5  # index just after the 'SEND ' in the data
    end = len(data)
    substr = data[start:end].replace('\x01', '')
    split_substr = shlex.split(substr)
    split_substr[0] = file_prefix + split_substr[0]
    split_substr.append(str(os.getpid()))
    split_substr.insert(0, './dcc.py')
    return split_substr


def spawn_download(data):
    'Assumes data will be sent in as a ctcp reply from the bot'
    args = create_args_for_subprocess(data)
    subprocess.Popen(args)


def process_forever(irc, xdccbot, log, download_queue):
    'loop infinitely reading from server - blocks'
    global DOWNLOADING

    while True:
        if not DOWNLOADING:
            initiate_download(irc, log, xdccbot, download_queue)
            DOWNLOADING = True
        text = irc.recv(4096)
        log.write(text)
        if text.startswith('PING'):
            pong(irc, text)
        elif '\x01DCC SEND' in text:
            spawn_download(text)


def setup():
    'prepares variables - pep really wants me to use docstrings'
    botnick = 'colourfulfrown'
    if sys.argv[0].endswith('python'):
        del(sys.argv[0])
    if len(sys.argv) == 5:
        server = sys.argv[1]
        channel = sys.argv[2]
        xdccbot = sys.argv[3]
        file_name = sys.argv[4]
    else:
        usage()
        sys.exit(0)
    if not channel.startswith('#'):
        channel = '#%s' % channel
    return server, channel, xdccbot, botnick, file_name


def register(irc, server, botnick, channel):
    'sleep, I am too lazy to figure out the responses - also sometimes fails'
    irc.connect((server, 6667))
    irc.send('NICK ' + botnick + '\n')
    irc.send('USER ' + botnick + ' ' + botnick + ' ' + botnick + ' :hi\n')
    time.sleep(2)
    irc.send('JOIN ' + channel + '\n')
    time.sleep(2)


def begin():
    'Initialization'
    # because global variables are in caps
    server, channel, xdccbot, botnick, file_name = setup()

    signal.signal(signal.SIGUSR1, child_died)

    irc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    print 'Connecting to', server

    register(irc, server, botnick, channel)
    print 'Joining %s' % channel

    logfile = 'logs/irc_' + str(datetime.now().time()) + '.log'
    if not os.path.isdir('logs'):
        if os.path.isfile('logs'):  # because who knows
            try:
                os.remove('logs')
            except OSError:
                print >> sys.stderr, 'Cannot create logs directory.'
                sys.exit(1)
        os.mkdir('logs')

    with open(logfile, 'w') as mylog:
        try:
            download_queue = acquire_packlist(irc, xdccbot, file_name, mylog)
            process_forever(irc, xdccbot, mylog, download_queue)
        except KeyboardInterrupt:
            sys.exit(0)

if __name__ == '__main__':
    begin()
