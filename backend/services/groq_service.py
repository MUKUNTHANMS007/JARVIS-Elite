import os
from groq import AsyncGroq

# Reusing the existing API key
client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))

async def summarize_inbox(gmail: int, github: int, notion: int) -> str:
    total = gmail + github + notion
    if total == 0:
        return "All clear. No new updates."

    prompt = f"""
    Gmail: {gmail} unread, GitHub: {github} notifications, Notion: {notion} updates.
    Write ONE short sentence describing where most messages are from.
    Example: "Primarily updates from GitHub and Notion pipelines."
    Just the sentence, nothing else.
    """
    try:
        response = await client.chat.completions.create(
            model="llama-3.1-8b-instant",  # fast small model
            messages=[{"role": "user", "content": prompt}],
            max_tokens=30
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Summarize Error: {e}")
        return "System incoming data pipeline aggregated."
