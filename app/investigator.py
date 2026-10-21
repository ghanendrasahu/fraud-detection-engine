"""AI Investigator module - generates natural language summaries."""

from __future__ import annotations

from app.config import settings
from app.logging_config import get_logger
from app.schemas import Decision, ReasonCode, TransactionEvent, TransactionFeatures

logger = get_logger(__name__)


def _build_template_summary(
    transaction: TransactionEvent,
    features: TransactionFeatures,
    ml_risk: float,
    graph_penalty: float,
    reasons: list[ReasonCode],
    decision: Decision,
) -> str:
    """Deterministic template-based summary when no LLM is available."""
    parts: list[str] = []

    parts.append(
        f"Transaction ₹{transaction.amount:,.0f} from {transaction.device_id} "
        f"({transaction.ip_address}) was flagged for investigation."
    )

    if features.is_new_device:
        parts.append("The transaction originated from a new device.")

    if features.speed_kmh > 800:
        parts.append(
            f"Impossible travel was detected: the user's previous location "
            f"was {features.speed_kmh:,.0f} km away."
        )

    if features.account_velocity_1h >= 5:
        parts.append(
            f"High transaction velocity: {features.account_velocity_1h} transactions "
            f"in the last hour."
        )

    if features.amount_sum_24h > 100000:
        parts.append(
            f"High 24-hour volume: ₹{features.amount_sum_24h:,.0f} in the last day."
        )

    if graph_penalty > 70:
        parts.append("The device is linked to suspicious entities in the network graph.")

    parts.append(
        f"ML risk score: {ml_risk:.1%}. "
        f"Combined evidence {'indicates elevated fraud risk.' if decision == Decision.INVESTIGATION_REQUIRED else 'does not indicate fraud.'}"
    )

    return " ".join(parts)


def _build_llm_summary(
    transaction: TransactionEvent,
    features: TransactionFeatures,
    ml_risk: float,
    graph_penalty: float,
    reasons: list[ReasonCode],
    decision: Decision,
) -> str | None:
    """Attempt to call an LLM for a richer summary. Returns None on failure."""
    if not settings.LLM_API_KEY:
        return None

    try:
        import requests

        prompt = (
            "You are a fraud investigator. Given the following structured data, "
            "write a 2-3 sentence investigation summary.\n\n"
            f"Transaction ID: {transaction.transaction_id}\n"
            f"Amount: ₹{transaction.amount:,.0f}\n"
            f"Device: {transaction.device_id}\n"
            f"IP: {transaction.ip_address}\n"
            f"New device: {features.is_new_device}\n"
            f"Speed: {features.speed_kmh:.0f} km/h\n"
            f"Velocity (1h): {features.account_velocity_1h}\n"
            f"24h volume: ₹{features.amount_sum_24h:,.0f}\n"
            f"Graph penalty: {graph_penalty:.0f}\n"
            f"ML risk: {ml_risk:.1%}\n"
            f"Decision: {decision.value}\n"
            "Reasons: " + "; ".join(r.message for r in reasons) + "\n"
        )

        resp = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.LLM_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": settings.LLM_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 200,
                "temperature": 0.3,
            },
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()

    except Exception as e:
        logger.warning("LLM call failed, using template fallback: %s", e)
        return None


def generate_investigator_summary(
    transaction: TransactionEvent,
    features: TransactionFeatures,
    ml_risk: float,
    graph_penalty: float,
    reasons: list[ReasonCode],
    decision: Decision,
) -> str:
    """Generate a natural language summary for the investigator."""
    llm_summary = _build_llm_summary(
        transaction, features, ml_risk, graph_penalty, reasons, decision
    )
    if llm_summary:
        return llm_summary

    return _build_template_summary(
        transaction, features, ml_risk, graph_penalty, reasons, decision
    )
