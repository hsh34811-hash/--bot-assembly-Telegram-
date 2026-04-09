# =============================================
# Developer : ✘ 𝙍𝘼𝙑𝙀𝙉
# Telegram  : @P_X_24
# =============================================

import os
import sys
import logging

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)

# معرف التطبيق - احصل عليه من my.telegram.org
API_ID = int(os.environ.get("API_ID", ""))

# هاش التطبيق - احصل عليه من my.telegram.org
API_HASH = os.environ.get("API_HASH", "")

# توكن البوت - احصل عليه من @BotFather
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")

# معرف المالك (Sudo) - ضع هنا الـ Telegram ID بتاعك
SUDO_ID = os.environ.get("SUDO_ID", "")

if not BOT_TOKEN:
    print("Error: BOT_TOKEN is not set. Please set it as an environment variable.")
    sys.exit(1)

if not SUDO_ID:
    print("Error: SUDO_ID is not set. Please set it as an environment variable.")
    sys.exit(1)

RUNNING_PROCESSES = {}
CLIENTS = {}
WHAT_NEED_TO_DO_ECHO = {}
POINTS_DATA = {}

if not os.path.isdir("echo_ac"):
    os.makedirs("echo_ac")
