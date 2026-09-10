"""Graph engine using NetworkX for entity-link analysis."""

from __future__ import annotations

from typing import Any

import networkx as nx  # type: ignore[import-untyped]

from app.config import settings
from app.logging_config import get_logger

logger = get_logger(__name__)


class GraphEngine:
    """Maintains an in-memory transaction graph and computes graph-based risk."""

    def __init__(self) -> None:
        self.graph = nx.Graph()
        self._suspicious_devices: set[str] = set(settings.SUSPICIOUS_DEVICES)
        self._suspicious_ips: set[str] = set(settings.SUSPICIOUS_IPS)
        self._suspicious_users: set[str] = set(settings.SUSPICIOUS_USERS)

    # ---- node / edge helpers ----------------------------------------------

    def _user_node(self, user_id: str) -> str:
        return f"USER:{user_id}"

    def _device_node(self, device_id: str) -> str:
        return f"DEVICE:{device_id}"

    def _ip_node(self, ip: str) -> str:
        return f"IP:{ip}"

    def _is_suspicious(self, node_id: str) -> bool:
        if node_id.startswith("DEVICE:"):
            return node_id[7:] in self._suspicious_devices
        if node_id.startswith("IP:"):
            return node_id[3:] in self._suspicious_ips
        if node_id.startswith("USER:"):
            return node_id[5:] in self._suspicious_users
        return False

    # ---- public API -------------------------------------------------------

    def add_transaction(self, user_id: str, device_id: str, ip_address: str) -> None:
        """Add a transaction's entities and relationships to the graph."""
        u = self._user_node(user_id)
        d = self._device_node(device_id)
        ip = self._ip_node(ip_address)

        for node_id, ntype in [(u, "USER"), (d, "DEVICE"), (ip, "IP")]:
            if not self.graph.has_node(node_id):
                self.graph.add_node(node_id, node_type=ntype, label=node_id)

        if not self.graph.has_edge(u, d):
            self.graph.add_edge(u, d, relationship="USES")
        if not self.graph.has_edge(u, ip):
            self.graph.add_edge(u, ip, relationship="CONNECTED_FROM")
        if not self.graph.has_edge(d, u):
            self.graph.add_edge(d, u, relationship="SEEN_WITH")
        if not self.graph.has_edge(ip, u):
            self.graph.add_edge(ip, u, relationship="USED_BY")

    def compute_graph_penalty(self, user_id: str, device_id: str, ip_address: str) -> float:
        """Compute a penalty score (0-100) based on graph relationships."""
        penalty = 0.0

        u = self._user_node(user_id)
        d = self._device_node(device_id)
        ip = self._ip_node(ip_address)

        if d in self.graph and self._is_suspicious(d):
            penalty += 80.0
            logger.info("Suspicious device detected: %s", device_id)

        if ip in self.graph and self._is_suspicious(ip):
            penalty += 70.0
            logger.info("Suspicious IP detected: %s", ip_address)

        # Direct neighbor check
        if u in self.graph:
            for neighbor in self.graph.neighbors(u):
                if self._is_suspicious(neighbor):
                    penalty += 60.0
                    logger.info("Connection to suspicious entity: %s", neighbor)

            # 2-hop check for suspicious users
            for neighbor in self.graph.neighbors(u):
                if neighbor.startswith("DEVICE:") or neighbor.startswith("IP:"):
                    for hop2 in self.graph.neighbors(neighbor):
                        if hop2 != u and hop2.startswith("USER:") and self._is_suspicious(hop2):
                            penalty += 40.0
                            logger.info("2-hop connection to suspicious user: %s", hop2)
                            break

        return min(penalty, 100.0)

    def get_2hop_neighborhood(self, user_id: str) -> dict[str, Any]:
        """Return a 2-hop subgraph around the user for investigation view."""
        u = self._user_node(user_id)
        if u not in self.graph:
            return {"nodes": [], "edges": []}

        neighborhood: set[str] = {u}
        for hop1 in self.graph.neighbors(u):
            neighborhood.add(hop1)
            for hop2 in self.graph.neighbors(hop1):
                neighborhood.add(hop2)

        subgraph = self.graph.subgraph(neighborhood)

        nodes = []
        for nid, data in subgraph.nodes(data=True):
            nodes.append({
                "id": nid,
                "label": nid,
                "node_type": data.get("node_type", "UNKNOWN"),
                "suspicious": self._is_suspicious(nid),
            })

        edges = []
        for src, tgt, data in subgraph.edges(data=True):
            edges.append({
                "source": src,
                "target": tgt,
                "relationship": data.get("relationship", "LINKED"),
            })

        return {"nodes": nodes, "edges": edges}

    def health_check(self) -> str:
        return "ready"
