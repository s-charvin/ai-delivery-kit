#!/usr/bin/env bash
set -euo pipefail

# Pressure test: simulate the full range of real UI-mapping scenarios the
# ui-truth-mapping skill must handle — from whole-page new routes down to a
# single red-dot badge — and confirm the validator accepts correctly-built
# contracts and rejects the documented anti-patterns.
#
# Scenarios covered:
#   A. Whole-page new route (page unit, 2 states)          — large feature
#   B. Red-dot badge as scoped component (component)        — tiny change
#   C. Disconnected artifact split — reject-tip component   — local subtree
#   D. Disconnected artifact split — appeal-cta component   — local subtree
#   E. Multi-state component (loading/empty/loaded)         — state switching
#   F. Multi-state modal bottom sheet (3 states)            — overlay + switcher
#   G. INVALID — invisible default state (empty template)   — hydration gap
#   H. INVALID — whole-page dump with truth-annotated context — scope creep

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
VALIDATOR="$ROOT/scripts/validate-ui-contract-html.py"

fail() { echo "FAIL: $*" >&2; exit 1; }

[[ -f "$VALIDATOR" ]] || fail "Missing validator: $VALIDATOR"

TMP_DIR=$(mktemp -d)
trap 'rm -rf "$TMP_DIR"' EXIT

# Shared preview script (the fixed hydrate + switch IIFE every contract keeps).
read -r -d '' PREVIEW_SCRIPT <<'JS' || true
(function () {
  var main = document.querySelector("main[data-ui-contract]");
  if (!main) return;
  var metaEl = document.getElementById("ui-contract-meta");
  var host = main.querySelector("[data-ui-state-host]");
  var switcher = main.querySelector("[data-ui-state-switcher]");
  if (!metaEl || !host) return;
  var meta;
  try { meta = JSON.parse(metaEl.textContent); } catch (e) { return; }
  var states = Array.isArray(meta.states) ? meta.states : [];
  var defaultId =
    main.getAttribute("data-ui-state-default") ||
    (states.find(function (s) { return s && s.default; }) || states[0] || {}).id;
  function templateFor(id) {
    return main.querySelector('template[data-ui-state="' + id + '"]');
  }
  function activate(id) {
    var tpl = templateFor(id);
    if (!tpl) return;
    host.replaceChildren(tpl.content.cloneNode(true));
    host.setAttribute("data-active-state", id);
    if (!switcher) return;
    switcher.querySelectorAll("button[data-state-id]").forEach(function (btn) {
      btn.setAttribute("aria-pressed", btn.getAttribute("data-state-id") === id ? "true" : "false");
    });
  }
  if (switcher) {
    switcher.replaceChildren();
    states.forEach(function (s) {
      if (!s || !s.id) return;
      var btn = document.createElement("button");
      btn.type = "button";
      btn.setAttribute("data-state-id", s.id);
      btn.textContent = s.id + (s.default ? " (default)" : "");
      btn.addEventListener("click", function () { activate(s.id); });
      switcher.appendChild(btn);
    });
  }
  if (defaultId) activate(defaultId);
})();
JS

