#/!/usr/bin/env python

'''
Automatically downloads wanted packs from irc xdcc bots.
'''

import os
import re
import sys
import time
import errno
import shlex
import socket
import signal
import argparse
import subprocess
import ConfigParser
from datetime import datetime

DOWNLOADING = False


def leave_irc(irc):
    'Sends a quit command to the server and exits'
    irc.send('QUIT :bye')
    sys.exit(0)


def child_died(*_):
    'Signal from child that the current file is done being downloaded'
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
    log_write(log, 'SENDING MSG: %s\n' % msg)
    irc.send(msg + '\r\n')


def log_write(logfile, msg, debug=False):
    'Writes a log to the logfile as well as print to stdout in debug mode'
    if debug:
        print msg.rstrip('\n')
    if not msg.endswith('\n'):
        logfile.write('%s\n' % msg)
    else:
        logfile.write(msg)


def get_packlist(irc, xdccbot, file_name, log, file_prefix):
    'Acquires a list of packs a bot and search for files'

    irc.send('PRIVMSG %s :xdcc send -1\r\n' % xdccbot)
    print 'Acquiring Packlist'
    text = ''
    while True:
        text = irc.recv(4096)
        log_write(log, text)
        if '\x01DCC SEND' in text:
            break
        elif 'No such nick/channel' in text:
            print >> sys.stderr, 'Bot %s not found.' % xdccbot
            sys.exit(1)
        elif 'PING' in text:
            pong(irc, text, log)
    args = create_args_for_subprocess(text, file_prefix)
    try:
        subprocess.check_output(args)
    except subprocess.CalledProcessError as err:
        print >> sys.stderr, 'Fatal Error. See log.'
        log_write(log, str(err))
        sys.exit(1)
    with open(args[1], 'r') as packlist:
        file_name_split = file_name.split()
        download_queue = []
        for line in packlist:
            if all(word.lower() in line.lower() for word in file_name_split):
                pack_number = re.match('#([0-9]+) ', line)
                if pack_number:
                    pack_number = pack_number.group(1)
                else:
                    print >> sys.stderr, 'Pack name is too generic. Try again'
                    sys.exit(1)
                download_queue.append(int(pack_number))
    os.remove(args[1])
    if not download_queue:
        log_write(log, 'nothing found')
        print 'Nothing found'
        sys.exit(0)
    return download_queue


def pong(irc, text, log):
    'The "heartbeat" letting the server know we are still alive'
    log_write(log, 'Sending ping response\n')
    irc.send('PONG ' + text.split()[1] + '\r\n')


def create_args_for_subprocess(data, file_prefix):
    '''
    Data (hopefully) comes in with the form of:

        :botname!botmsg PRIVMSG mynick :\x01DCC SEND file addr port size\x01

    The subprocess requires the file name, remote address, remote port, file
    size, process to notify when completed, and obviously the process to run.
    '''

    if not file_prefix.endswith('/'):
        file_prefix = file_prefix + '/'
    start = data.index('SEND') + 5  # index just after the 'SEND ' in the data
    end = len(data)
    substr = data[start:end].replace('\x01', '')
    split_substr = shlex.split(substr)
    split_substr[0] = file_prefix + split_substr[0]
    split_substr.insert(0, './dcc.py')
    return split_substr


def spawn_download(data, file_prefix):
    'Assumes data will be sent in as a ctcp reply from the bot'
    args = create_args_for_subprocess(data, file_prefix)
    subprocess.Popen(args)


def process_forever(irc, xdccbot, log, download_queue, dest):
    'loop infinitely reading from server - blocks'
    global DOWNLOADING

    while True:
        if not DOWNLOADING:
            initiate_download(irc, log, xdccbot, download_queue)
            DOWNLOADING = True
        # when the child sends a signal marking it's completion, this function
        # may get interrupted and raise EINTR - we want to ignore that
        try:
            text = irc.recv(4096)
        except socket.error as err:
            if err.errno != errno.EINTR:
                raise
            text = 'recv interrupted by child\n'
        log_write(log, text)
        if 'PING' in text:
            pong(irc, text, log)
        if '\x01DCC SEND' in text:
            spawn_download(text, dest)
        if DOWNLOADING and all(wrd in text for wrd in ['NOTICE', 'position']):
            index = text.rindex('position') + 9
            index = text[index]
            if int(index) != 1:
                print 'Stuck in queue - position %s' % index
        log.flush()


def ask_user_for(something):
    'Prompts user for data'
    try:
        return raw_input('%s not given. Please provide or press Control C to'
                         ' quit: ' % something)
    except KeyboardInterrupt:
        sys.exit(0)


