// Package assets 描述发行资源身份；不保存业务状态或执行另一份核心。
package assets

import (
	"crypto/sha256"
	"encoding/json"
	"fmt"
	"io/fs"
	"path"
	"sort"
	"strings"

	kitassets "github.com/s-charvin/ai-delivery-kit"
	"github.com/s-charvin/ai-delivery-kit/internal/delivery/protocol"
)

const ManifestName = "meta/kit-assets.json"

type Error struct{ Path, Message string }

func (e *Error) Error() string {
	return e.Path + ": " + e.Message + "；请显式运行 ai-delivery init --upgrade <项目路径> 刷新受管资源，保留当前业务数据"
}

type Entry struct {
	Path   string `json:"path"`
	Scope  string `json:"scope"`
	SHA256 string `json:"sha256"`
}
type Manifest struct {
	Version        int     `json:"asset_manifest_version"`
	ResourceDigest string  `json:"resource_digest"`
	Files          []Entry `json:"files"`
}

func Paths() ([]string, error) {
	paths := []string{}
	err := fs.WalkDir(kitassets.Embedded, ".", func(p string, d fs.DirEntry, e error) error {
		if e != nil {
			return e
		}
		if !d.IsDir() {
			paths = append(paths, p)
		}
		return nil
	})
	sort.Strings(paths)
	return paths, err
}

func Digest() (string, error) {
	paths, err := Paths()
	if err != nil {
		return "", err
	}
	hashes := map[string]any{}
	for _, p := range paths {
		b, err := kitassets.Embedded.ReadFile(p)
		if err != nil {
			return "", err
		}
		hashes[p] = fmt.Sprintf("%x", sha256.Sum256(b))
	}
	return protocol.CanonicalSHA256(hashes)
}

func Expected() (Manifest, error) {
	digest, err := Digest()
	if err != nil {
		return Manifest{}, err
	}
	paths, err := Paths()
	if err != nil {
		return Manifest{}, err
	}
	m := Manifest{1, digest, []Entry{}}
	for _, p := range paths {
		scope := "file"
		switch p {
		case "AGENTS.md":
			scope = "agents-block"
		}
		b, err := kitassets.Embedded.ReadFile(p)
		if err != nil {
			return m, err
		}
		b, err = Project(p, scope, b)
		if err != nil {
			return m, err
		}
		m.Files = append(m.Files, Entry{p, scope, fmt.Sprintf("%x", sha256.Sum256(b))})
	}
	return m, nil
}

// Project 仅投影工具拥有的区段；其余规范/IDE 设置仍是合法项目输入。
func Project(p, scope string, b []byte) ([]byte, error) {
	switch scope {
	case "file":
		return b, nil
	case "agents-block":
		start, end := "<!-- ai-delivery:ui-contract-gate:start -->", "<!-- ai-delivery:ui-contract-gate:end -->"
		s := string(b)
		i, j := strings.Index(s, start), strings.Index(s, end)
		if i < 0 || j < i || strings.Count(s, start) != 1 || strings.Count(s, end) != 1 {
			return nil, fmt.Errorf("缺少或重复受管 AGENTS 区段")
		}
		return []byte(s[i : j+len(end)]), nil

	}
	return nil, fmt.Errorf("未知资源 scope: %s", scope)
}

// Verify 接受同一个 workspace evidence reader，安装检查和动作闭包共用身份。
func Verify(delivery string, read func(string) ([]byte, bool, error)) error {
	manifestPath := path.Join(delivery, ManifestName)
	fail := func(p string, e any) error { return &Error{p, fmt.Sprint(e)} }
	b, ok, err := read(manifestPath)
	if err != nil {
		return fail(manifestPath, err)
	}
	if !ok {
		return fail(manifestPath, "缺少资源清单")
	}
	obj, err := protocol.Object(b)
	if err != nil {
		return fail(manifestPath, err)
	}
	expected, err := Expected()
	if err != nil {
		return err
	}
	if len(obj) != 3 || obj["asset_manifest_version"] != json.Number("1") {
		return fail(manifestPath, "asset_manifest_version 要求当前数值 1")
	}
	if obj["resource_digest"] != expected.ResourceDigest {
		return fail(manifestPath, "当前程序与项目资源合同不匹配；请核对 PATH 中 ai-delivery 的绝对路径与发行版本")
	}
	files, ok := obj["files"].([]any)
	if !ok || len(files) != len(expected.Files) {
		return fail(manifestPath, "资源文件集合不匹配")
	}
	for i, want := range expected.Files {
		got, ok := files[i].(map[string]any)
		if !ok || len(got) != 3 || got["path"] != want.Path || got["scope"] != want.Scope || got["sha256"] != want.SHA256 {
			return fail(manifestPath, "资源文件身份或排序不匹配: "+want.Path)
		}
		b, ok, err := read(want.Path)
		if err != nil {
			return fail(want.Path, err)
		}
		if !ok {
			return fail(want.Path, "缺少受管资源")
		}
		projected, err := Project(want.Path, want.Scope, b)
		if err != nil {
			return fail(want.Path, err)
		}
		if fmt.Sprintf("%x", sha256.Sum256(projected)) != want.SHA256 {
			return fail(want.Path, "受管资源内容已改变")
		}
	}
	return nil
}
