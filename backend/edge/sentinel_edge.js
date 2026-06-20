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
  const later = new Date(now.getTime() + 15 * 60000);
  
  const today = now.toISOString().split('T')[0];
  const tomorrow = later.toISOString().split('T')[0];
  
  const nowTime = now.toTimeString().split(' ')[0];
  const laterTime = later.toTimeString().split(' ')[0];

  let filter;
  if (today === tomorrow) {
    // Same day
    filter = `or=(and(event_date.eq.${today},event_time.gte.${nowTime},event_time.lte.${laterTime}))`;
  } else {
    // Midnight Crossover
    filter = `or=(and(event_date.eq.${today},event_time.gte.${nowTime}),and(event_date.eq.${tomorrow},event_time.lte.${laterTime}))`;
  }

  try {
    // 1. Scan Calendar for Imminent Events (within 15 minutes)
    const calUrl = `${SUPABASE_URL}/rest/v1/calendar_events?${filter}&select=*`;
    
    const response = await fetch(calUrl, {
      headers: {
        "apikey": SUPABASE_KEY,
        "Authorization": `Bearer ${SUPABASE_KEY}`
      }
    });

    const events = await response.json();
    let routedCount = 0;

    if (Array.isArray(events)) {
      routedCount = events.length;
      for (const event of events) {
        await notifyNeuralCore(event, env);
      }
    } else {
      console.error("[Sentinel Edge] Postgrest returned non-array response:", events);
      return new Response(`Sentinel Scan Error: ${JSON.stringify(events)}`, { status: 500 });
    }

    return new Response(`Sentinel Scan Complete: ${routedCount} events routed.`, { status: 200 });
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