def parse_args():
    'Parse and return command line and configuration file arguments'
    conf_parser = argparse.ArgumentParser(add_help=False)
    conf_parser.add_argument('-c', '--conf', dest='conf', metavar='FILE',
                             help='Location of lazydcc config file')
    args, remaining_args = conf_parser.parse_known_args()
    defaults = {'botnick': '',
                'server': '',
                'channel': '',
                'xdccbot': '',
                'packname': ''}

    if args.conf:
        config = ConfigParser.SafeConfigParser()
        config.read(args.conf)
        try:
            defaults = dict(config.items('lazydcc'))
        except ConfigParser.NoSectionError:
            print >> sys.stderr, 'Bad configuration file'

    parser = argparse.ArgumentParser(parents=[conf_parser],
                                     description='Download files from xdcc '
                                                 'bot based on filename.')
    parser.set_defaults(**defaults)
    parser.add_argument('-m', '--bot-name', help='Bot name to download files',
                        dest='botnick')
    parser.add_argument('-s', '--server', help='Server name to connect to',
                        dest='server')
    parser.add_argument('-a', '--channel', help='Channel name to connect to',
                        dest='channel')
    parser.add_argument('-b', '--xdccbot', help='Bot name to get packs from',
                        dest='xdccbot')
    parser.add_argument('-n', '--pack-name', help='Pack to download',
                        dest='packname', default='default')
    parser.add_argument('-d', '--destination', help='Location to download to',
                        dest='destination_dir')
    parser.add_argument('-p', '--packnumbers',
                        help='Comma separated pack numbers to download',
                        dest='packnumbers', default='default')
    args = parser.parse_args(remaining_args)
    return args


def setup():
    'Parses options from commandline and optionally the config file'
    args = parse_args()
    if not args.conf:
        args.conf = 'ignore'
    if not args.destination_dir:
        args.destination_dir = './'

    return tuple(ask_user_for(i[0].title()) if not i[1] or i[1] == 'default'
                 else i[1] for i in args._get_kwargs())


def register(irc, server, botnick, channel, log):
    'I am too lazy to figure out the responses - also sometimes fails'
    try:
        irc.connect((server, 6667))
    except socket.gaierror:
        print >> sys.stderr, 'Bad server name'
        sys.exit(1)
    irc.send('NICK ' + botnick + '\n')
    irc.send('USER ' + botnick + ' ' + botnick + ' ' + botnick + ' :hi\n')
    irc.settimeout(2)
    while True:  # https://github.com/mac-reid/lazydcc/issues/1
        try:
            msg = irc.recv(4096)
        except socket.timeout:
            break
        log_write(log, msg)
        if msg.startswith('PING'):
            pong(irc, msg, log)

        # https://github.com/mac-reid/lazydcc/issues/5
        if 'Nickname is already in use' in msg:
            botnick += '_'
            irc.send('NICK ' + botnick + '\n')
    irc.settimeout(None)
    print 'Joining %s' % channel
    irc.send('JOIN ' + channel + '\n')
    time.sleep(2)


def begin():
    'Initialization'
    botnick, channel, _, dest, pack_name, packnumbers, server, xdccbot = setup()

    if not channel.startswith('#'):
        channel = '#%s' % channel

    signal.signal(signal.SIGUSR1, child_died)

    logfile = 'logs/irc_%s.log' % str(datetime.now().time())
    if not os.path.isdir('logs'):
        if os.path.isfile('logs'):  # because who knows
            print >> sys.stderr, 'Cannot create directory for logging'
            print >> sys.stderr, 'File logs exists at %s' % os.getcwd()
            print >> sys.stderr, 'Logging to %s/tmplogfile' % os.getcwd()
            logfile = 'tmplogfile'
        else:
            os.mkdir('logs')

    with open(logfile, 'w') as mylog:
        try:
            irc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            print 'Connecting to %s' % server
            register(irc, server, botnick, channel, mylog)
            if packnumbers and packnumbers != 'default':
                if re.match(r'^(\d+,|\d+)+$', packnumbers):
                    download_queue = [int(a) for a in packnumbers.split(',')]
                else:
                    print >> sys.stderr, 'Packnumbers must be numbers separated by commas (1,2,3,4)'
                    sys.exit(1)
            else:
                download_queue = get_packlist(irc, xdccbot, pack_name, mylog, dest)
            process_forever(irc, xdccbot, mylog, download_queue, dest)
        except KeyboardInterrupt:
            sys.exit(0)


if __name__ == '__main__':
    begin()
