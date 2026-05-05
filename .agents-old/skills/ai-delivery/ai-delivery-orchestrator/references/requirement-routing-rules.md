# Requirement Routing Rules

Use these rules when the default entry flow needs to recommend either:

- `continue req-xxx`
- `create req-yyy`

Always produce one recommendation only, then pause for human confirmation before taking either path.

## Evidence Sources

Inspect the current repository state before recommending a route:

- existing `.ai-delivery/requirements/*` packages
- requirement titles and summaries
- `todo.md`, `status.json`, and `traceability.json`
- source material links, filenames, identifiers, and feature scope from the new user input

## Recommend `continue req-xxx` Only When

Recommend continuing an existing requirement only when all of the following are true:

1. The candidate requirement is still active.
   - It is not fully merged, archived, or otherwise terminal.
2. The new material clearly points to the same product scope.
   - Examples: same feature, same page/flow, same API scope, same requirement document, or the same governed source links already appear in traceability.
3. There is no strong conflicting evidence that this is a different delivery stream.

When recommending `continue`, cite at least two concrete evidence bullets.

## Recommend `create req-yyy` When

Recommend creating a new requirement when any of the following is true:

- no active requirement has enough matching evidence
- the closest candidate is already merged, archived, or otherwise terminal
- the new material introduces a meaningfully different feature scope, acceptance target, or delivery stream
- continuing an existing requirement would mix unrelated product truth into the same governed package

If the evidence is mixed or weak, prefer `create req-yyy`.

## Human Gate

After recommending either `continue` or `create`:

1. show the single recommended route
2. show the evidence bullets behind it
3. pause for human confirmation or override

If the human overrides the recommendation, follow the human decision and continue the governed workflow from there.
