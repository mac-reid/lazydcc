package main

import (
	"bufio"
	"crypto/tls"
	"errors"
	"fmt"
	"log"
	"net"
	"strings"
	"time"
)

// IRC does a shitty job handling communications
// between irc server and local system
type IRC struct {
	UseTLS bool
	nick   string
	server string
	pong   string
	socket net.Conn
	reader *bufio.Reader
	writer *bufio.Writer
	log    *log.Logger
}

func (irc *IRC) listen() error {
	for {
		msg, err := irc.reader.ReadString('\n')
		if err != nil {
			return err
		}
		irc.handleMsg(msg)
	}
}

func (irc *IRC) handleMsg(msg string) {
	fmt.Printf("Received: %s", msg)
	if strings.HasPrefix(msg, "PING") {
		addr := strings.Split(msg, ":")[1]
		if irc.pong != addr {
			irc.pong = addr
		}
		irc.Sendf("PONG :%s", irc.pong)
	}
}

// Send Send raw string
func (irc *IRC) Send(msg string) error {
	fmt.Printf("Sending: %s\n", msg)
	if _, err := irc.writer.WriteString(msg + "\r\n"); err != nil {
		return err
	}
	return irc.writer.Flush()
}

// Sendf Send raw formatted string
func (irc *IRC) Sendf(format string, a ...interface{}) error {
	return irc.Send(fmt.Sprintf(format, a...))
}

// DownloadPack foo
func (irc *IRC) DownloadPack(packid, botname string) error {
	return irc.Sendf("PRIVMSG %s :xdcc send %s", botname, packid)
}

// Connect foo
func (irc *IRC) Connect(servername string) error {
	irc.server = servername
	var err error
	var conn net.Conn
	if irc.UseTLS {
		config := tls.Config{}
		conn, err = tls.Dial("tcp", irc.server, &config)
		if err != nil {
			return err
		}
	} else {
		conn, err = net.Dial("tcp", irc.server)
		if err != nil {
			return err
		}
	}
	irc.socket = conn
	irc.reader = bufio.NewReader(conn)
	irc.writer = bufio.NewWriter(conn)
	go irc.listen()
	time.Sleep(5 * time.Second)
	return nil
}

// Register foo
func (irc *IRC) Register(nick string) error {
	if irc.writer == nil {
		return errors.New("not connected to IRC Server, call irc.Connect first")
	}
	if err := irc.Sendf("USER %s some host :%s", nick, nick); err != nil {
		return err
	}
	err := irc.Sendf("NICK %s", nick)
	return err
}

// NewIRC foo
func NewIRC(tls bool) *IRC {
	return &IRC{UseTLS: tls}
}
