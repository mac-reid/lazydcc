A bad irc bot to download stuff from xdcc bots.

Built and tested with python 2.7 on Linux. Uses only builtin modules. Sometimes fails.

Usage:

    usage: lazydcc.py [-h] [-c FILE] [-m BOTNICK] [-s SERVER] [-a CHANNEL]
                      [-b XDCCBOT] [-n PACKNAME] [-d DESTINATION_DIR]

    Download files from xdcc bot based on filename.

    optional arguments:
      -h, --help            show this help message and exit
      -c FILE, --conf FILE  Location of lazydcc config file
      -m BOTNICK, --bot-name BOTNICK
                            Bot name to download files
      -s SERVER, --server SERVER
                            Server name to connect to
      -a CHANNEL, --channel CHANNEL
                            Channel name to connect to
      -b XDCCBOT, --xdccbot XDCCBOT
                            Bot name to get packs from
      -n PACKNAME, --pack-name PACKNAME
                            Pack to download
      -d DESTINATION_DIR, --destination DESTINATION_DIR
                            Location to download to
      -p PACKNUMBERS, --packnumbers PACKNUMBERS
                            Comma separated pack numbers to download


The packnumbers and packname are mutually exclusive. If you provide packnumbers, the packname argument will be ignored.

Optionally set options in lazydcc.conf - there are a whole 5 options to set.
These options are overridden by command line flags if present.

Example run:

    ~ python lazydcc.py
    Botnick not given. Please provide or press Control C to quit: colourfulfrown
    Channel not given. Please provide or press Control C to quit: insertinfohere
    Packname not given. Please provide or press Control C to quit: make sure it is somewhat unique
    Packnumbers not given. Please provide or press Control C to quit: 1,2,3,4,5
    Server not given. Please provide or press Control C to quit: irc.something.blah
    Xdccbot not given. Please provide or press Control C to quit: IServePacks

Examples of providing arguments:

    ~ cat lazydcc.conf
    [lazydcc]
    server = irc.example.net
    channel = example
    botnick = colourfulfrown
    xdccbot = IServePacks
    destination_dir = /home/me/packs/
    ~ python lazydcc.py -c lazydcc.conf -n 'some pack by name'
    ~ python lazydcc.py -c lazydcc.conf -p '1,2,3,4,5'


