# Security Policy

This repository is for public research and demo artifacts only.

Do not commit secrets, credentials, private files, raw user data, or unredacted logs. If a secret is committed by mistake, revoke it immediately and rotate any affected credential.

Before publishing or pushing generated artifacts, run a manual preflight:

```bash
git status --short
git diff --cached --stat
git diff --cached --check
git diff --cached
```

Check for filenames and content that may include secrets, credentials, private documents, or personally identifiable information.
