package runner

import (
	"context"
	"crypto/sha256"
	"fmt"
	"io"
	"os"

	"github.com/s-charvin/ai-delivery-kit/internal/projectfs"
)

type StreamCapture struct {
	Bytes  int64  `json:"bytes"`
	SHA256 string `json:"sha256"`
}
type capturedLog struct {
	file, reader, writer *os.File
	done                 chan struct{}
	capture              StreamCapture
	err                  error
}

// 原生流经独立管道采集；摘要来自实际收到的字节，不来自事后同名文件。
func newCapturedLog(path string) (*capturedLog, error) {
	file, err := projectfs.CreateExclusiveFile(path)
	if err != nil {
		return nil, err
	}
	reader, writer, err := os.Pipe()
	if err != nil {
		file.Close()
		return nil, err
	}
	c := &capturedLog{file: file, reader: reader, writer: writer, done: make(chan struct{})}
	go func() {
		defer close(c.done)
		defer reader.Close()
		hash := sha256.New()
		c.capture.Bytes, c.err = io.Copy(io.MultiWriter(file, hash), reader)
		c.capture.SHA256 = fmt.Sprintf("%x", hash.Sum(nil))
	}()
	return c, nil
}
func (c *capturedLog) close() { c.writer.Close(); c.reader.Close(); <-c.done; c.file.Close() }
func (c *capturedLog) finish(ctx context.Context) error {
	select {
	case <-c.done:
	case <-ctx.Done():
		c.reader.Close()
		<-c.done
		return fmt.Errorf("原生输出管道未结束: %w", ctx.Err())
	}
	if c.err != nil {
		return fmt.Errorf("原生流采集失败: %w", c.err)
	}
	if err := c.file.Sync(); err != nil {
		return err
	}
	return c.validate()
}
func (c *capturedLog) validate() error {
	original, err := c.file.Stat()
	if err != nil {
		return err
	}
	current, err := os.Lstat(c.file.Name())
	if err != nil {
		return err
	}
	if !current.Mode().IsRegular() || !os.SameFile(original, current) {
		return fmt.Errorf("原始输出路径已被替换: %s", c.file.Name())
	}
	if original.Size() != c.capture.Bytes {
		return fmt.Errorf("原始输出长度与实际采集字节不一致: %s", c.file.Name())
	}
	if _, err = c.file.Seek(0, io.SeekStart); err != nil {
		return err
	}
	hash := sha256.New()
	n, err := io.Copy(hash, c.file)
	if err != nil {
		return err
	}
	if n != c.capture.Bytes || fmt.Sprintf("%x", hash.Sum(nil)) != c.capture.SHA256 {
		return fmt.Errorf("原始输出被截断或改写: %s", c.file.Name())
	}
	return nil
}
