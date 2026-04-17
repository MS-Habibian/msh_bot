from pyrogram import Client
from config import TG_API_ID, TG_API_HASH

# We initialize a Pyrogram client. 
# "user_session" will be the name of the session file created in your root directory.
tg_app = Client(
    "user_session",
    api_id=TG_API_ID,
    api_hash=TG_API_HASH
)
