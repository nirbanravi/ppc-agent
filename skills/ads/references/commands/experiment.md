# /ads experiment [platform] [idea]

Goal: a prioritised test backlog the client can actually run and read.

## Steps
1. Base ideas on findings (`--from <audit run>`) wherever possible; each experiment lists `based_on_findings`.
2. For each experiment write: hypothesis (if X then Y because Z), primary metric, guardrails, design, MDE, duration, budget, decision rule, priority.
3. Design choice, strongest first: platform-native split/lift test (verify the tool exists and its current requirements online) → geo split → campaign/budget split → pre/post with a holdout window. Say which one and why; pre/post caps confidence at medium.
4. Duration/MDE: estimate from the account's own daily conversions. Rough rule for a two-arm test on conversion rate: n per arm ≈ 16·p(1−p)/(p·MDE)². Show the inputs. If the account cannot reach significance in 6 weeks, say so and suggest a bigger MDE or a higher-volume proxy metric.
5. Do not run tests on broken tracking.
6. Put experiments in `analyst.json → experiments`; finalize; reply with the top 3 and their decision rules.

Launching an experiment that changes the account goes through `/ads create` or `/ads optimize` changesets.
