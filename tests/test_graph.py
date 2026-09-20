"""Tests for the graph engine."""

from __future__ import annotations

import pytest  # type: ignore[import-untyped]

from app.graph_engine import GraphEngine


class TestGraphEngine:
    """Test graph construction, suspicious detection, and penalties."""

    def setup_method(self) -> None:
        self.engine = GraphEngine()

    def test_add_transaction_creates_nodes(self) -> None:
        self.engine.add_transaction("user_1", "device_1", "10.0.0.1")
        assert self.engine.graph.has_node("USER:user_1")
        assert self.engine.graph.has_node("DEVICE:device_1")
        assert self.engine.graph.has_node("IP:10.0.0.1")

    def test_add_transaction_creates_edges(self) -> None:
        self.engine.add_transaction("user_1", "device_1", "10.0.0.1")
        assert self.engine.graph.has_edge("USER:user_1", "DEVICE:device_1")
        assert self.engine.graph.has_edge("USER:user_1", "IP:10.0.0.1")
        assert self.engine.graph.has_edge("DEVICE:device_1", "USER:user_1")
        assert self.engine.graph.has_edge("IP:10.0.0.1", "USER:user_1")

    def test_suspicious_device_penalty(self) -> None:
        self.engine.add_transaction("user_1", "device_suspicious_01", "10.0.0.1")
        penalty = self.engine.compute_graph_penalty("user_1", "device_suspicious_01", "10.0.0.1")
        assert penalty >= 80

    def test_suspicious_ip_penalty(self) -> None:
        self.engine.add_transaction("user_1", "device_1", "10.10.10.10")
        penalty = self.engine.compute_graph_penalty("user_1", "device_1", "10.10.10.10")
        assert penalty >= 70

    def test_suspicious_user_connection(self) -> None:
        self.engine.add_transaction("user_flagged_01", "device_1", "10.0.0.1")
        self.engine.add_transaction("user_1", "device_1", "10.0.0.1")
        penalty = self.engine.compute_graph_penalty("user_1", "device_1", "10.0.0.1")
        assert penalty >= 60

    def test_penalty_capped_at_100(self) -> None:
        self.engine.add_transaction("user_1", "device_suspicious_01", "10.10.10.10")
        penalty = self.engine.compute_graph_penalty("user_1", "device_suspicious_01", "10.10.10.10")
        assert penalty <= 100

    def test_2hop_neighborhood(self) -> None:
        self.engine.add_transaction("user_1", "device_1", "10.0.0.1")
        self.engine.add_transaction("user_1", "device_2", "10.0.0.2")
        result = self.engine.get_2hop_neighborhood("user_1")
        assert len(result["nodes"]) >= 3
        assert len(result["edges"]) >= 4

    def test_2hop_neighborhood_empty(self) -> None:
        result = self.engine.get_2hop_neighborhood("nonexistent_user")
        assert result["nodes"] == []
        assert result["edges"] == []

    def test_graph_penalty_normal_entities(self) -> None:
        self.engine.add_transaction("user_1", "device_1", "10.0.0.1")
        penalty = self.engine.compute_graph_penalty("user_1", "device_1", "10.0.0.1")
        assert penalty == 0.0
