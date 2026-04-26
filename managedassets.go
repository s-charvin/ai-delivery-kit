package kitassets

import "embed"

// Embedded must live at the module root because go:embed cannot traverse .. to reach sibling directories.
//
//go:embed .agents/skills/ai-delivery scripts/validate-project-ai-delivery-skills.sh tests/ai-delivery-skills/api-nonblocking-policy.test.sh tests/ai-delivery-skills/validate-sources.test.sh
var Embedded embed.FS
