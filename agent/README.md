# Clean Room Fetch.ai agents

The coordinator is the only Agent Chat Protocol entry point. Explorer, builder and verifier are distinct uAgents in one Bureau. The coordinator publishes its chat manifest and uses an Agentverse mailbox. Port 8001 binds only 127.0.0.1. No database or Payment Protocol.

## Run

```sh
.venv/bin/python -m agent.coordinator --addresses
.venv/bin/python -m agent.coordinator
```

The current environment has uagents 0.26.1. If missing, install into the virtual environment with `uv pip install --python .venv/bin/python 'uagents==0.26.1' openai`. NEED from Shri: declare uagents in root project dependencies; this task does not edit pyproject.toml or uv.lock.

Names, public addresses and exact ASI:One commands are in [ADDRESSES.md](ADDRESSES.md). Keep agent/.identity.json private; it is ignored, as are runtime artifacts and private-key patterns. Existing root .env is read, never edited. SubQ is optional for date selection; fixed dates are used when it is absent or fails.

## Real workflow

`rebuild cal` → explorer collects 30 public calendar observations → builder receives training rows only and calls **server.brain.run_cal(lines, on_event)** → verifier independently checks the returned code on nine held-out dates → coordinator replies with measured version history, rules, held-out pass/fail and September 1752 output.

The builder now fails clearly if run_cal is unavailable. It never silently selects the old lookup stub. The legacy stub_builder helper remains only for explicitly injected development fixtures. No successful real result or hosted snapshot is invented.

Current teammate APIs are adapted inside agent/:

- Prefer explorer.cal_runner.run(dates); otherwise use its trace_lines(dates) and normalize to {seq,test,source:"text",args,output,deleted}. A subprocess adapter is used only if neither exists.
- Prefer server.checker.run("cal", code, lines, tests). Otherwise use server.checker.check with temporary code/trace files under ignored agent/.runtime/, adapting globalThis.Cal to the checker factory contract. Test totals become explicit pass/fail records. No files in checker/, explorer/ or copies/ are manually changed by the adapters.
- The real brain's own runtime behavior includes calling configured Meta/Gemini endpoints and saving generated copies/scores. That is distinct from editing source; the strict agent-only task requires approval for those runtime effects before executing it here.

The held-out set includes February/September dates in 1700, 1751 and 1753, plus leap/non-leap February cases. These expected outputs never go to the builder. The verifier ignores the brain's claimed held_pct and measures its own result. The famous 1752 quirk may be prior model knowledge; unseen-input tests provide evidence.

## Chat safety and status

Commands: rebuild cal, rebuild today-run, status, rules, score, tests. Unknown rebuild targets return exactly `Unknown target.` Owner-only start/reset/test compare the authenticated sender to OWNER_ADDRESS. Today-run replay and owner controls remain explicit NEED adapters until supplied. No chat text reaches shell/eval/exec. One rebuild at a time; ten messages per rolling minute per sender. Every stage has a timeout and one retry; successful jobs are cached to avoid repeating side effects on delivery retries.

Mailbox registration has been confirmed in live logs. The real-brain local workflow passed (38.1% → 100% train, independent 9/9 held-out). The new ASI:One web-chat transcript is still pending. See VERIFICATION.md. Local SDK tests are not represented as ASI:One conversations.

## Verify and freeze

```sh
.venv/bin/python -m unittest agent.test_runtime -v
# Runs real model calls and generated-copy writes; requires authorization:
.venv/bin/python -m agent.smoke
# After a real result exists:
.venv/bin/python -m agent.freeze agent/.runtime/snapshot.json
```

The smoke command exchanges actual typed uAgent messages locally and tries rebuild/status/rules/score/tests/unknown. It labels its transcript `local-uagents`, not ASI:One. Live mailbox replies record a separate ignored agent/.runtime/chat-transcript.jsonl. Completed results save snapshot.json; failed or stub results cannot be frozen.

The freeze tool fills hosted_agent.py's SNAPSHOT from real measured results. Paste the standalone file into an Agentverse hosted-agent editor and start that hosted instance. It answers status/rules/score/tests without this laptop. Deployment must be verified in Agentverse; merely saving the file locally does not host it. No remote account credentials are stored here.

Official references: [Chat Protocol / ASI:One example](https://uagents.fetch.ai/docs/examples/asi-1), [mailbox](https://uagents.fetch.ai/docs/agentverse/mailbox), [Bureau](https://uagents.fetch.ai/docs/guides/bureau).
