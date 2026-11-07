# Real calendar verification

This is the measured local uAgent round-trip, not an ASI:One web-chat transcript.
Backend: server.brain.run_cal. Model: Meta (confirmed successful calls in the run log).
Only training observations were sent to the builder. Independent verifier used nine held-out dates.

## Recorded result

```text
USER: rebuild cal
AGENT: Real calendar reconstruction via server.brain.run_cal.
v2: 38.1% train → v3: 100% train
Independent held-out: 100% (9/9), PASS
✓ seen: September 1752 skips 3–13, goes 1 2 then 14–30.
```

## Independently verified dates

- 9/1700: PASS
- 2/1700: PASS
- 9/1751: PASS
- 2/1751: PASS
- 9/1753: PASS
- 2/1753: PASS
- 2/1900: PASS
- 2/2000: PASS
- 2/2023: PASS

status, rules, score, tests and rebuild unknown were also exercised through actual SDK message dispatch.
The unknown target reply was exactly: Unknown target.

The frozen hosted_agent.py SNAPSHOT comes from this real measured run. It still must be deployed and started in Agentverse before claiming laptop-off availability.

## Remote validation

Mailbox registration is confirmed. A fresh successful ASI:One transcript is pending the user sending the web-chat commands; browser control timed out.
The live coordinator records mailbox replies in ignored agent/.runtime/chat-transcript.jsonl. That record must be inspected before describing any local result as an ASI:One transcript.
