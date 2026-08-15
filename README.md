# Nimbus Harness Lab

Nimbus Harness Lab is an experimental workspace for AI agent harness design, evaluation, observability, and safety.

This repository is owned by Nimbus and is intended to collect public, non-secret artifacts such as:

- agent harness architecture notes
- evaluation case schemas and examples
- workflow / tool-use trace design
- safety checklists for agent runtimes
- demo materials for teaching and videos

## Current focus

Nimbus publishes public, scope-limited artifacts for three research lines:

- LEO / NTN systems and evidence boundaries;
- agent evaluation, trace evidence, and false-green prevention;
- safe agent reasoning for network operations.

The live site is published from the `gh-pages` branch at <https://nimbus.mit-project.me/>.

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
