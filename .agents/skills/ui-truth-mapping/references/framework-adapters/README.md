# Framework Adapter References

The UI Truth Mapping skill defines the framework-neutral governance contract.
Adapters in this directory are implementation references for a host framework;
they are optional and interchangeable. An adapter must follow the core rules
for real host rendering, deterministic capture, evidence binding, temporary
artifact cleanup, and independent motion confirmation.

Before using an adapter:

1. Identify the host framework and its existing official rendering-test path.
2. Confirm that the adapter's capture and encoder path is already supported by
   the host project, or record the explicit project decision that permits it.
3. Use the adapter only for test/capture mechanics. Production components must
   follow the host project's own architecture and dependencies.

Each adapter should document its native test entrypoint, real component trigger,
static and motion capture, timing and encoding semantics, decode checks,
temporary-output cleanup, known limitations, and evidence-field mapping.
