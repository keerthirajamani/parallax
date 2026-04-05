import sys
import pandas as pd
from datetime import datetime
from zoneinfo import ZoneInfo

from src.utils.common_utils import (
    apply_trailing_sl,
    fetch_candles,
    nse_market_status
)
from src.utils.indicators import three_horse_crow_pandas, ut_bot_alerts
from src.utils.webhook_trigger import webhook_handler
from src.config.symbols import resolve_symbol_map, SYMBOL_REGISTRY

IST = ZoneInfo("Asia/Kolkata")


class SignalProcessor:

    def __init__(self):
        pd.set_option("display.max_rows", None)
        pd.set_option("display.max_columns", None)
        pd.set_option("display.width", None)
        pd.set_option("display.max_colwidth", None)

    def candles_to_df(self, candles):
        df = pd.DataFrame(
            candles,
            columns=["datetime", "open", "high", "low", "close", "volume", "oi"]
        )
        df["datetime"] = pd.to_datetime(df["datetime"])
        df = df.sort_values("datetime").reset_index(drop=True)
        df.set_index("datetime", inplace=True)
        return df

    def get_data(self, symbol, unit, interval, symbol_map):
        instrument = symbol_map[symbol]
        print(f"------ instrument ------{symbol}------")

        all_candles = fetch_candles(instrument, unit, interval)

        df = three_horse_crow_pandas(all_candles, 3)
        # df = ut_bot_alerts(all_candles)

        df = apply_trailing_sl(df)
        df["symbol"] = symbol

        print(df.tail(40).to_string())

        return self.build_signals_from_last_row(df)

    def build_signals_from_last_row(self, df):
        if df.empty:
            return []

        last = df.iloc[-1]
        signals = []

        base_payload = {
            "symbol": last["symbol"],
            "close": float(last["close"]),
            "tsl": last["tsl"],
            "timestamp": last.name.isoformat(),
        }

        if last["sl_hit"]:
            signals.append({**base_payload, "signal_type": "sl"})

        if last["buy"]:
            signals.append({**base_payload, "signal_type": "buy"})

        elif last["sell"]:
            signals.append({**base_payload, "signal_type": "sell"})

        return signals

    def run(self, event, context=None):
        market_status = nse_market_status()
        print("market_status ",market_status)
        # if market_status != "NORMAL_OPEN":
        #     return {
        #         "status": "skipped",
        #         "message": f"Market status: {market_status}"
        #     }

        webhoook_results = []

        unit = event.get("unit")
        interval = event.get("interval")
        entity = event.get("entity")

        print("Unit is", unit)
        print("Interval is", interval)

        Symbols = resolve_symbol_map(entity)

        print("Symbols", Symbols)
        print("current time:", datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S %Z"))

        for Symbol in Symbols:
            signals = self.get_data(Symbol, unit, interval, Symbols)

            if not signals:
                print("No Signal for symbol", Symbol)
                print()
                continue

            event_payload = {
                "mode": entity,
                "unit": unit,
                "instrument": Symbols[Symbol],
                "interval": interval,
                "signals": signals,
            }

            print("Event Payload is", event_payload)

            webhoook_results.append(webhook_handler(event_payload, None))

            # keep/remove based on your need
            sys.exit("Planned Exit")

        print("Webhook results", webhoook_results)
        return True


# ===== Lambda Entry =====

processor = SignalProcessor()

def lambda_handler(event, context):
    return processor.run(event, context)


# ===== Local Test =====

# if __name__ == "__main__":
#     event = {"unit": "hours", "interval": 1, "entity": "INDEX"}
#     print(lambda_handler(event, None))