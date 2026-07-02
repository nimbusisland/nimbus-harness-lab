# Agent Harness Taxonomy

An agent harness is the execution system around the model, not the model alone.

Key components:

1. System/developer prompts and policies
2. Tool schema and dispatcher
3. Permission and approval model
4. Planning, retry, and repair loops
5. Memory and retrieval
6. Observation formatting and trace capture
7. Sandbox and runtime boundaries
8. Evaluator, grader, and benchmark driver
9. Multi-agent orchestration, if present

Core research question:

> Holding the model constant, how much does the harness/runtime change final task success, safety, cost, trace quality, and reproducibility?
