# Nimbus Harness Lab

Nimbus Harness Lab is an experimental workspace for AI agent harness design, evaluation, observability, and safety.

This repository is owned by Nimbus（雲嶼） and is intended to collect public, non-secret artifacts such as:

- agent harness architecture notes
- evaluation case schemas and examples
- workflow / tool-use trace design
- safety checklists for agent runtimes
- demo materials for teaching and videos

## Current focus

The first research thread is **smart cloud drive AI assistants**: how to design a safe and testable harness around an AI assistant that can plan workflows, call tools, generate skills, run sandboxed code, and be evaluated with deterministic and LLM-assisted tests.

## Safety rules

This repository must not contain:

- API keys, tokens, cookies, passwords, private keys, or credentials
- private user files, raw chat transcripts, or private documents
- unredacted screenshots containing secrets or personally identifiable information
- production database dumps or storage volumes

Use placeholders in examples, such as `YOUR_API_KEY_HERE`.

## Planned structure

```text
docs/
  harness-taxonomy.md
  smart-clouddrive-harness.md
  trace-schema.md
examples/
  eval-case-schema.yaml
  sample-trace.json
checklists/
  safety-review.md
  publishing-preflight.md
```

## License

MIT, unless a specific subdirectory states otherwise.
