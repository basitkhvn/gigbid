# ADR 1: One marketplace port, two adapters
Agents never call GigSim/Upwork directly. They call MCP tools on the Marketplace server; the server delegates to a `MarketplaceAdapter` (GigSim or live Upwork) chosen by `marketplace.mode`. **Why:** the graph can't tell which marketplace it uses; live-mode safety (drafts only, throttling) is enforced in one place. **Cost:** an extra hop per call.
