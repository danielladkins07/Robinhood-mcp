# Robinhood MCP

A Claude Code workspace for **Robinhood Agentic Trading** through the Robinhood
Trading MCP (Model Context Protocol) server:

```
https://agent.robinhood.com/mcp/trading
```

## What's in here

| File | Purpose |
| --- | --- |
| `.mcp.json` | Registers the `robinhood-trading` HTTP MCP server for this project |
| `.claude/settings.json` | Enables that server and requires approval for **every** Robinhood tool call |
| `CLAUDE.md` | Guardrails for the agent: confirm before every order, check the account and buying power, never store account data in the repo |

## Setup (Claude Code)

1. You need a primary Robinhood individual investing account in good standing.
2. Clone this repo and start Claude Code in it: `claude`
3. Approve the project MCP server `robinhood-trading` when prompted.
   (Or add it globally: `claude mcp add robinhood-trading --transport http https://agent.robinhood.com/mcp/trading`)
4. Type `/mcp`, select **robinhood-trading** and authenticate.
5. During authentication, Robinhood prompts you to open an **Agentic account**.
   Finish the on-screen steps. This has to be done on a **desktop browser**, so on
   mobile, copy the onboarding URL and open it on a desktop.

Other clients (Claude Desktop, ChatGPT, Codex, Cursor, Grok and more) connect with
the same MCP URL. See Robinhood's *Agentic Trading overview* help article.

## Example prompts

- "What's my portfolio value and buying power across my accounts?"
- "Look at my portfolio and tell me what risks I'm exposed to."
- "Rebalance my Agentic account to 20% ROAR / 80% HMNI. Show me the plan first."
- "Build a bull and bear thesis for ROAR from recent news and quotes."

## Permissions

`.claude/settings.json` puts every `mcp__robinhood-trading` tool under **ask**, so
Claude Code asks you before each call, including read-only ones. To skip prompts
for read-only tools, add their names (run `/mcp` to see them) to `permissions.allow`
in `.claude/settings.local.json`. Keep order-placement tools on **ask**.

## Risks

You're responsible for every trade your agent places. AI agents can make
mistakes, misread instructions or act on stale data. Agentic trading carries
significant risk, including loss of your entire investment. Only the Agentic
account can be traded. Crypto trading needs a linked Robinhood Crypto account
and isn't available in every state (for example, New York). Nothing in this repo
is investment advice.
