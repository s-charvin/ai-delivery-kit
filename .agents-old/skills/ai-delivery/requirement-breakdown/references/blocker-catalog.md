# Blocker Catalog

## Core Blockers

- `blocked_requirement_conflict`: the requirement source contradicts itself or another requirement source.
- `blocked_missing_requirement`: a critical business fact is missing.
- `blocked_figma_conflict`: the design source contradicts itself.
- `blocked_requirement_figma_conflict`: requirement truth and visual truth disagree.
- `blocked_missing_design`: a required visual carrier is missing from design evidence.
- `blocked_dependency`: an upstream sub-requirement is not merged to the main development branch.
- `blocked_merge_conflict`: merge-back to the main development branch failed.
- `blocked_verification_failure`: required checks failed and the output cannot be trusted.

## Usage Rule

Choose the narrowest blocker that explains why the next state transition cannot happen, then document the evidence and recovery condition in the matching requirement folder.
