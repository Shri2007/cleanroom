# Clean Room Fetch.ai agents

Only the coordinator speaks Agent Chat Protocol to users. Explorer, builder, and verifier exchange typed Work/Result messages in one Bureau. The coordinator uses mailbox=True and publishes its Chat Protocol manifest. No payment protocol, database, tunnel, or chat-to-shell execution.

## Start

From the repository root:

```sh
uv pip install --python .venv/bin/python 'uagents==0.26.1' openai
.venv/bin/python -m agent.coordinator --addresses
.venv/bin/python -m agent.coordinator
```

Do not run `uv sync` before a teammate adds uagents to the project dependencies: it may remove the manually installed package. Dependency files outside agent/ were deliberately not edited.

The first run generates an ignored, owner-readable `agent/.identity.json` seed. Keep it safe and never share it; names/addresses are public and printed on startup. Alternatively configure a unique CLEANROOM_AGENT_SEED in the existing environment. OWNER_ADDRESS is the **sending agent address** checked for start/reset/test, not a GitHub name or browser account. Never put seeds or API keys in source. Existing root .env is read, never changed here.

Optional SubQ date selection uses SUBQ_API_KEY, SUBQ_BASE_URL, SUBQ_MODEL. Missing/failed SubQ falls back to 30 fixed dates, including September 1752 and leap/non-leap Februaries. Nine fixed held-out dates cover 1700, 1751, 1753 and February boundary years. Only training outputs go to the builder.

## Connect Agentverse and ASI:One

1. Keep the Bureau running. Open the printed Inspector URL.
2. Sign in to Agentverse, choose **Connect → Mailbox**, and verify the registration logs. mailbox=True and publishing the manifest configure registration, but do not prove account linkage or ASI:One delivery by themselves.
3. Open the coordinator's Agentverse profile, then **Chat with Agent** in ASI:One. Send `rebuild cal`.
4. Verify the reply contains measured version scores, seen/guessed rules, independent held-out tests, and the observed September 1752 calendar.

References: [official ASI:One Chat Protocol example](https://uagents.fetch.ai/docs/examples/asi-1), [mailbox setup](https://uagents.fetch.ai/docs/agentverse/mailbox), [Bureau](https://uagents.fetch.ai/docs/guides/bureau). These fixed commands do not call the ASI:One LLM API, so an ASI1 model API key is not required by this implementation. Your ASI:One chat account and Agentverse connection are still needed for live verification.

SDK 0.26.1 hard-codes its ASGI bind host. Our launcher sets its runtime HOST constant to 127.0.0.1 to keep port 8001 private to this laptop. Mailbox messages arrive over the outbound Agentverse connection; no tunnel is needed. Port 8000 remains the teammate's backend.

## Commands and safety

`rebuild cal`, `rebuild today-run`, `status`, `rules`, `score`, `tests`; owner-only `start`, `reset`, `test`. Unknown rebuild targets return exactly “Unknown target.” URLs and arbitrary commands are rejected. Up to ten messages per rolling minute per sender. Duplicate ChatMessage IDs are acknowledged but not executed twice. One rebuild runs at a time; status remains responsive.

Each workflow step gets a bounded response timeout and one retry (explorer 30s, builder 180s, verifier 15s). Successful worker requests are cached by job and stage so a delivery retry does not rerun side effects. Failure replies name the failed stage and last good version. Workers accept requests only from their coordinator. They do not accept public chat.

## Temporary adapters and honest demo mode

If missing, each interface prints `NEED from teammate: ...` and uses a clearly scoped agent-local adapter:

- explorer.cal_runner.run(dates): agent-local fixed /usr/bin/cal execution with integer validation, no shell.
- server.checker.run("cal", code, lines, tests): agent-local Node VM subprocess, timeouts, permissions, PATH-only environment.
- server.brain.run_cal(lines, on_event): **STUB MODE**, a training-only lookup table. v1 stores ten training observations; v2 stores all training observations. Scores are measured, not invented. On the fixed set this intentionally shows 47.62% → 100% training with **0/9 held-out passing**, not a learned calendar algorithm.

The real brain adapter auto-selects run_cal when it exists at process start/import; restart agents after teammate interface changes. Expected result: {best_version, train_pct, held_pct, rules}. If no code field is included, the agent reads copies/cal_vN.js for the validated best version. It never writes copies/. on_event accepts split/rules/score/done events. A score event contains version, train_pct, held_pct, kept. The independent verifier ignores the brain's claimed held_pct and measures its own held-out score.

`today-run` and owner controls print a NEED response until a teammate supplies fixed adapters. No camera action or saved-trace replay is falsely reported as completed. Stub mode is for chat plumbing only. Human edits and the model may introduce prior knowledge; honest held-out scores, not a claim of novel discovery, are the proof.

## Hosted freeze

Completed runs save an ignored `agent/.runtime/snapshot.json` (no code or credentials). At 3:30 paste the verified snapshot (rules, scores, verification, stub flag and status) into SNAPSHOT in hosted_agent.py and paste that file into the Agentverse hosted editor. The file attaches to the platform-provided agent and has no imports from this repository. It answers status/rules/score/tests only and cannot trigger rebuilds. Freeze results only after an actual run; the default snapshot deliberately contains no invented scores.

## Test

```sh
.venv/bin/python -m unittest discover -s tests -p test_agents.py -v
```

Tests exercise actual uAgent handler functions with a local typed-message transport, real /usr/bin/cal observations and isolated Node scores. They do not prove remote Agentverse registration or ASI:One chat delivery. Never label them as a live ASI:One demo.

## Current verification

Thirteen tests passed across the agent suite and the additional real-SDK dispatch test. The extra test starts the SDK message receivers/dispensers and runs the actual internal request/response flow without registering externally. The live Bureau published the Chat Protocol manifest and registered with the Almanac API. Account mailbox linking and actual ASI:One delivery still need verification. Public identities are in [ADDRESSES.md](ADDRESSES.md).

NEED from teammate: declare uagents==0.26.1 in the root project dependencies; only the virtual environment was updated here.
