import queue
import threading
import time
import random


class LiveDataEngine:
    def __init__(self, worker_count=4):
        self.symbols = set()
        self.data_queue = queue.Queue()
        self.command_queue = queue.Queue()

        self.running = False
        self.worker_count = worker_count

        self.stream_thread = None
        self.command_thread = None
        self.worker_threads = []

    def start(self):
        if self.running:
            return

        self.running = True

        # Thread for handling subscribe/unsubscribe commands
        self.command_thread = threading.Thread(
            target=self._command_loop,
            daemon=True
        )
        self.command_thread.start()

        # Thread for fetching / receiving live data
        self.stream_thread = threading.Thread(
            target=self._stream_loop,
            daemon=True
        )
        self.stream_thread.start()

        # Worker threads for processing incoming data
        for i in range(self.worker_count):
            thread = threading.Thread(
                target=self._worker_loop,
                args=(i,),
                daemon=True
            )
            thread.start()
            self.worker_threads.append(thread)

    def subscribe(self, symbol):
        self.command_queue.put(("SUBSCRIBE", symbol.upper()))

    def unsubscribe(self, symbol):
        self.command_queue.put(("UNSUBSCRIBE", symbol.upper()))

    def stop(self):
        self.command_queue.put(("STOP", None))

    def _command_loop(self):
        while self.running:
            command, symbol = self.command_queue.get()

            if command == "STOP":
                self.running = False
                break

            elif command == "SUBSCRIBE":
                if symbol not in self.symbols:
                    self.symbols.add(symbol)
                    print(f"Subscribed: {symbol}")

                    # Real broker/websocket subscribe call goes here
                    # websocket.send({"action": "subscribe", "symbol": symbol})

            elif command == "UNSUBSCRIBE":
                if symbol in self.symbols:
                    self.symbols.remove(symbol)
                    print(f"Unsubscribed: {symbol}")

                    # Real broker/websocket unsubscribe call goes here
                    # websocket.send({"action": "unsubscribe", "symbol": symbol})

    def _stream_loop(self):
        """
        Simulates live market data.
        Replace this with real websocket receiving logic.
        """
        while self.running:
            for symbol in list(self.symbols):
                fake_price = round(random.uniform(100, 500), 2)

                tick = {
                    "symbol": symbol,
                    "price": fake_price,
                    "timestamp": time.time()
                }

                self.data_queue.put(tick)

            time.sleep(1)

    def _worker_loop(self, worker_id):
        while self.running:
            try:
                tick = self.data_queue.get(timeout=1)
            except queue.Empty:
                continue

            self.process_tick(tick, worker_id)
            self.data_queue.task_done()

    def process_tick(self, tick, worker_id):
        """
        Your strategy / processing logic goes here.
        """
        symbol = tick["symbol"]
        price = tick["price"]

        print(f"Worker {worker_id} processing {symbol}: {price}")

        # Example:
        # calculate indicator
        # check signal
        # send order request
        # update database

if __name__ == "__main__":
    engine = LiveDataEngine(worker_count=40)
    engine.start()

    symbols = [
        "AAPL", "MSFT", "GOOG", "TSLA", "NVDA",
        "META", "AMZN", "NFLX", "AMD", "INTC"
    ]

    for symbol in symbols:
        engine.subscribe(symbol)

    time.sleep(10)

    engine.subscribe("IBM")
    engine.subscribe("ORCL")

    time.sleep(10)

    engine.unsubscribe("TSLA")

    time.sleep(10)

    engine.stop()        