import os

def send_whatsapp(number: str, message: str) -> str:
    """
    Opens the WhatsApp Desktop app or web via the URI protocol to send a message.
    The user must still click 'Send' in the WhatsApp application.
    """
    try:
        # Format: whatsapp://send?phone=...&text=...
        # Ensure number starts with + or just digits
        clean_number = "".join(filter(str.isdigit, number))
        
        # URI encode message (basic)
        safe_message = message.replace(" ", "%20")
        
        uri = f"whatsapp://send?phone={clean_number}&text={safe_message}"
        os.system(f"start {uri}")
        
        return f"Successfully commanded Windows to initiate a WhatsApp message to {number} with the content: '{message}'."
    except Exception as e:
        return f"Failed to initiate WhatsApp via URI: {e}"
