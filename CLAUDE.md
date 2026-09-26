# Robinhood Agentic Trading

This project connects Claude Code to the Robinhood Trading MCP
(`https://agent.robinhood.com/mcp/trading`), configured in `.mcp.json` as the
`robinhood-trading` server.

## Scope of access

- **Read access:** all of the user's Robinhood accounts (including account numbers),
  positions, balances, transactions, order history, watchlists and scans.
- **Trading:** orders can only be placed in the user's **Robinhood Agentic account**.
- **Crypto:** trades only, and only in pairs that Robinhood supports. The agent
  can't transfer, stake or lend crypto. The user needs a Robinhood Crypto account
  and must accept the updated agreement. Agentic crypto trading isn't available in
  some states, including New York.

## Trading rules (always follow)

1. **Never place, modify or cancel an order without explicit confirmation from the
   user in the current conversation.** Before each order, show a summary: account,
   symbol, side, quantity or dollar amount, order type, limit/stop price,
   time-in-force and estimated cost. Wait for a clear "yes".
2. Confirm that the target account is the Agentic account before submitting.
3. Check buying power and current quote before proposing an order. Flag anything
   stale, missing or inconsistent instead of guessing.
4. For multi-order plans (rebalancing, building a portfolio), present the whole
   plan first and get approval for the plan. Then confirm each order unless the
   user explicitly waives per-order confirmation for that plan.
5. Don't treat market analysis, news summaries or bull/bear theses as
   recommendations. State assumptions and uncertainty.
6. Never write account numbers, balances, positions or other account data into
   files in this repository or into commit messages.
7. If an MCP call returns an error from Robinhood, report it verbatim and stop. Do
   not retry order placement automatically, because a retry could create a
   duplicate order.

## Troubleshooting

- Run `/mcp` to check that `robinhood-trading` is connected and authenticated.
- If the connection misbehaves, remove and re-add the server, then authenticate again.
- Opening the Agentic account and authenticating must be done on a desktop browser.
