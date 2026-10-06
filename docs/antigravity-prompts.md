# Antigravity prompts for this repo

Use these in Antigravity 2.0, the Antigravity extension in your editor, or the CLI (`agy`). Review every change before you accept it.

## Understand the project

```
Explain this project in five bullets: what each agent folder does, how the tools are defined, and how I run it locally.
```

## Run the checks

```
Run python -m pytest -q, then run python run_answer_key.py access_triage. Summarize the results in a table: request, expected, actual.
```

## Add a tool (the live demo on the live-start branch)

```
In access_triage/tools.py, add a function tool named check_sod_conflicts(email: str, app: str, role: str) -> dict.
It loads data/sod_rules.json. Each rule has role_a and role_b in the form "App:role".
Build the requested entitlement as f"{app}:{role}". If it matches role_a or role_b of a rule, and the person already holds the other role in current_access (from get_employee), add a violation with rule_id, already_holds and reason.
Return status "checked", requested, conflict (bool) and violations. Return status "not_found" if the person is not found.
Write a clear Google-style docstring, because ADK sends it to the model as the tool description.
Then add the tool to TOOLS in access_triage/agent.py, add a step "Call check_sod_conflicts for the requester, app and role." before the decision step, and add the rule "ESCALATE if check_sod_conflicts returns a conflict."
Do not change any other file.
```

## Build your own agent from a short spec

Replace the bracketed parts.

```
Create a new ADK agent in a folder named [my_agent], following the patterns in access_triage.
Goal: [one sentence on what the agent decides or produces].
Tools: [list each tool as name(args) -> what it returns]. Use sample JSON data in [my_agent]/data for now.
Rules the agent must follow: [list them].
Write a clear docstring for every tool. Add a tests/test_[my_agent].py that checks the tools without calling a model.
Do not change any other folder.
```

## Draw the architecture (for your demo-day slide)

An example result is in [architecture.md](architecture.md).

```
Read this repo and create a Mermaid diagram of the architecture: each agent, its tools, the MCP server, the policy guard, and Agent Runtime and Gemini Enterprise as the deployment targets. Use current product names: Agent Runtime is part of Gemini Enterprise Agent Platform, not Vertex AI Agent Engine. Save it as docs/my-architecture.md.
```

With the CLI, you can also try an open-source diagram tool such as Archify (https://github.com/tt-a1i/archify). Review any third-party tool before you install it.
