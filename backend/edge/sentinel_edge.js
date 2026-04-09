// J.A.R.V.I.S. Neural Sentinel (Edge Worker)
// Deployment: Cloudflare Workers / Cron Trigger
// Logic: Sub-millisecond surveillance of high-priority triggers.

export default {
  async scheduled(event, env, ctx) {
    ctx.waitUntil(handleSentinelCheck(env));
  },
  
  async fetch(request, env) {
    // Manual trigger support
    return await handleSentinelCheck(env);
  }
};

async function handleSentinelCheck(env) {
  const { SUPABASE_URL, SUPABASE_KEY, NEURAL_CORE_URL, NEURAL_EDGE_SECRET } = env;

  if (!SUPABASE_URL || !SUPABASE_KEY || !NEURAL_CORE_URL || !NEURAL_EDGE_SECRET) {
    console.error("[Sentinel Edge] Drift: Missing environment variables.");
    return new Response("Missing env", { status: 500 });
  }

  const now = new Date();
  const today = now.toISOString().split('T')[0];
  const fifteenMinsLater = new Date(now.getTime() + 15 * 60000).toISOString();

  try {
    // 1. Scan Calendar for Imminent Events (within 15 minutes)
    const calUrl = `${SUPABASE_URL}/rest/v1/calendar_events?event_date=eq.${today}&event_time=gte.${now.toTimeString().split(' ')[0]}&event_time=lte.${new Date(now.getTime() + 15 * 60000).toTimeString().split(' ')[0]}&select=*`;
    
    const response = await fetch(calUrl, {
      headers: {
        "apikey": SUPABASE_KEY,
        "Authorization": `Bearer ${SUPABASE_KEY}`
      }
    });

    const events = await response.json();

    if (events && events.length > 0) {
      for (const event of events) {
        await notifyNeuralCore(event, env);
      }
    }

    return new Response(`Sentinel Scan Complete: ${events.length} events routed.`, { status: 200 });
  } catch (err) {
    console.error(`[Sentinel Edge] Scan Fail: ${err}`);
    return new Response("Scan Fail", { status: 500 });
  }
}

async function notifyNeuralCore(event, env) {
  const { NEURAL_CORE_URL, NEURAL_EDGE_SECRET } = env;
  const payload = JSON.stringify({
    type: "PROACTIVE_TRIGGER",
    event_id: event.id,
    title: event.title,
    timestamp: Date.now()
  });

  // --- NEURAL SIGNATURE (HMAC-SHA256 Mapping) ---
  const encoder = new TextEncoder();
  const key = await crypto.subtle.importKey(
    "raw", 
    encoder.encode(NEURAL_EDGE_SECRET),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"]
  );
  const signature = await crypto.subtle.sign("HMAC", key, encoder.encode(payload));
  const signatureHex = Array.from(new Uint8Array(signature))
    .map(b => b.toString(16).padStart(2, '0'))
    .join('');

  // Push Trigger to Unified Backend
  await fetch(`${NEURAL_CORE_URL}/api/neural/edge-trigger`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Neural-Signature": signatureHex
    },
    body: payload
  });
  
  console.log(`[Sentinel Edge] Signal Dispatched: ${event.title}`);
}
