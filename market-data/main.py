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

import json
import kafka
import logging
import os
import threading
import time
import traceback

from data import *

logging.basicConfig(level=logging.INFO)

store = DataStore()
process_id = f"market-data-{unique_id()}"
producer = create_producer(process_id)

def consume_updates():
    consumer = create_update_consumer(process_id)

    for message in consumer:
        try:
            item = DataItem.object(json.loads(message.value))
        except:
            traceback.print_exc()
            continue

        store.put_item(item)

def update_prices():
    orders = store.get_items(Order)

    open_bids = [x.price for x in orders
                 if x.action == "buy"
                 and x.execution_time is None
                 and x.deletion_time is None]

    open_asks = [x.price for x in orders
                 if x.action == "sell"
                 and x.execution_time is None
                 and x.deletion_time is None]

    trades = [x.price for x in store.get_items(Trade)
              if x.deletion_time is None]

    curr = MarketData(id="crackers")

    if open_bids:
        curr.bid_price = max(open_bids)

    if open_asks:
        curr.ask_price = min(open_asks)

    if trades:
        curr.high_price = max(trades)
        curr.low_price = min(trades)

    prev = store.get_item(MarketData, "crackers")

    if not prev or (prev and (curr.bid_price != prev.bid_price
                              or curr.ask_price != prev.ask_price
                              or curr.high_price != prev.high_price
                              or curr.low_price != prev.low_price)):
        producer.send("updates", curr.json().encode("ascii"))
        print(f"{process_id}: Updated market prices")

if __name__ == "__main__":
    update_thread = threading.Thread(target=consume_updates, daemon=True)
    update_thread.start()

    while True:
        time.sleep(1)
        update_prices()
