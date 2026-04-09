import os
from notion_client import Client

def save_note_to_notion(idea: str) -> str:
    """Save an idea or note directly to a designated Notion Page or Database."""
    token = os.getenv("NOTION_TOKEN")
    # Need a specific Page ID to append as an 'item'
    parent_id = os.getenv("NOTION_PAGE_ID") 
    
    if not token or "your" in token:
        return f"Notion Token is missing in .env. JARVIS was unable to save the note: '{idea}'."
    
    if not parent_id:
        return f"NOTION_PAGE_ID is missing in your .env. I need a destination to save your idea: '{idea}'."
        
    try:
        notion = Client(auth=token)
        # Assuming we append to a page as a simple bulleted list item for now
        notion.blocks.children.append(
            block_id=parent_id,
            children=[
                {
                    "object": "block",
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": idea
                                }
                            }
                        ]
                    }
                }
            ]
        )
        return f"Successfully saved your idea to Notion: '{idea}'."
    except Exception as e:
        return f"Failed to save to Notion: {str(e)}"
