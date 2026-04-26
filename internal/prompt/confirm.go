package prompt

import (
	"bufio"
	"fmt"
	"io"
	"strings"
)

type Prompter interface {
	Confirm(question string, defaultYes bool) (bool, error)
}

type Terminal struct {
	Reader io.Reader
	Writer io.Writer
}

func (t Terminal) Confirm(question string, defaultYes bool) (bool, error) {
	suffix := "[y/N]"
	if defaultYes {
		suffix = "[Y/n]"
	}

	if _, err := fmt.Fprintf(t.Writer, "%s %s ", question, suffix); err != nil {
		return false, err
	}

	line, err := bufio.NewReader(t.Reader).ReadString('\n')
	if err != nil && err != io.EOF {
		return false, err
	}

	answer := strings.TrimSpace(strings.ToLower(line))
	if err == io.EOF && answer == "" {
		return false, nil
	}
	if answer == "" {
		return defaultYes, nil
	}

	return answer == "y" || answer == "yes", nil
}
