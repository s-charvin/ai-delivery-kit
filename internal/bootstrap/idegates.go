package bootstrap

import (
	"bytes"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strings"
)

const uiContractHookMarker = "validate-ui-contract.sh"

func isAmendableJSONTarget(target string) bool {
	switch filepath.ToSlash(target) {
	case ".cursor/hooks.json", ".claude/settings.json", ".codex/hooks.json":
		return true
	default:
		return false
	}
}

// mergeAmendableJSON merges desired kit gate config into existing project JSON
// without dropping unrelated top-level keys or foreign hook entries.
func mergeAmendableJSON(existing, desired []byte) ([]byte, error) {
	desiredObj := map[string]any{}
	if err := json.Unmarshal(desired, &desiredObj); err != nil {
		return nil, fmt.Errorf("parse desired gate json: %w", err)
	}

	existingObj := map[string]any{}
	if len(bytes.TrimSpace(existing)) == 0 {
		existingObj = map[string]any{}
	} else if err := json.Unmarshal(existing, &existingObj); err != nil {
		return nil, fmt.Errorf("parse existing gate json: %w", err)
	}

	desiredHooks, _ := desiredObj["hooks"].(map[string]any)
	existingHooks, _ := existingObj["hooks"].(map[string]any)
	if existingHooks == nil {
		existingHooks = map[string]any{}
	}
	if desiredHooks == nil {
		desiredHooks = map[string]any{}
	}

	for event, desiredValue := range desiredHooks {
		desiredGroups, ok := desiredValue.([]any)
		if !ok {
			existingHooks[event] = desiredValue
			continue
		}
		existingGroups, _ := existingHooks[event].([]any)
		existingHooks[event] = upsertHookGroups(existingGroups, desiredGroups)
	}
	existingObj["hooks"] = existingHooks

	// Preserve desired version when existing has none (Cursor hooks.json).
	if _, ok := existingObj["version"]; !ok {
		if version, ok := desiredObj["version"]; ok {
			existingObj["version"] = version
		}
	}

	out, err := json.MarshalIndent(existingObj, "", "  ")
	if err != nil {
		return nil, err
	}
	return append(out, '\n'), nil
}

func upsertHookGroups(existing, desired []any) []any {
	result := append([]any{}, existing...)
	for _, desiredGroup := range desired {
		desiredMap, ok := desiredGroup.(map[string]any)
		if !ok {
			result = append(result, desiredGroup)
			continue
		}
		replaced := false
		for i, existingGroup := range result {
			existingMap, ok := existingGroup.(map[string]any)
			if !ok {
				continue
			}
			if hookGroupOwnsUIContractGate(existingMap) {
				result[i] = desiredMap
				replaced = true
				break
			}
		}
		if !replaced {
			result = append(result, desiredMap)
		}
	}
	return result
}

func hookGroupOwnsUIContractGate(group map[string]any) bool {
	if commandContainsMarker(group["command"]) {
		return true
	}
	hooks, ok := group["hooks"].([]any)
	if !ok {
		return false
	}
	for _, hook := range hooks {
		hookMap, ok := hook.(map[string]any)
		if !ok {
			continue
		}
		if commandContainsMarker(hookMap["command"]) {
			return true
		}
	}
	return false
}

func commandContainsMarker(value any) bool {
	command, ok := value.(string)
	if !ok {
		return false
	}
	return strings.Contains(command, uiContractHookMarker)
}

func writeAmendableJSON(target string, desired []byte) error {
	existing, err := os.ReadFile(target)
	if err != nil {
		if !os.IsNotExist(err) {
			return fmt.Errorf("read %s: %w", target, err)
		}
		existing = nil
	}

	merged, err := mergeAmendableJSON(existing, desired)
	if err != nil {
		return fmt.Errorf("merge %s: %w", target, err)
	}

	if err := os.MkdirAll(filepath.Dir(target), 0o755); err != nil {
		return fmt.Errorf("create parent for %s: %w", target, err)
	}
	if err := os.WriteFile(target, merged, 0o644); err != nil {
		return fmt.Errorf("write %s: %w", target, err)
	}
	return nil
}
