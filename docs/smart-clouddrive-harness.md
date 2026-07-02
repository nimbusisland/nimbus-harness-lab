# Smart Cloud Drive Harness Notes

A smart cloud drive assistant should treat every model output as a proposal, not as an immediately trusted command.

Recommended control flow:

```text
User prompt
  -> Planner model
  -> Structured workflow
  -> Schema and semantic validation
  -> Skill registry check
  -> Permission classification
  -> User approval gate for write/destructive actions
  -> Workflow executor
  -> Service layer or sandbox
  -> Audit trace and eval harness
```

Important evaluation dimensions:

- correctness: did the requested file/folder state change happen?
- safety: were destructive actions gated and cross-user boundaries preserved?
- plan quality: were steps minimal, explainable, and executable?
- robustness: do repeated runs produce stable results?
- observability: can failures be diagnosed from traces?
