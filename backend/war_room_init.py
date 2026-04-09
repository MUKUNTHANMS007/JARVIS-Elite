import asyncio
import json
from tools.leetcode_tool import sync_leetcode_intelligence, get_placement_roadmap

async def main():
    try:
        stats = await sync_leetcode_intelligence()
        roadmap = await get_placement_roadmap()
        print(json.dumps({"stats": stats, "roadmap": roadmap}))
    except Exception as e:
        print(json.dumps({"error": str(e)}))

if __name__ == "__main__":
    asyncio.run(main())
