# Roadmap

Rubric's focus: be the best tool for testing **agent behavior** — what the agent
did, not just what it said — and make regressions impossible to miss in CI.

Issues marked `good first issue` are scoped for first-time contributors.
If you want to pick something up, comment on the issue and go.

## Now (v0.2.x)

- [x] LangGraph / LangChain auto-capture (`run_langgraph`, `from_langgraph`, `from_messages`)
- [x] Regression diffing (`rubric compare`) with markdown output
- [x] GitHub Action with PR regression comments
- [ ] Auto-capture for **OpenAI Agents SDK** runs
- [ ] Auto-capture for **CrewAI** crews
- [ ] Auto-capture for **Claude Agent SDK** / Anthropic tool-use loops
- [ ] `AnswerRelevancy` metric (#10)
- [ ] Ollama end-to-end example — zero API keys (#6)

## Next (v0.3)

- [ ] **MCP server testing** — run scenarios against an MCP server and assert on tool behavior
- [ ] Baseline auto-update on merge to main (Action option)
- [ ] Dataset loaders (CSV / JSONL) for scenario suites
- [ ] Eval history: trend pass rate / scores across runs in the HTML report
- [ ] GitLab CI / CircleCI recipes

## Later

- [ ] Local web dashboard with run history
- [ ] Slack / Discord notifications on regression
- [ ] Production trace sampling → scheduled eval runs

## Non-goals

- A hosted cloud platform. Rubric stays local-first and CI-native.
- Becoming a general-purpose LLM benchmark harness. Plenty of good ones exist;
  Rubric is for testing *your* agent's behavior on *your* scenarios.
