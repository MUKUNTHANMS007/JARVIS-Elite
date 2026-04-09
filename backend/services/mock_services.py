import random

async def get_unread_count() -> int:
    return random.randint(1, 15)

async def get_notification_count() -> int:
    return random.randint(0, 8)

async def get_update_count() -> int:
    return random.randint(0, 5)
