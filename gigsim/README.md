# gigsim/ (reserved for the instructor-provided simulator)

The official GigSim simulator was **not** included in the starter kit zip I received
(`GigBid_Student_Starter_Kit_v0.1.zip`: scaffold only). To remain runnable, this repo ships a
clearly separate stand-in in `gigsim_local/` that implements the same surface the assignment
describes (jobs, clients with hidden preferences, Connects, proposals, messages, rate limits,
occasional 5xx). When the official `gigsim/` is dropped into this folder, only the base URL in
`agent/config.yaml` (`marketplace.gigsim_url`) and the adapter field mapping in
`mcp_servers/marketplace/adapters/gigsim.py` need to change. Nothing in this folder is edited by me.
