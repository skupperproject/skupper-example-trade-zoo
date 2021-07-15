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

import asyncio
import json
import kafka
import logging
import os
import sys
import threading
import traceback
import time

from data import *

logging.basicConfig(level=logging.INFO)

process_id = f"market-maker-{unique_id()}"
store = DataStore()

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

def process_orders(user):
    market_data = store.get_item(MarketData, "crackers")

    if not market_data:
        return

    if market_data.ask_price is None or market_data.bid_price is None:
        return

    if market_data.ask_price - market_data.bid_price > 2:
        return

    now = time.time()
    orders = store.get_items(Order)

    buy_orders = [x for x in orders
                  if x.action == "buy"
                  and x.user_id != user.id
                  and x.quantity == 1
                  and x.price == market_data.bid_price
                  and now - x.creation_time > 10
                  and x.execution_time is None
                  and x.deletion_time is None]

    sell_orders = [x for x in orders
                   if x.action == "sell"
                   and x.user_id != user.id
                   and x.quantity == 1
                   and x.price == market_data.ask_price
                   and now - x.creation_time > 10
                   and x.execution_time is None
                   and x.deletion_time is None]

    for buy_order, sell_order in zip(buy_orders, sell_orders):
        sell = Order()
        sell.user_id = user.id
        sell.action = "sell"
        sell.quantity = buy_order.quantity
        sell.price = buy_order.price
        sell.creation_time = time.time()

        buy = Order()
        buy.user_id = user.id
        buy.action = "buy"
        buy.quantity = sell_order.quantity
        buy.price = sell_order.price
        buy.creation_time = time.time()

        producer.send("orders", sell.json().encode("ascii"))
        producer.send("orders", buy.json().encode("ascii"))

        print(f"{process_id}: Made a deal!")

if __name__ == "__main__":
    update_thread = threading.Thread(target=consume_updates, daemon=True)
    update_thread.start()

    user = User(id="market-maker")
    user.name = "market-maker"

    producer.send("updates", user.json().encode("ascii"))
    asyncio.run(store.await_item(User, user.id))

    while True:
        time.sleep(1)
        process_orders(user)
