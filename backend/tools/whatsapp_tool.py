import urllib.parse
import webbrowser

def send_whatsapp(number: str, message: str) -> str:
    """
    Opens the WhatsApp Desktop app or web via the URI protocol to send a message.
    The user must still click 'Send' in the WhatsApp application.
    """
    try:
        # Format: whatsapp://send?phone=...&text=...
        # Ensure number starts with + or just digits
        clean_number = "".join(filter(str.isdigit, number))
        
        # Safe URL encoding of the message parameter
        safe_message = urllib.parse.quote(message)
        
        uri = f"whatsapp://send?phone={clean_number}&text={safe_message}"
        
        # Open URI safely using webbrowser standard module (uses ShellExecute under the hood on Windows)
        webbrowser.open(uri)
        
        return f"Successfully commanded Windows to initiate a WhatsApp message to {number} with the content: '{message}'."
    except Exception as e:
        return f"Failed to initiate WhatsApp via URI: {e}"
