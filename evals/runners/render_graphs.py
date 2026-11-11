"""Render both graphs from code (Mermaid) -> docs/images/*.mmd (GitHub renders Mermaid in Markdown)."""
import os
import tempfile

os.environ.setdefault("GIGBID_STATE_DIR", tempfile.mkdtemp())
from agent.config import ROOT  # noqa: E402
from agent.graphs.bid_graph import build_bid_graph  # noqa: E402
from agent.graphs.conversation_graph import build_conversation_graph  # noqa: E402

out = ROOT / "docs/images"
out.mkdir(parents=True, exist_ok=True)
for name, g in (("bid_graph", build_bid_graph()), ("conversation_graph", build_conversation_graph())):
    (out / f"{name}.mmd").write_text(g.get_graph().draw_mermaid())
    print("wrote", out / f"{name}.mmd")
