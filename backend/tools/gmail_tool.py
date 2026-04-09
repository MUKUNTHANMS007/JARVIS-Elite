import os
import base64
import google.genai as genai
from email.mime.text import MIMEText
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly', 'https://www.googleapis.com/auth/gmail.send']

# --- JARVIS Intelligence Brain ---
# Using the stable 2026 'google.genai' SDK
GENAI_API_KEY = os.environ.get("GEMINI_API_KEY")

def get_gmail_service():
    """Retrieve the Gmail service object using OAuth2 credentials."""
    creds = None
    token_path = 'token.json'
    if not os.path.exists(token_path):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        token_path = os.path.join(base_dir, '..', 'token.json')

    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            return None
    return build('gmail', 'v1', credentials=creds)

def get_jarvis_email_briefing() -> str:
    """
    JARVIS High-Intelligence: Batch fetches emails and uses Gemini 
    to provide a 2-sentence executive summary of what matters.
    """
    try:
        service = get_gmail_service()
        if not service: return "Sir, I'm unable to access your terminal for Gmail sync."

        results = service.users().messages().list(userId='me', q='category:primary', maxResults=15).execute()
        messages = results.get('messages', [])
        
        if not messages:
            return "Your primary inbox is pristine, Sir. No action required."

        raw_data = []
        for msg in messages:
            try:
                m = service.users().messages().get(
                    userId='me', id=msg['id'], format='metadata', 
                    metadataHeaders=['Subject', 'From']
                ).execute()
                headers = m['payload']['headers']
                subj = next((h['value'] for h in headers if h['name'] == 'Subject'), 'N/A')
                sender = next((h['value'] for h in headers if h['name'] == 'From'), 'N/A')
                raw_data.append(f"From: {sender} | Subj: {subj} | Snippet: {m.get('snippet', '')}")
            except: continue

        if not raw_data: return "Inbox scanned. No primary updates found."

        # 1. BRAIN SETUP: Initialize the New 2026 GenAI Client
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key: return "Intelligence Hub Error: API key missing."
        client = genai.Client(api_key=api_key)

        prompt = f"""
        Analyze these emails for Mukunthan (PSG iTech Student).
        Your task is to identify and prioritize: 
        1. Security/Auth (Password resets, login alerts, e.g. Mathpix).
        2. Finance/Subcriptions (Payment failures, receipts, e.g. Spotify, Google Play).
        3. Academic/Career (Placements, Internships, Exams, Lab Records, e.g. Indeed).
        4. Competitive Events (Hackathons, Coding contests, e.g. Codeforces).

        Provide a concise, high-intelligence executive briefing in 4 sentences max.
        
        CRITICAL: Identify the specific entity (e.g. Spotify, Mathpix) and the required action.
        
        Emails:
        {chr(10).join(raw_data)}
        """

        # 2. NEURAL DISCOVERY (2.0-Native Discovery Loop)
        try:
            # List models and filter for generateContent capability
            models = list(client.models.list())
            
            # Prioritize models for the 2026 PSG iTech environment
            discovery_order = ["3.1-flash", "2.5-flash", "flash", "pro"]
            target_model = None
            
            for keyword in discovery_order:
                target_model = next((m.name for m in models if keyword in m.name.lower()), None)
                if target_model: break
            
            if not target_model and models:
                target_model = models[0].name
            
            if not target_model:
                return "Sir, I've scanned the mail but no authorized intelligence models were found."

            # Generate the Briefing
            response = client.models.generate_content(
                model=target_model,
                contents=prompt
            )
            return response.text.strip()
            
        except Exception as e:
            return f"Sir, I've scanned the mail but the intelligence hub encountered a drift: {str(e)}"
    except Exception as e:
        return f"Neural Error: {str(e)}"

def check_gmail_inbox() -> str:
    """Retrieve an accurate, precise count and high-fidelity summary of recent Primary unread emails."""
    try:
        service = get_gmail_service()
        if not service:
            return "Gmail check failed: Not authenticated."
        
        # Recency-Focused Precision: Primary tab messages from the last 48 hours.
        # This is the most effective way to eliminate 'Ghost' unread counts.
        query = 'label:INBOX is:unread -label:CATEGORY_SOCIAL -label:CATEGORY_PROMOTIONS -label:CATEGORY_UPDATES -label:CATEGORY_FORUMS newer_than:2d'
        results = service.users().messages().list(userId='me', q=query, maxResults=500).execute()
        messages = results.get('messages', [])
        total_precise = len(messages)
        
        if total_precise == 0:
            return "Your primary inbox is clear for the last 48 hours, Sir."
            
        # Neural Proof: Fetch the latest 3 to prove real-time intelligence
        proof = []
        for msg in messages[:3]:
            try:
                m = service.users().messages().get(userId='me', id=msg['id'], format='metadata', metadataHeaders=['From']).execute()
                sender = next((h['value'] for h in m['payload']['headers'] if h['name'] == 'From'), 'Unknown')
                proof.append(sender.split('<')[0].strip())
            except: continue
        
        proof_str = f" Recent updates from: {', '.join(proof)}." if proof else ""
        print(f"Verification: Found {total_precise} messages.")
        return f"You have {total_precise} primary unread emails.{proof_str}"
    except Exception as e:
        return f"Gmail API error: {e}"

def get_gmail_briefing(limit: int = 5) -> str:
    """Forward compatibility alias for the intelligence layer."""
    return get_jarvis_email_briefing()

def get_unread_count_raw() -> int:
    """Return an accurate, precise integer count of recent Primary unread messages (last 48h)."""
    try:
        service = get_gmail_service()
        if not service: return 0
        # Recency-Focused: Only count 'True' primary unread messages
        query = 'label:INBOX is:unread -label:CATEGORY_SOCIAL -label:CATEGORY_PROMOTIONS -label:CATEGORY_UPDATES -label:CATEGORY_FORUMS newer_than:2d'
        results = service.users().messages().list(userId='me', q=query, maxResults=500).execute()
        messages = results.get('messages', [])
        return len(messages)
    except Exception as e:
        print(f"[Gmail Error] Count sync failed: {e}")
        return 0

def get_smart_email_notifications(limit: int = 15) -> str:
    """Forward compatibility alias for the intelligence layer."""
    return get_jarvis_email_briefing()

def send_email(to: str, subject: str, message_text: str) -> str:
    """Send an email via Gmail API."""
    try:
        service = get_gmail_service()
        if not service:
            return "Gmail sending failed: Not authenticated."
        message = MIMEText(message_text)
        message['to'] = to
        message['subject'] = subject
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        service.users().messages().send(userId='me', body={'raw': raw}).execute()
        return f"Official email successfully sent to {to}."
    except Exception as e:
        return f"Failed to send email: {e}"
