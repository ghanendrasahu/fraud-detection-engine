const API_BASE = '';

export async function processTransaction(txn) {
  const resp = await fetch(`${API_BASE}/v1/transactions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(txn),
  });
  if (!resp.ok) throw new Error(`API error: ${resp.status}`);
  return resp.json();
}

export async function fetchHealth() {
  const resp = await fetch(`${API_BASE}/health`);
  if (!resp.ok) throw new Error(`Health check failed: ${resp.status}`);
  return resp.json();
}

export async function fetchModelInfo() {
  const resp = await fetch(`${API_BASE}/v1/model/info`);
  if (!resp.ok) throw new Error(`Model info failed: ${resp.status}`);
  return resp.json();
}
