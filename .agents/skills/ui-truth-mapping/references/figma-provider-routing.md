# Figma provider routing

Apply before Figma evidence acquisition, including an authorized Stage 4 repair.
Do not require Figma tooling for `none`, `existing`, or `runtime-baseline` work
that does not need Figma evidence. This policy adds no schema field or checkpoint.

## Select one provider

Inspect the current session's skills and callable/discoverable MCP tools. A skill
name alone is not a working connection; check authentication, file access and the
required read capability with a bounded, read-only probe of the supplied node.
Distinguish missing installation from an installed but disconnected/unauthorized
provider. Never claim a probe succeeded without its result.

| User choice | Available providers | Action |
|---|---|---|
| TemPad | Any | Use TemPad; if unavailable, resolve its setup, never silently substitute official Figma. |
| Official Figma | Any | Use official Figma; if unavailable, resolve its setup, never silently substitute TemPad. |
| Unspecified | TemPad only | Use TemPad. |
| Unspecified | Official Figma only | Use official Figma. |
| Unspecified | Both | Default to TemPad. |
| Unspecified | Neither | Ask whether to install automatically; no evidence acquisition until resolved. |

An explicit request overrides every default. If the user names an unsupported or
ambiguous provider, clarify it instead of assigning one. Announce the selection
briefly; do not ask again when the table already resolves it. Record provider,
loaded skill identity/source, probe result and relevant limitations in existing
`progress.md` or `decisions.md`; preserve original Figma node/revision provenance.
Do not silently mix providers within one evidence acquisition. A tool error
stops dependent work: diagnose it, follow the provider's documented recovery, and
ask before switching providers. Missing access does not authorize guessed UI,
screenshots-only reconstruction, fabricated assets, or a runtime-baseline downgrade.

## Missing setup

If neither provider is installed, ask once whether to install automatically,
naming the provider, trusted source and installation scope. With no stated
preference, propose TemPad; allow the user to choose official Figma instead.
For an explicitly selected missing provider, offer installation of that provider.
Installation requires explicit consent; accepting development or CP-UI is not
installation consent. If the user declines, stop the affected delivery flow,
record the blocker, and do not continue implementation or freeze. No answer is
not consent. An existing refusal persists until the user changes it.

After consent, use the environment's supported installer and verified publisher
instructions for the selected skill/plugin and MCP connection. Inspect installed
state first; do not invent package IDs, URLs or shell installation commands.
Installing Markdown alone does not configure MCP. If automatic setup is not
supported, explain the required manual step and remain blocked. Authentication,
Figma permissions or a host restart may need user action; verify the connection
again before resuming. Do not reinstall an already-installed provider to solve an
access problem or automatically install both providers.

## Provider-specific evidence

- **TemPad:** use the installed TemPad skill's actual source, if available;
  `get_code` reads the scoped node, `get_structure` resolves hierarchy/geometry
  ambiguity. TemPad `data-hint-*` interpretation belongs only to this route.
- **Official Figma:** load the official plugin's `figma:figma-design-to-code`
  skill (or its verified environment equivalent) before `get_design_context`.
  Do not confuse it with an unrelated TemPad skill sharing the unqualified
  `figma-design-to-code` name. Follow the installed skill/tool contract, including
  `skillNames` when required. Read scoped design context first; metadata and
  screenshots supplement it, not replace it. Load official motion guidance when
  motion is returned/required, and `figma-use` before any `use_figma` call.
  Do not write to the Figma file unless the user separately authorized that action.

Both routes supply evidence to `ui-truth-mapping`, which retains Stage 2 ownership,
real host-stack implementation, source/asset fidelity, coverage, PNG/GIF review
and freeze gates. Generated React/Tailwind is reference material, never a second
preview to port into Flutter/Android. Persist exact exported asset bytes where
needed; provider URLs expire. Stage 4 normally consumes the frozen component and
confirmed previews; selecting a provider is not permission to refetch or unfreeze.
