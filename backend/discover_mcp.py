import sys
import os
sys.path.append(os.getcwd())

try:
    from tools.mcp_tool import mcp
    print(f"MCP Type: {type(mcp)}")
    
    # Discovery loop
    targets = ["tools", "get_tools", "list_tools", "all_tools", "_tools", "_list_tool", "get_all_tools"]
    for t in targets:
        if hasattr(mcp, t):
            attr = getattr(mcp, t)
            print(f"FOUND: {t} (Type: {type(attr)})")
            if callable(attr):
                try: print(f"  - CALLABLE {t}() -> {attr()}")
                except Exception as e: print(f"  - ERROR calling {t}: {e}")
            else:
                print(f"  - PROPERTY {t} -> {attr}")
except Exception as e:
    print(f"CRITICAL: Failed to import/inspect mcp: {e}")
