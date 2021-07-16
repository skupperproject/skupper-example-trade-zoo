#
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
#

import os
import threading
import time
import traceback

from data import *

process_id = f"market-data-{unique_id()}"

store = DataStore()
updated = threading.Event()

def log(message):
    print(f"{process_id}: {message}")

def process_updates():
    consumer = create_update_consumer(process_id)

    try:
        for item in consume_items(consumer):
            store.put(item)

            if not isinstance(item, MarketData):
                updated.set()
    finally:
        consumer.close()

def process_prices():
    while updated.wait():
        update_market_data()
        updated.clear()

def update_market_data():
    log("Updating market data")

    orders = store.get(Order)

    open_bids = [x.price for x in orders
                 if x.action == "buy"
                 and x.execution_time is None
                 and x.deletion_time is None]

    open_asks = [x.price for x in orders
                 if x.action == "sell"
                 and x.execution_time is None
                 and x.deletion_time is None]

    trades = [x.price for x in store.get(Trade) if x.deletion_time is None]

    data = MarketData(id="crackers")

    if open_bids:
        data.bid_price = max(open_bids)

    if open_asks:
        data.ask_price = min(open_asks)

    if trades:
        data.high_price = max(trades)
        data.low_price = min(trades)

    produce_item("updates", data)

    log("Updated market data")

if __name__ == "__main__":
    update_thread = threading.Thread(target=process_updates, daemon=True)
    price_thread = threading.Thread(target=process_prices, daemon=True)

    update_thread.start()
    price_thread.run()
