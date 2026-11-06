package main

import (
	"bufio"
	"encoding/json"
	"fmt"
	"github.com/s-charvin/ai-delivery-kit/internal/delivery/runner/testdata/owner"
	"net"
	"os"
	"os/exec"
	"strings"
	"time"
)

func main() {
	switch os.Args[1] {
	case "orphan":
		cmd := exec.Command(os.Args[0], "leaf", os.Args[2])
		cmd.Stdout = os.Stdout
		cmd.Stderr = os.Stderr
		if err := cmd.Start(); err != nil {
			panic(err)
		}
		conn, err := net.Dial("tcp", os.Args[3])
		if err != nil {
			panic(err)
		}
		defer conn.Close()
		if _, err = bufio.NewReader(conn).ReadString('\n'); err != nil {
			os.Exit(9)
		}
	case "leaf":
		conn, err := net.Dial("tcp", os.Args[2])
		if err != nil {
			panic(err)
		}
		defer conn.Close()
		fmt.Fprintln(os.Stdout, "后代仍持有stdout")
		if _, err = bufio.NewReader(conn).ReadString('\n'); err != nil {
			os.Exit(9)
		}
		fmt.Fprintln(os.Stdout, "后代解除阻塞")
	case "tree":
		cmd := exec.Command(os.Args[0], "handshake", os.Args[2])
		if err := cmd.Run(); err != nil {
			os.Exit(8)
		}
	case "echo":
		cwd, _ := os.Getwd()
		json.NewEncoder(os.Stdout).Encode(map[string]any{"args": os.Args[2:], "cwd": cwd})
		fmt.Fprint(os.Stderr, "原生错误流🙂"+strings.Repeat("x", 2*1024*1024))
	case "fail":
		fmt.Fprintln(os.Stderr, "真实失败")
		os.Exit(7)
	case "timeout":
		for {
			time.Sleep(time.Hour)
		}
	case "touch":
		if err := os.WriteFile(os.Args[2], []byte(owner.Save("执行过")), 0644); err != nil {
			panic(err)
		}
	case "report":
		if err := os.WriteFile(os.Args[2], []byte(`{"passed":true}`), 0644); err != nil {
			panic(err)
		}
	case "handshake", "logged-handshake":
		if os.Args[1] == "logged-handshake" {
			fmt.Fprint(os.Stdout, strings.Repeat("真实stdout🙂", 65536))
			fmt.Fprint(os.Stderr, strings.Repeat("真实stderr🙂", 65536))
		}
		conn, err := net.Dial("tcp", os.Args[2])
		if err != nil {
			panic(err)
		}
		defer conn.Close()
		if _, err = bufio.NewReader(conn).ReadString('\n'); err != nil {
			os.Exit(9)
		}
	default:
		os.Exit(12)
	}
}
