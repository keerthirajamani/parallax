"""
Paper Trading Execution Engine
================================
Processes signal payloads and manages paper orders, positions, and P&L.
Designed so the execution layer can be swapped to a real broker in future.
"""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field, asdict


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class Order:
    order_id: str
    symbol: str
    side: str           # 'BUY' | 'SELL'
    qty: float
    price: float
    order_type: str     # 'MARKET' | 'SL' | 'TSL'
    status: str         # 'FILLED' | 'REJECTED' | 'CANCELLED'
    timestamp: str
    trigger_price: Optional[float] = None
    notes: str = ""

    def to_dict(self):
        return asdict(self)


@dataclass
class Position:
    symbol: str
    qty: float
    avg_price: float
    entry_time: str
    mode: str           # 'EQUITY' | 'FNO' etc.
    realized_pnl: float = 0.0
    open: bool = True

    @property
    def unrealized_pnl(self) -> float:
        return 0.0  # updated at query time with live price

    def to_dict(self):
        d = asdict(self)
        return d


# ---------------------------------------------------------------------------
# JSON persistence layer
# ---------------------------------------------------------------------------

class JSONStore:
    """
    Flat-file persistence. Replace this class with a DB adapter later.
    File structure:
    {
      "positions": { SYMBOL: {...} },
      "orders":    [ {...}, ... ],
      "trades":    [ {...}, ... ],   # closed trade records
      "equity_curve": [ {ts, equity}, ... ]
    }
    """

    def __init__(self, filepath: str = "trades.json"):
        self.path = Path(filepath)
        self._data = self._load()

    def _load(self) -> dict:
        if self.path.exists():
            with open(self.path, "r") as f:
                return json.load(f)
        return {"positions": {}, "orders": [], "trades": [], "equity_curve": []}

    def save(self):
        with open(self.path, "w") as f:
            json.dump(self._data, f, indent=2, default=str)

    # --- positions ---
    def get_position(self, symbol: str) -> Optional[dict]:
        return self._data["positions"].get(symbol)

    def set_position(self, symbol: str, pos: dict):
        self._data["positions"][symbol] = pos
        self.save()

    def close_position(self, symbol: str):
        if symbol in self._data["positions"]:
            self._data["positions"][symbol]["open"] = False
            self.save()

    def all_open_positions(self) -> dict:
        return {k: v for k, v in self._data["positions"].items() if v.get("open")}

    # --- orders ---
    def append_order(self, order: dict):
        self._data["orders"].append(order)
        self.save()

    def all_orders(self) -> list:
        return self._data["orders"]

    # --- closed trades ---
    def append_trade(self, trade: dict):
        self._data["trades"].append(trade)
        self.save()

    def all_trades(self) -> list:
        return self._data["trades"]

    # --- equity curve ---
    def append_equity_point(self, ts: str, equity: float):
        self._data["equity_curve"].append({"ts": ts, "equity": equity})
        self.save()

    def equity_curve(self) -> list:
        return self._data["equity_curve"]


# ---------------------------------------------------------------------------
# Signal processor — parses your event payload
# ---------------------------------------------------------------------------

class SignalProcessor:
    """
    Parses the event dict coming from your signal generator.
    Normalises np.float64 / datetime strings etc.
    """

    VALID_SIGNAL_TYPES = {"buy", "sell", "sl", "tsl", "exit"}

    @staticmethod
    def parse(event: dict) -> list[dict]:
        """
        Returns a list of normalised signal dicts ready for the engine.
        One event can carry multiple signals (as in your payload).
        """
        mode = event.get("mode", "EQUITY")
        unit = event.get("unit", "days")
        interval = event.get("interval", 1)
        raw_signals = event.get("signals", [])

        parsed = []
        for s in raw_signals:
            sig_type = str(s.get("signal_type", "")).lower()
            if sig_type not in SignalProcessor.VALID_SIGNAL_TYPES:
                print(f"[SignalProcessor] Unknown signal_type '{sig_type}' — skipped.")
                continue

            parsed.append({
                "mode": mode,
                "unit": unit,
                "interval": interval,
                "symbol": s["symbol"],
                "close": float(s["close"]),
                "tsl": float(s["tsl"]) if s.get("tsl") is not None else None,
                "timestamp": str(s["timestamp"]),
                "signal_type": sig_type,
            })

        return parsed


# ---------------------------------------------------------------------------
# Paper Trading Engine
# ---------------------------------------------------------------------------

