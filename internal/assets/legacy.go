package assets

import (
	_ "embed"
	"encoding/json"
)

// 只嵌入固定旧受管文件的路径/hash，用于显式刷新时识别文件所有权；没有旧规则或解析器。
//
//go:embed legacy.json
var legacyJSON []byte

type LegacyEntry struct {
	Source string `json:"source"`
	SHA256 string `json:"sha256"`
}

func Legacy() ([]LegacyEntry, error) {
	var out []LegacyEntry
	err := json.Unmarshal(legacyJSON, &out)
	return out, err
}
