# Proposed Trace Schema

```json
{
  "run_id": "uuid",
  "session_id": "uuid",
  "model": {
    "provider": "local|external",
    "name": "model-name"
  },
  "planner_attempts": [
    {
      "attempt": 1,
      "parse_ok": true,
      "validation_errors": []
    }
  ],
  "workflow": [],
  "permission_decisions": [],
  "approval": {
    "required": true,
    "result": "approved|cancelled|auto"
  },
  "step_results": [],
  "sandbox": {
    "used": false,
    "duration_ms": 0,
    "timed_out": false,
    "produced_files": []
  },
  "termination_reason": "success|validation_failed|permission_denied|user_cancelled|sandbox_error"
}
```
