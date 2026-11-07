# Agent identities

Public identities printed from the current local seed. Do not copy or publish the seed itself. Re-run `python -m agent.coordinator --addresses` if the seed changes.

| Role | Name | Address |
| --- | --- | --- |
| Coordinator | cleanroom-coordinator-ee13ec | `agent1qvknkpk00qmxeuxzkfv2w6xwe4pdmm60l25wju8rvekzxeacwv7vkzj6cmv` |
| Explorer | cleanroom-explorer-ee13ec | `agent1qds302wfpy5zs5erqycl3009rlgyscs8hxeveekmkehfp4p98djz2d2dgud` |
| Builder | cleanroom-builder-ee13ec | `agent1qtnplcu8dp8atg38net0xdgctlaq0l097604eahunjy00ch40y2hw5s4x30` |
| Verifier | cleanroom-verifier-ee13ec | `agent1qd53r9v2r58xcy9e3mzxd7n49226jm03zcyr847m9w340g2m59zdws4tkcw` |

Only the coordinator is an external chat entry point. Workers are locally reachable inside the Bureau and do not need public inbound endpoints.

Live launch confirmed Chat Protocol manifest publication and successful batch registration on the Almanac API. Account mailbox linking and an actual ASI:One conversation remain unverified. No on-chain payment was made or is needed for the local test.

[Connect the coordinator mailbox](https://agentverse.ai/inspect/?uri=http%3A%2F%2F127.0.0.1%3A8001&address=agent1qvknkpk00qmxeuxzkfv2w6xwe4pdmm60l25wju8rvekzxeacwv7vkzj6cmv)

## Exact ASI:One commands

Find **cleanroom-coordinator-ee13ec** in Agentverse, open its profile, and choose **Chat with Agent**. Keep the local Bureau running for live rebuilds. ASI:One may retain the @agent mention; the command parser accepts its own leading mention.

```text
@agent1qvknkpk00qmxeuxzkfv2w6xwe4pdmm60l25wju8rvekzxeacwv7vkzj6cmv rebuild cal
@agent1qvknkpk00qmxeuxzkfv2w6xwe4pdmm60l25wju8rvekzxeacwv7vkzj6cmv status
@agent1qvknkpk00qmxeuxzkfv2w6xwe4pdmm60l25wju8rvekzxeacwv7vkzj6cmv rules
@agent1qvknkpk00qmxeuxzkfv2w6xwe4pdmm60l25wju8rvekzxeacwv7vkzj6cmv score
@agent1qvknkpk00qmxeuxzkfv2w6xwe4pdmm60l25wju8rvekzxeacwv7vkzj6cmv tests
@agent1qvknkpk00qmxeuxzkfv2w6xwe4pdmm60l25wju8rvekzxeacwv7vkzj6cmv rebuild unknown
```

The final command must reply exactly `Unknown target.` The first command must use `server.brain.run_cal`; implicit stub fallback is disabled. Verifier outputs include held-out dates around 1700, 1751 and 1753.

The mailbox connection was confirmed in the live service logs. This file does not claim that a new real-brain ASI:One run has passed until its transcript is captured.

## Hosted freeze agent

`hosted_agent.py` is standalone source for the Agentverse hosted editor. `python -m agent.freeze <agent-local snapshot.json>` fills it from a measured real result and rejects stub snapshots. The hosted instance's public address is assigned by Agentverse after deployment; no address is invented here. The hosted service, once deployed and started, can answer read-only commands while the demo laptop is off.
