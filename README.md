# Antigravity + ADK Agent Starter

A small, working agent project you can copy for a hackathon. It shows the patterns that turn a chat demo into something useful:

| Folder | Pattern | What to look at |
|---|---|---|
| `access_triage/` | **Function tools.** One agent, five Python tools. | `tools.py`: the docstrings are what the model reads. |
| `access_triage_panel/` | **Multi-agent.** Three reviewers run in parallel, then a decider merges their findings. | `ParallelAgent`, `SequentialAgent`, `output_key`. |
| `access_triage_mcp/` + `mcp_server/` | **MCP tools.** The same tools, served by an MCP server. The agent gets them over the protocol. | `McpToolset` in the agent, `FastMCP` in the server. |
| `access_triage_guarded/` | **Agent security.** A policy check in code runs before the agent can record a decision. | `access_triage/policy.py`, `before_tool_callback`. |
| `docs/user-delegated-access.md` | **User-delegated access.** How an agent in Gemini Enterprise acts as the signed-in user. | The token pattern and the registration step. |

The scenario: **Cymbal Logistics**, a fictional freight company, triages access requests for three internal apps. The agent recommends APPROVE, DENY or ESCALATE. It never grants access itself. All people, apps and data are fictional.

Swap the JSON files in `access_triage/data/` for your own system, and the patterns still hold.

## Quick start

You need Python 3.10 or later, the Google Cloud CLI, and a Google Cloud project with the Vertex AI API enabled (part of Gemini Enterprise Agent Platform).

```
git clone https://github.com/HuntsDesk/antigravity-adk-starter.git
cd antigravity-adk-starter
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
gcloud auth application-default login
cp .env.example .env          # then set GOOGLE_CLOUD_PROJECT to your project
make env                      # copies .env into each agent folder
python -m pytest -q           # tool, policy and MCP tests: no model calls
adk web
```

Open the address `adk web` prints, pick an agent, and send:

```
Triage access request REQ-1003.
```

Open the event trace to see every tool call and its arguments.

## Sample requests and the answer key

| Request | Expected | Why |
|---|---|---|
| REQ-1001 | APPROVE | Finance analyst asking for a read-only finance role. |
| REQ-1002 | DENY | A contractor asking for production admin. Also breaks rule SOD-02. |
| REQ-1003 | ESCALATE | Rule SOD-01: already holds the conflicting finance role. The panel also spots that the requester is covering for his own manager. |
| REQ-1004 | DENY | The requester is terminated, and still holds access. |
| REQ-1005 | ESCALATE | The app is not in the catalog. The agent must not invent a policy. |
| REQ-1006 | ESCALATE | Rule SOD-01. The justification also contains an instruction aimed at the agent. Try it in `access_triage_guarded`. |

Check an agent against the whole key without the UI:

```
python run_answer_key.py access_triage
python repeat_check.py access_triage REQ-1006 5
```

`repeat_check.py` runs one request several times and counts the outcomes. Model answers vary; run this before you rely on one in a demo.

## Build with Antigravity

Antigravity is Google's agentic development platform. You can reach it several ways: **Antigravity 2.0** (the desktop agent manager), the **Antigravity CLI** (`agy`), and the **Antigravity extension** for editors such as VS Code and JetBrains. Through Gemini Enterprise, your organization can run it under Google Cloud's enterprise controls.

Prompts that work well on this repo are in [docs/antigravity-prompts.md](docs/antigravity-prompts.md): adding a tool, explaining the project, building your own agent from a short spec, and drawing an architecture diagram. The architecture diagram the CLI drew for this repo is in [docs/architecture.md](docs/architecture.md).

To practice, switch to the `live-start` branch. It is the same project without `check_sod_conflicts`, so the agent approves REQ-1003 when it should escalate. Use the add-a-tool prompt to fix it. The panel agent needs that tool, so it does not load on this branch until you add it.

```
git checkout live-start
```

## Deploy to Agent Runtime

```
export PROJECT_ID=your-project-id
./deploy.sh
```

Deployment takes several minutes. It prints a resource name that ends in `reasoningEngines/` and a number. Test it in the Google Cloud console: **Agent Platform > Deployments**, open the agent, then **Playground**.

Only `access_triage/` is deployed. It is self-contained. The MCP version uses a local stdio server, which does not exist in a deployed agent; for production, host the MCP server separately and connect with `StreamableHTTPConnectionParams`.

## Make it available in Gemini Enterprise

You need a Gemini Enterprise app and permission to add agents to it. In the Google Cloud console: **Gemini Enterprise > Apps**, open your app, **Agents > Add agent > Custom agent via Agent Runtime**, then paste the resource name from the deploy step.

If the Gemini Enterprise app is in a different project from the agent, grant the app project's Discovery Engine service agent the **Discovery Engine Service Agent** role in the agent's project.

The **Authorizations** step on that page is where user-delegated access starts. See [docs/user-delegated-access.md](docs/user-delegated-access.md).

## Security notes

Read [docs/agent-security.md](docs/agent-security.md). The short version: instructions are a request, not a control. Put the rules that matter in code.

## Repo layout

```
access_triage/            single agent and the shared tools, data and policy
  tools.py                five function tools (plain Python)
  policy.py               the same rules as deterministic code, plus the guard
  data/                   fictional directory, app policies, SoD rules, requests
access_triage_panel/      multi-agent version
access_triage_mcp/        agent that gets its tools from mcp_server/
access_triage_guarded/    agent with the policy guard
mcp_server/server.py      FastMCP server for the five tools
tests/                    no-model tests for tools, policy, guard and MCP server
docs/                     prompts, user-delegated access, agent security
```

## License

MIT. See [LICENSE](LICENSE).
