"""test_main_memgraph.py"""
import asyncio

from web.main import get_memory_graph
from active import memgraph


def test_memory_graph_endpoint_returns_nodes_edges(monkeypatch):
    monkeypatch.setattr(memgraph, "find_sources",
                        lambda: [("2026-08-13.md", "【爱好】主人喜欢薄荷\n你怕打雷\n")])
    out = asyncio.run(get_memory_graph())
    assert set(out) == {"nodes", "edges"}
    assert any(n["type"] == "you" for n in out["nodes"])
    assert any(e["rel"] == "关于" for e in out["edges"])


def test_memory_graph_empty_when_no_sources(monkeypatch):
    monkeypatch.setattr(memgraph, "find_sources", lambda: [])
    out = asyncio.run(get_memory_graph())
    assert out == {"nodes": [], "edges": []}
