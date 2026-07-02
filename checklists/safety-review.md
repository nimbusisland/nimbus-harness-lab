# Agent Harness Safety Review

- [ ] Model output is treated as a proposal, not a command
- [ ] Tool calls are schema-validated
- [ ] Unknown tools/skills are rejected before execution
- [ ] Destructive actions require approval
- [ ] Multi-tenant operations bind `user_id` server-side
- [ ] Generated code requires review and sandbox execution
- [ ] Sandbox has timeout, output, network, and filesystem controls
- [ ] Traces capture failures without leaking secrets
- [ ] Eval cases cover prompt injection and approval bypass
