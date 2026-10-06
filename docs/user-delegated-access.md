# User-delegated access

## The idea

A hackathon agent usually calls APIs with one key or one service account. That account can see everything, so every user of the agent can too.

User-delegated access means the agent calls the API **as the person using it**. The user signs in once (OAuth), and the agent receives that user's access token. The API then applies that user's own permissions.

## How it works with Gemini Enterprise

1. **Create an OAuth client** for the API you want to call. Add this redirect URI:
   `https://vertexaisearch.cloud.google.com/static/oauth/oauth.html`
2. **Register the agent in Gemini Enterprise** (Agents > Add agent > Custom agent via Agent Runtime). On the **Authorizations** step, click **Add authorization** and fill in **Authorization name**, **Client ID**, **Client secret**, **Token URI** and **Authorization URI**. Tick **PKCE verification enabled** if your OAuth provider supports it. The authorization name cannot be changed later, and your code uses it to find the token.
3. **Users sign in once.** The first time someone uses the agent, Gemini Enterprise asks them to authorize it.
4. **The agent reads the token from session state** and calls the API with it.

## Reading the token in a tool

This pattern follows Google's codelab [Integrate Gemini Enterprise Agents with Google Workspace](https://codelabs.developers.google.com/ge-gws-agents). Gemini Enterprise places the token in session state under a key that starts with the authorization name. Check the codelab for the current details before you rely on it.

```python
import re
from google.adk.tools.tool_context import ToolContext

AUTH_NAME = "my-authorization"   # the Authorization name you entered in Gemini Enterprise


def _user_token(tool_context: ToolContext) -> str | None:
    state = tool_context.state.to_dict() if hasattr(tool_context.state, "to_dict") else tool_context.state
    pattern = re.compile(rf"^{re.escape(AUTH_NAME)}_\d+$")
    for key, value in state.items():
        if pattern.match(key):
            return value
    return None


def list_my_tickets(tool_context: ToolContext) -> dict:
    """List the signed-in user's open tickets."""
    token = _user_token(tool_context)
    if not token:
        return {"status": "not_authorized", "message": "Ask the user to authorize the agent."}
    # Call your API with: headers={"Authorization": f"Bearer {token}"}
    ...
```

ADK passes `tool_context` to any tool that declares it. The model does not see it.

## Checklist before real users

- The OAuth client asks only for the scopes the tools need.
- Tools fail closed: no token means no call.
- Tokens are never logged or returned to the model.
- The policy guard still runs. Delegated access limits what the user can reach; the guard limits what the agent may decide.
