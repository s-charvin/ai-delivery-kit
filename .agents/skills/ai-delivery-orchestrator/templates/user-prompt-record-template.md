<!-- ai-delivery-template-language
Localize headings and AI-written labels into the user's language; preserve the
user's original text exactly, not a translation. Remove this comment and unused
placeholders in the instance. This is a default layout, not a parsed schema.
-->

# User Input Record: <task-topic>

- Requirement: <req-id>
- Task type: <implementation / repair / acceptance / research / workflow improvement>
- Available coverage: <actual available input range; disclose missing history>

## Input 001 | Initial prompt

Source: user
Received at: <actual environment-provided time; omit when unknown>

### User original

```text
<Full original input, retaining paragraphs, lists, code and links.>
```

### Attachments and context (optional)

<Relative links to preserved accessible attachments or actual offered options.
Mark AI context explicitly; never mix it into the original. Omit if unnecessary.>

<!-- Usage instructions: remove from the instance.
Save as requirement prompts/001_User-input-<task-type>-<topic>.md, localized;
next independent task uses 002. User-specified names override this default.
For a related supplement/correction/choice/continuation, copy the input section
in THIS file and increment Input 002, 003, etc. Do not create an empty supplement.
New session/day/stage does not start a task; cross-day supplements never rename
this file. Actual repeated user input gets its own next input section; merely
re-reading stored input does not. Existing input is not replaced by a summary.
If the original contains backticks, use an outer fence longer than its longest
consecutive backtick run; leave the original unchanged. State inaccessible
attachments/history and any host-required redaction, never invent originals.
See references/framework-adaptation.md for preservation and scope rules.
-->
