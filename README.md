# AI Delivery Kit

Bootstrap governed `ai-delivery` workflows into arbitrary business repositories.

## Canonical Entry Paths

The public onboarding flow is CLI-first, with a no-install bootstrap path for users who do not want to keep the binary on `PATH`.

### Install The CLI

Published install script path:

```text
scripts/install-ai-delivery.sh
```

Unix example:

```bash
curl -fsSL https://raw.githubusercontent.com/s-charvin/ai-delivery-kit/main/scripts/install-ai-delivery.sh | bash
ai-delivery init /path/to/repo --project-id my-app --main-branch main
```

### Bootstrap Without Installing

Published bootstrap script path:

```text
scripts/bootstrap-ai-delivery.sh
```

Unix example:

```bash
curl -fsSL https://raw.githubusercontent.com/s-charvin/ai-delivery-kit/main/scripts/bootstrap-ai-delivery.sh | bash -s -- /path/to/repo --project-id my-app --main-branch main
```

The bootstrap script uses the same canonical CLI logic, but downloads a temporary binary instead of installing it globally.

### Prerequisites

During `ai-delivery init`, the CLI checks for `specify-cli` and `superpowers`.

- If they are already present, the CLI skips reinstallation.
- If they are missing, the CLI prompts before using the official installation path.
- If you decline installation, the CLI still initializes the governed `ai-delivery` assets and prints the official install links for manual follow-up.

## Source Repo Compatibility Wrapper

This source repository still keeps `scripts/bootstrap-ai-delivery-project.sh` as a compatibility wrapper for local development and contract tests. Public onboarding should prefer the release-facing CLI and bootstrap scripts above.

## Release Policy

- `main` validates build and pre-release checks only.
- `tag push` publishes the formal GitHub Release.