class PaperTradingEngine:
    """
    Core execution engine.
    - On BUY signal  → open a new position
    - On SELL / SL / TSL / EXIT → close existing position, record P&L

    Future real-broker swap: subclass or replace _execute_buy / _execute_sell
    with actual broker API calls.
    """

    DEFAULT_QTY = 1          # default shares per order; make this configurable
    INITIAL_CAPITAL = 100_000.0

    def __init__(self, store: JSONStore = None, qty: int = DEFAULT_QTY):
        self.store = store or JSONStore()
        self.qty = qty
        self._log: list[str] = []

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def process_event(self, event: dict) -> list[dict]:
        """
        Main entry: accepts raw event payload, returns list of execution results.
        """
        signals = SignalProcessor.parse(event)
        results = []
        for signal in signals:
            result = self._route_signal(signal)
            if result:
                results.append(result)
        return results

    # ------------------------------------------------------------------
    # Routing
    # ------------------------------------------------------------------

    def _route_signal(self, signal: dict) -> Optional[dict]:
        st = signal["signal_type"]

        if st == "buy":
            return self._execute_buy(signal)

        elif st in ("sell", "sl", "tsl", "exit"):
            return self._execute_sell(signal)

        return None

    # ------------------------------------------------------------------
    # Buy execution
    # ------------------------------------------------------------------

    def _execute_buy(self, signal: dict) -> dict:
        symbol = signal["symbol"]
        price = signal["close"]
        ts = signal["timestamp"]

        # Avoid double-entry
        existing = self.store.get_position(symbol)
        if existing and existing.get("open"):
            msg = f"[{symbol}] Already have open position — BUY skipped."
            self._log.append(msg)
            print(msg)
            return {"action": "skipped", "reason": "position_exists", "symbol": symbol}

        order = Order(
            order_id=str(uuid.uuid4())[:8],
            symbol=symbol,
            side="BUY",
            qty=self.qty,
            price=price,
            order_type="MARKET",
            status="FILLED",
            timestamp=ts,
            notes=f"Signal: buy | mode: {signal['mode']}",
        )

        position = Position(
            symbol=symbol,
            qty=self.qty,
            avg_price=price,
            entry_time=ts,
            mode=signal["mode"],
        )

        self.store.set_position(symbol, position.to_dict())
        self.store.append_order(order.to_dict())
        self._record_equity(ts)

        msg = f"[{symbol}] BUY {self.qty} @ ₹{price:.2f} | Order {order.order_id}"
        self._log.append(msg)
        print(msg)
        return {"action": "buy", "order": order.to_dict(), "position": position.to_dict()}

    # ------------------------------------------------------------------
    # Sell / SL / TSL execution
    # ------------------------------------------------------------------

    def _execute_sell(self, signal: dict) -> dict:
        symbol = signal["symbol"]
        exit_price = signal["close"]
        ts = signal["timestamp"]
        sig_type = signal["signal_type"]

        position = self.store.get_position(symbol)
        if not position or not position.get("open"):
            msg = f"[{symbol}] No open position to exit — {sig_type.upper()} skipped."
            self._log.append(msg)
            print(msg)
            return {"action": "skipped", "reason": "no_open_position", "symbol": symbol}

        entry_price = position["avg_price"]
        qty = position["qty"]
        pnl = (exit_price - entry_price) * qty
        pnl_pct = ((exit_price - entry_price) / entry_price) * 100

        order_type_map = {"sell": "MARKET", "sl": "SL", "tsl": "TSL", "exit": "MARKET"}

        order = Order(
            order_id=str(uuid.uuid4())[:8],
            symbol=symbol,
            side="SELL",
            qty=qty,
            price=exit_price,
            order_type=order_type_map.get(sig_type, "MARKET"),
            status="FILLED",
            timestamp=ts,
            trigger_price=signal.get("tsl"),
            notes=f"Signal: {sig_type} | TSL: {signal.get('tsl')}",
        )

        trade_record = {
            "trade_id": str(uuid.uuid4())[:8],
            "symbol": symbol,
            "entry_price": entry_price,
            "exit_price": exit_price,
            "qty": qty,
            "pnl": round(pnl, 2),
            "pnl_pct": round(pnl_pct, 2),
            "entry_time": position["entry_time"],
            "exit_time": ts,
            "exit_reason": sig_type,
            "mode": position["mode"],
        }

        self.store.close_position(symbol)
        self.store.append_order(order.to_dict())
        self.store.append_trade(trade_record)
        self._record_equity(ts)

        emoji = "✅" if pnl >= 0 else "❌"
        msg = (
            f"{emoji} [{symbol}] {sig_type.upper()} {qty} @ ₹{exit_price:.2f} | "
            f"Entry ₹{entry_price:.2f} | P&L ₹{pnl:+.2f} ({pnl_pct:+.2f}%)"
        )
        self._log.append(msg)
        print(msg)
        return {"action": sig_type, "order": order.to_dict(), "trade": trade_record}

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _record_equity(self, ts: str):
        trades = self.store.all_trades()
        realized = sum(t["pnl"] for t in trades)
        equity = self.INITIAL_CAPITAL + realized
        self.store.append_equity_point(ts, round(equity, 2))

    def summary(self) -> dict:
        trades = self.store.all_trades()
        if not trades:
            return {"total_trades": 0, "message": "No closed trades yet."}

        wins = [t for t in trades if t["pnl"] > 0]
        losses = [t for t in trades if t["pnl"] <= 0]
        total_pnl = sum(t["pnl"] for t in trades)

        return {
            "total_trades": len(trades),
            "wins": len(wins),
            "losses": len(losses),
            "win_rate_pct": round(len(wins) / len(trades) * 100, 1),
            "total_pnl": round(total_pnl, 2),
            "avg_pnl_per_trade": round(total_pnl / len(trades), 2),
            "best_trade": max(trades, key=lambda t: t["pnl"]),
            "worst_trade": min(trades, key=lambda t: t["pnl"]),
            "open_positions": list(self.store.all_open_positions().keys()),
        }

    def get_log(self) -> list[str]:
        return self._log