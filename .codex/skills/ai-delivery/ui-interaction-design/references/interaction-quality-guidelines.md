# Interaction Quality Guidelines

Use this reference when `ui-interaction-design` needs better bounded defaults for micro-interactions, loading, feedback, motion, timing, and accessibility without changing business meaning.

## Purposeful Motion

Motion should only be used when it improves understanding.

Valid purposes:

- feedback: confirms an action or state change happened
- orientation: shows where content came from or where it is going
- focus: draws attention to important updates or errors
- continuity: preserves context across state or surface changes

Avoid motion that exists only to decorate, entertain, or make the UI feel more "premium" without clarifying user understanding.

## Feedback Surface Ladder

Choose the lightest feedback surface that still preserves clarity:

1. inline feedback
2. field or component-local feedback
3. section or page-local feedback
4. transient global feedback such as toast or snackbar
5. blocking or interruptive feedback such as modal or full-page state

Guidance:

- prefer inline or local feedback for validation and recoverable errors
- use toast or snackbar for non-blocking status confirmation when the user can stay in context
- do not rely on toast alone for critical, persistent, or form-specific errors
- use blocking interruption only when the source truth or platform rule requires explicit acknowledgement

## Loading Pattern Ladder

Choose the narrowest loading scope that matches the user action:

1. control-level loading
2. inline section loading
3. container or panel loading
4. page-level loading
5. app-wide blocking loading

Guidance:

- prefer button or control-level loading for single-action submissions
- prefer inline progress or skeletons when preserving layout helps orientation
- use skeletons only when layout is known and stable enough to preserve user context
- avoid full-screen or blocking loading unless the user truly cannot proceed safely
- state whether editing remains possible during loading
- state whether retry is local, global, or unavailable

## Motion Pattern Guidance

When motion is allowed, prefer patterns that remain readable across web, iOS, and Android:

- state emphasis: subtle fade, scale, or elevation change to confirm state
- container continuity: preserve parent-child relationship when content expands, collapses, or swaps
- entry and exit: make surface arrival and dismissal understandable
- progress continuity: indicate that work is ongoing without hiding context
- focus recovery: keep user attention near the changed area after validation or error

Avoid:

- large choreographed transitions for routine actions
- motion that prevents interruption or recovery
- motion that obscures content, focus, or error visibility
- hover-only effects that have no touch or keyboard equivalent

## Timing Guidance

Use timing as a guideline, not a hard requirement unless the source defines it.

Suggested ranges:

- micro-feedback: `80-150ms`
- small state changes: `150-250ms`
- component or panel transitions: `200-350ms`
- major continuity transitions: `300-500ms`
- anything longer than `500ms`: justify why it is needed

Guidance:

- short feedback should feel immediate
- longer transitions should communicate meaningful continuity
- repeated interactions should not accumulate noticeable delay
- if timing is not source-backed, record it as a bounded assumption

## Input Modality And Accessibility

Interaction quality must hold across pointer, touch, keyboard, and assistive use.

### Keyboard And Focus

- interactive controls should remain keyboard reachable
- focus should stay visible through validation, loading, and error transitions
- after an error, keep or restore focus where recovery is clearest
- after transient feedback, avoid unexpected focus jumps

### Touch And Pointer

- do not rely on hover as the only affordance
- if hover adds meaning, provide an equivalent focus or touch-visible state
- gesture shortcuts should have a visible or discoverable non-gesture alternative when they affect important actions

### Reduced Motion

- respect reduced-motion preferences by default when source truth is silent
- retain state clarity even when motion is minimized
- do not hide success, error, or progress meaning behind animation alone

### Announcements And State Semantics

- important loading, success, and error states should remain semantically clear
- persistent validation or blocking errors should not be conveyed only visually
- disabled states should remain understandable, especially when they block completion

## Common Interaction Quality Patterns

### Validation

- prefer validation timing that matches the field and risk level
- use immediate validation for obvious format issues when it does not create noise
- use blur or submit-time validation when constant interruption would hurt entry flow

### Success Feedback

- local confirmation is usually enough when the user stays in the same context
- use stronger confirmation only when the change is destructive, cross-surface, or easy to miss

### Error Recovery

- error states should explain what the user can do next
- prefer recoverable, in-context retry when the source truth allows
- separate transient transport errors from persistent business-rule errors

### Gestures

- use gesture-driven interactions only when the gesture is already established by the source or existing pattern
- critical actions need a visible fallback path
- gesture completion thresholds should feel deliberate, not hair-trigger

## Common Failure Modes

- over-animation that adds delight but hides meaning
- blocking loading when local progress would be enough
- toast-only critical errors
- hover-only discoverability
- invisible focus after validation or modal return
- success feedback that disappears before the user can perceive it
- gestures that have no visible fallback
- motion that ignores reduced-motion expectations
- optimistic feedback that implies success before the source-backed flow allows it
