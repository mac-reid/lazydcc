package main

import (
	"fmt"
	"time"
)

const servername = ""

func run() {
	irc := NewIRC(true)
	fmt.Printf("connect returns: %v\n", irc.Connect(servername))
	time.Sleep(3 * time.Second)
	fmt.Println(irc.Register("colourfulfrown"))
}

func main() {
	run()
}
