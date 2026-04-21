import sys
import json
from dotenv import load_dotenv

load_dotenv()

mode = sys.argv[1]

if mode == "signals":
    from src.signals.signal_generation_engine import lambda_handler
    event = json.loads(sys.argv[2])
    lambda_handler(event, None)

elif mode == "token_refresh":
    from src.dhan.access_token_updater import lambda_handler
    lambda_handler({}, None)
