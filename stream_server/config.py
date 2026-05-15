import os

from dotenv import load_dotenv

load_dotenv()

MAIN_BACKEND_URL = os.getenv("MAIN_BACKEND_URL")
SFU_INTERNAL_SECRET = os.getenv("SFU_INTERNAL_SECRET")
SFU_HEARTBEAT_INTERVAL_SECONDS = int(
    os.getenv("SFU_HEARTBEAT_INTERVAL_SECONDS")
)

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")

FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN")
Max_MSG_LEN = int(os.getenv("Max_MSG_LEN", "280"))

def get_internal_headers() -> dict[str, str]:
    return {
        "X-SFU-Secret": SFU_INTERNAL_SECRET or "",
    }