# ---------------------------------------------------------------------------
# Scenario A — Whole-page new route: /settings page (page unit, 2 states)
# ---------------------------------------------------------------------------
cat > "$TMP_DIR/settings-page.html" <<HTML
<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>UI Contract: settings-page</title>
<script type="application/json" id="ui-contract-meta">
{
  "schema_version": 2,
  "contract_id": "settings-page",
  "source": { "requirement": "req-settings.md", "design_file": "figma-key-a", "root_node": "10:1" },
  "unit": {
    "id": "settings-page", "type": "page", "title": "Settings",
    "route_or_trigger": "/settings", "requirements": ["subreq-settings-1"],
    "source_node": "10:1", "dependencies": []
  },
  "states": [
    { "id": "loaded", "source_node": "10:1", "default": true },
    { "id": "loading", "source_node": "10:50", "default": false }
  ],
  "revision": 1,
  "delivery": { "status": "frozen", "implemented": null }
}
</script>
<style>
  :root { --color-surface: #FFFFFF; --color-text: #111111; --space-x: 16px; }
  [data-ui-contract] { background: var(--color-surface); color: var(--color-text); min-height: 100vh; }
  [data-ui-state-switcher] { display: flex; gap: 8px; padding: 8px 12px; }
  [data-ui-id="settings-list"] { padding: 0 var(--space-x); }
  [data-ui-id="settings-row-notifications"] { padding: 14px 0; }
</style>
</head>
<body>
<main data-ui-contract data-ui-unit-id="settings-page" data-ui-unit-type="page" data-ui-state-default="loaded">
  <nav data-ui-state-switcher aria-label="UI contract states"></nav>
  <div data-ui-state-host></div>
  <template data-ui-state="loaded">
    <ul data-ui-id="settings-list" data-ui-kind="list" data-figma-node="10:5" data-evidence="code">
      <li data-ui-id="settings-row-notifications" data-ui-kind="list-item" data-figma-node="10:6" data-evidence="code">Notifications</li>
      <li data-ui-id="settings-row-privacy" data-ui-kind="list-item" data-figma-node="10:7" data-evidence="code">Privacy</li>
    </ul>
  </template>
  <template data-ui-state="loading">
    <div data-ui-id="settings-skeleton" data-ui-kind="container" data-figma-node="10:51" data-evidence="code">Loading settings…</div>
  </template>
  <details data-ui-review-panel>
    <summary>Contract evidence</summary>
    <dl>
      <dt data-ui-scope="in_scope">In scope</dt>
      <dd>10:5 settings list; 10:6 notifications row; 10:7 privacy row; 10:51 loading skeleton.</dd>
      <dt data-ui-scope="out_of_scope">Out of scope context</dt>
      <dd>none</dd>
    </dl>
  </details>
  <script data-ui-state-preview>
$PREVIEW_SCRIPT
  </script>
</main>
</body>
</html>
HTML

python3 "$VALIDATOR" "$TMP_DIR/settings-page.html" >"$TMP_DIR/settings-page.out" 2>&1 \
  || { cat "$TMP_DIR/settings-page.out" >&2; fail "Scenario A (whole-page) should validate"; }
grep -q '^OK:' "$TMP_DIR/settings-page.out" || fail "Scenario A must print OK"

# ---------------------------------------------------------------------------
# Scenario B — Red-dot badge as a scoped component (component, 1 state)
# Tiny change: only the unread badge is In Scope. No matching tab-bar contract
# is assumed here, so create a `component` rooted at the badge subtree — not a
# brand-new shared-component dump of the whole tab bar, and not a messages-page.
# ---------------------------------------------------------------------------
cat > "$TMP_DIR/unread-badge.html" <<HTML
<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>UI Contract: unread-badge</title>
<script type="application/json" id="ui-contract-meta">
{
  "schema_version": 2,
  "contract_id": "unread-badge",
  "source": { "requirement": "req-unread-badge.md", "design_file": "figma-key-b", "root_node": "20:5" },
  "unit": {
    "id": "unread-badge", "type": "component", "title": "Unread Badge",
    "route_or_trigger": "on notifications tab icon", "requirements": ["subreq-badge-1"],
    "source_node": "20:5", "dependencies": []
  },
  "states": [
    { "id": "default", "source_node": "20:5", "default": true }
  ],
  "revision": 1,
  "delivery": { "status": "frozen", "implemented": null }
}
</script>
<style>
  [data-ui-contract] { min-height: 100vh; }
  [data-ui-state-switcher] { display: flex; gap: 8px; padding: 8px 12px; }
  [data-ui-id="unread-badge"] { min-width: 16px; height: 16px; border-radius: 8px; background: #FF3B30; color: #FFF; font-size: 10px; line-height: 16px; text-align: center; }
</style>
</head>
<body>
<main data-ui-contract data-ui-unit-id="unread-badge" data-ui-unit-type="component" data-ui-state-default="default">
  <nav data-ui-state-switcher aria-label="UI contract states"></nav>
  <div data-ui-state-host></div>
  <template data-ui-state="default">
    <span data-ui-id="unread-badge" data-ui-kind="badge" data-figma-node="20:5" data-evidence="code">3</span>
  </template>
  <details data-ui-review-panel>
    <summary>Contract evidence</summary>
    <dl>
      <dt data-ui-scope="in_scope">In scope</dt>
      <dd>20:5 unread badge only.</dd>
      <dt data-ui-scope="out_of_scope">Out of scope context</dt>
      <dd>Messages page chrome and the rest of the tab bar — not frozen here.</dd>
    </dl>
  </details>
  <script data-ui-state-preview>
$PREVIEW_SCRIPT
  </script>
</main>
</body>
</html>
HTML

python3 "$VALIDATOR" "$TMP_DIR/unread-badge.html" >"$TMP_DIR/unread-badge.out" 2>&1 \
  || { cat "$TMP_DIR/unread-badge.out" >&2; fail "Scenario B (red-dot badge component) should validate"; }
grep -q '^OK:' "$TMP_DIR/unread-badge.out" || fail "Scenario B must print OK"

# ---------------------------------------------------------------------------
# Scenario C — Disconnected artifact: reject-tip component (component unit)
# A reject tip lives in the message list; its smallest common ancestor with
# the appeal CTA (Scenario D) is the whole page. So each gets its own
# component contract with a local minimal-ancestor root — never one
# whole-page contract.
# ---------------------------------------------------------------------------
cat > "$TMP_DIR/reject-tip.html" <<HTML
<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>UI Contract: reject-tip</title>
<script type="application/json" id="ui-contract-meta">
{
  "schema_version": 2,
  "contract_id": "reject-tip",
  "source": { "requirement": "req-reject-flow.md", "design_file": "figma-key-c", "root_node": "30:10" },
  "unit": {
    "id": "reject-tip", "type": "component", "title": "Reject Tip",
    "route_or_trigger": "inline in message list", "requirements": ["subreq-reject-tip"],
    "source_node": "30:10", "dependencies": []
  },
  "states": [
    { "id": "default", "source_node": "30:10", "default": true }
  ],
  "revision": 1,
  "delivery": { "status": "frozen", "implemented": null }
}
</script>
<style>
  [data-ui-contract] { min-height: 100vh; }
  [data-ui-state-switcher] { display: flex; gap: 8px; padding: 8px 12px; }
  [data-ui-id="reject-tip-card"] { padding: 12px 16px; background: #FFF3F3; border-radius: 8px; }
  [data-ui-id="reject-tip-icon"] { color: #FF3B30; }
</style>
</head>
<body>
<main data-ui-contract data-ui-unit-id="reject-tip" data-ui-unit-type="component" data-ui-state-default="default">
  <nav data-ui-state-switcher aria-label="UI contract states"></nav>
  <div data-ui-state-host></div>
  <template data-ui-state="default">
    <div data-ui-id="reject-tip-card" data-ui-kind="card" data-figma-node="30:11" data-evidence="code">
      <span data-ui-id="reject-tip-icon" data-ui-kind="icon" data-figma-node="30:12" data-evidence="code">!</span>
      <p data-ui-id="reject-tip-text" data-ui-kind="text" data-figma-node="30:13" data-evidence="code">This candidate is no longer available.</p>
    </div>
  </template>
  <details data-ui-review-panel>
    <summary>Contract evidence</summary>
    <dl>
      <dt data-ui-scope="in_scope">In scope</dt>
      <dd>30:11 reject tip card; 30:12 alert icon; 30:13 tip text. Split from appeal-cta (disconnected subtree).</dd>
      <dt data-ui-scope="out_of_scope">Out of scope context</dt>
      <dd>none</dd>
    </dl>
  </details>
  <script data-ui-state-preview>
$PREVIEW_SCRIPT
  </script>
</main>
</body>
</html>
HTML

python3 "$VALIDATOR" "$TMP_DIR/reject-tip.html" >"$TMP_DIR/reject-tip.out" 2>&1 \
  || { cat "$TMP_DIR/reject-tip.out" >&2; fail "Scenario C (reject-tip component) should validate"; }
grep -q '^OK:' "$TMP_DIR/reject-tip.out" || fail "Scenario C must print OK"

# ---------------------------------------------------------------------------
# Scenario D — Disconnected artifact: appeal-cta component (component unit)
# The appeal CTA lives in the composer; disconnected from the reject tip.
# ---------------------------------------------------------------------------
cat > "$TMP_DIR/appeal-cta.html" <<HTML
<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>UI Contract: appeal-cta</title>
<script type="application/json" id="ui-contract-meta">
{
  "schema_version": 2,
  "contract_id": "appeal-cta",
  "source": { "requirement": "req-reject-flow.md", "design_file": "figma-key-c", "root_node": "30:40" },
  "unit": {
    "id": "appeal-cta", "type": "component", "title": "Appeal CTA",
    "route_or_trigger": "inline in composer", "requirements": ["subreq-appeal-cta"],
    "source_node": "30:40", "dependencies": []
  },
  "states": [
    { "id": "default", "source_node": "30:40", "default": true }
  ],
  "revision": 1,
  "delivery": { "status": "frozen", "implemented": null }
}
</script>
<style>
  [data-ui-contract] { min-height: 100vh; }
  [data-ui-state-switcher] { display: flex; gap: 8px; padding: 8px 12px; }
  [data-ui-id="appeal-button"] { padding: 10px 20px; background: #0066CC; color: #FFF; border-radius: 8px; }
</style>
</head>
<body>
<main data-ui-contract data-ui-unit-id="appeal-cta" data-ui-unit-type="component" data-ui-state-default="default">
  <nav data-ui-state-switcher aria-label="UI contract states"></nav>
  <div data-ui-state-host></div>
  <template data-ui-state="default">
    <button data-ui-id="appeal-button" data-ui-kind="button" data-figma-node="30:41" data-evidence="code">Appeal this decision</button>
  </template>
  <details data-ui-review-panel>
    <summary>Contract evidence</summary>
    <dl>
      <dt data-ui-scope="in_scope">In scope</dt>
      <dd>30:41 appeal CTA button. Split from reject-tip (disconnected subtree).</dd>
      <dt data-ui-scope="out_of_scope">Out of scope context</dt>
      <dd>none</dd>
    </dl>
  </details>
  <script data-ui-state-preview>
$PREVIEW_SCRIPT
  </script>
</main>
</body>
</html>
HTML

python3 "$VALIDATOR" "$TMP_DIR/appeal-cta.html" >"$TMP_DIR/appeal-cta.out" 2>&1 \
  || { cat "$TMP_DIR/appeal-cta.out" >&2; fail "Scenario D (appeal-cta component) should validate"; }
grep -q '^OK:' "$TMP_DIR/appeal-cta.out" || fail "Scenario D must print OK"

# ---------------------------------------------------------------------------
# Scenario E — Multi-state component: inbox list (3 states, switcher required)
# A component with loading/empty/loaded states. The reviewer must be able to
# flip between all three in the browser — this is the core "state switching"
# requirement.
# ---------------------------------------------------------------------------
cat > "$TMP_DIR/inbox-list.html" <<HTML
<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>UI Contract: inbox-list</title>
<script type="application/json" id="ui-contract-meta">
{
  "schema_version": 2,
  "contract_id": "inbox-list",
  "source": { "requirement": "req-inbox.md", "design_file": "figma-key-e", "root_node": "40:1" },
  "unit": {
    "id": "inbox-list", "type": "component", "title": "Inbox List",
    "route_or_trigger": "inline on inbox page", "requirements": ["subreq-inbox-list"],
    "source_node": "40:1", "dependencies": []
  },
  "states": [
    { "id": "loaded", "source_node": "40:1", "default": true },
    { "id": "loading", "source_node": "40:30", "default": false },
    { "id": "empty", "source_node": "40:20", "default": false }
  ],
  "revision": 1,
  "delivery": { "status": "frozen", "implemented": null }
}
</script>
<style>
  [data-ui-contract] { min-height: 100vh; }
  [data-ui-state-switcher] { display: flex; gap: 8px; padding: 8px 12px; }
  [data-ui-id="inbox-list-root"] { padding: 0 16px; }
  [data-ui-id="inbox-row-1"] { padding: 12px 0; border-bottom: 1px solid #EEE; }
</style>
</head>
<body>
<main data-ui-contract data-ui-unit-id="inbox-list" data-ui-unit-type="component" data-ui-state-default="loaded">
  <nav data-ui-state-switcher aria-label="UI contract states"></nav>
  <div data-ui-state-host></div>
  <template data-ui-state="loaded">
    <ul data-ui-id="inbox-list-root" data-ui-kind="list" data-figma-node="40:2" data-evidence="code">
      <li data-ui-id="inbox-row-1" data-ui-kind="list-item" data-figma-node="40:3" data-evidence="code">New message from Alice</li>
      <li data-ui-id="inbox-row-2" data-ui-kind="list-item" data-figma-node="40:4" data-evidence="code">Meeting reminder</li>
    </ul>
  </template>
  <template data-ui-state="loading">
    <div data-ui-id="inbox-skeleton" data-ui-kind="container" data-figma-node="40:31" data-evidence="code">Loading inbox…</div>
  </template>
  <template data-ui-state="empty">
    <div data-ui-id="inbox-empty" data-ui-kind="container" data-figma-node="40:21" data-evidence="code">
      <p data-ui-id="inbox-empty-text" data-ui-kind="text" data-figma-node="40:22" data-evidence="code">No messages yet</p>
    </div>
  </template>
  <details data-ui-review-panel>
    <summary>Contract evidence</summary>
    <dl>
      <dt data-ui-scope="in_scope">In scope</dt>
      <dd>40:2 list root; 40:3-40:4 rows; 40:31 loading skeleton; 40:21-40:22 empty state.</dd>
      <dt data-ui-scope="out_of_scope">Out of scope context</dt>
      <dd>none</dd>
    </dl>
  </details>
  <script data-ui-state-preview>
$PREVIEW_SCRIPT
  </script>
</main>
</body>
</html>
HTML

python3 "$VALIDATOR" "$TMP_DIR/inbox-list.html" >"$TMP_DIR/inbox-list.out" 2>&1 \
  || { cat "$TMP_DIR/inbox-list.out" >&2; fail "Scenario E (multi-state component) should validate"; }
grep -q '^OK:' "$TMP_DIR/inbox-list.out" || fail "Scenario E must print OK"

# ---------------------------------------------------------------------------
# Scenario F — Multi-state modal bottom sheet (modal unit, 3 states)
# The sheet is its own unit with default/submitting/success. Trigger button is
# NOT in this contract — it would be patched into the message-row container.
# Preview infra + non-empty templates for EVERY state are mandatory.
# ---------------------------------------------------------------------------
cat > "$TMP_DIR/report-sheet.html" <<HTML
<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>UI Contract: report-sheet</title>
<script type="application/json" id="ui-contract-meta">
{
  "schema_version": 2,
  "contract_id": "report-sheet",
  "source": { "requirement": "req-report.md", "design_file": "figma-key-f", "root_node": "50:1" },
  "unit": {
    "id": "report-sheet", "type": "modal", "title": "Report Sheet",
    "route_or_trigger": "triggered by report-button click on message-row",
    "requirements": ["subreq-report-sheet"],
    "source_node": "50:1", "dependencies": []
  },
  "states": [
    { "id": "default", "source_node": "50:1", "default": true },
    { "id": "submitting", "source_node": "50:20", "default": false },
    { "id": "success", "source_node": "50:30", "default": false }
  ],
  "revision": 1,
  "delivery": { "status": "frozen", "implemented": null }
}
</script>
<style>
  [data-ui-contract] { min-height: 100vh; }
  [data-ui-state-switcher] { display: flex; gap: 8px; padding: 8px 12px; }
  [data-ui-id="report-sheet-panel"] { position: fixed; bottom: 0; left: 0; right: 0; background: #FFF; border-radius: 16px 16px 0 0; padding: 16px; }
  [data-ui-id="report-option-spam"] { padding: 14px 0; border-bottom: 1px solid #EEE; }
</style>
</head>
<body>
<main data-ui-contract data-ui-unit-id="report-sheet" data-ui-unit-type="modal" data-ui-state-default="default">
  <nav data-ui-state-switcher aria-label="UI contract states"></nav>
  <div data-ui-state-host></div>
  <template data-ui-state="default">
    <div data-ui-id="report-sheet-panel" data-ui-kind="sheet" data-figma-node="50:2" data-evidence="code">
      <button data-ui-id="report-option-spam" data-ui-kind="button" data-figma-node="50:3" data-evidence="code">Report as spam</button>
      <button data-ui-id="report-option-cancel" data-ui-kind="button" data-figma-node="50:4" data-evidence="code">Cancel</button>
    </div>
  </template>
  <template data-ui-state="submitting">
    <div data-ui-id="report-sheet-submitting" data-ui-kind="sheet" data-figma-node="50:21" data-evidence="code">
      <p data-ui-id="report-submitting-text" data-ui-kind="text" data-figma-node="50:22" data-evidence="code">Submitting…</p>
    </div>
  </template>
  <template data-ui-state="success">
    <div data-ui-id="report-sheet-success" data-ui-kind="sheet" data-figma-node="50:31" data-evidence="code">
      <p data-ui-id="report-success-text" data-ui-kind="text" data-figma-node="50:32" data-evidence="code">Report submitted</p>
    </div>
  </template>
  <details data-ui-review-panel>
    <summary>Contract evidence</summary>
    <dl>
      <dt data-ui-scope="in_scope">In scope</dt>
      <dd>50:2-50:4 default options; 50:21-50:22 submitting; 50:31-50:32 success. Trigger button lives in the message-row contract, not here.</dd>
      <dt data-ui-scope="out_of_scope">Out of scope context</dt>
      <dd>Messages page chrome — not frozen here.</dd>
    </dl>
  </details>
  <script data-ui-state-preview>
$PREVIEW_SCRIPT
  </script>
</main>
</body>
</html>
HTML

python3 "$VALIDATOR" "$TMP_DIR/report-sheet.html" >"$TMP_DIR/report-sheet.out" 2>&1 \
  || { cat "$TMP_DIR/report-sheet.out" >&2; fail "Scenario F (multi-state modal sheet) should validate"; }
grep -q '^OK:' "$TMP_DIR/report-sheet.out" || fail "Scenario F must print OK"

# ---------------------------------------------------------------------------
# Scenario G — INVALID: invisible default state (empty default template)
# The agent put the default state in <template> but left it empty — the
# browser would hydrate a blank host. Validator must reject.
# ---------------------------------------------------------------------------
cat > "$TMP_DIR/invisible-default.html" <<HTML
<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>UI Contract: invisible-default</title>
<script type="application/json" id="ui-contract-meta">
{
  "schema_version": 2,
  "contract_id": "invisible-default",
  "source": { "requirement": "req-x.md", "design_file": "figma-key-g", "root_node": "60:1" },
  "unit": {
    "id": "invisible-default", "type": "component", "title": "Broken Default",
    "route_or_trigger": "inline", "requirements": ["subreq-x"],
    "source_node": "60:1", "dependencies": []
  },
  "states": [
    { "id": "default", "source_node": "60:1", "default": true }
  ],
  "revision": 1,
  "delivery": { "status": "frozen", "implemented": null }
}
</script>
<style> [data-ui-contract] { min-height: 100vh; } </style>
</head>
<body>
<main data-ui-contract data-ui-unit-id="invisible-default" data-ui-unit-type="component" data-ui-state-default="default">
  <nav data-ui-state-switcher aria-label="UI contract states"></nav>
  <div data-ui-state-host></div>
  <template data-ui-state="default"></template>
  <details data-ui-review-panel>
    <summary>Contract evidence</summary>
    <dl>
      <dt data-ui-scope="in_scope">In scope</dt>
      <dd>60:1 root.</dd>
      <dt data-ui-scope="out_of_scope">Out of scope context</dt>
      <dd>none</dd>
    </dl>
  </details>
  <script data-ui-state-preview>
$PREVIEW_SCRIPT
  </script>
</main>
</body>
</html>
HTML

if python3 "$VALIDATOR" "$TMP_DIR/invisible-default.html" >"$TMP_DIR/invisible-default.out" 2>&1; then
  cat "$TMP_DIR/invisible-default.out" >&2
  fail "Scenario G (empty default template) must NOT validate"
fi
grep -q 'state template "default"' "$TMP_DIR/invisible-default.out" \
  || fail "Scenario G must report empty default state template"

# ---------------------------------------------------------------------------
# Scenario H — INVALID: whole-page dump with truth-annotated context chrome
# The agent dumped the whole page and truth-annotated the surrounding nav +
# composer (out of scope) instead of splitting out the in-scope tip. The
# validator must reject truth-annotated context.
# ---------------------------------------------------------------------------
cat > "$TMP_DIR/whole-page-dump.html" <<HTML
<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>UI Contract: whole-page-dump</title>
<script type="application/json" id="ui-contract-meta">
{
  "schema_version": 2,
  "contract_id": "whole-page-dump",
  "source": { "requirement": "req-tip.md", "design_file": "figma-key-h", "root_node": "70:1" },
  "unit": {
    "id": "whole-page-dump", "type": "page", "title": "Whole Page Dump",
    "route_or_trigger": "/messages", "requirements": ["subreq-tip"],
    "source_node": "70:1", "dependencies": []
  },
  "states": [
    { "id": "default", "source_node": "70:1", "default": true }
  ],
  "revision": 1,
  "delivery": { "status": "frozen", "implemented": null }
}
</script>
<style> [data-ui-contract] { min-height: 100vh; } </style>
</head>
<body>
<main data-ui-contract data-ui-unit-id="whole-page-dump" data-ui-unit-type="page" data-ui-state-default="default">
  <nav data-ui-state-switcher aria-label="UI contract states"></nav>
  <div data-ui-state-host></div>
  <template data-ui-state="default">
    <nav data-ui-scope="context" data-ui-id="page-nav" data-ui-kind="navigation" data-figma-node="70:2" data-evidence="code">Nav (out of scope, wrongly truth-annotated)</nav>
    <div data-ui-id="reject-tip-card" data-ui-kind="card" data-figma-node="70:10" data-evidence="code">Reject tip (the only in-scope artifact)</div>
  </template>
  <details data-ui-review-panel>
    <summary>Contract evidence</summary>
    <dl>
      <dt data-ui-scope="in_scope">In scope</dt>
      <dd>70:10 reject tip card.</dd>
      <dt data-ui-scope="out_of_scope">Out of scope context</dt>
      <dd>70:2 nav chrome (kept for positioning).</dd>
    </dl>
  </details>
  <script data-ui-state-preview>
$PREVIEW_SCRIPT
  </script>
</main>
</body>
</html>
HTML

if python3 "$VALIDATOR" "$TMP_DIR/whole-page-dump.html" >"$TMP_DIR/whole-page-dump.out" 2>&1; then
  cat "$TMP_DIR/whole-page-dump.out" >&2
  fail "Scenario H (truth-annotated context) must NOT validate"
fi
grep -q 'data-ui-scope="context" must not carry' "$TMP_DIR/whole-page-dump.out" \
  || fail "Scenario H must report context-not-truth"

echo "PASS: ui-contract-scenarios-pressure (6 valid scenarios accepted, 2 anti-patterns rejected)"
