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
import threading
import time

from data import *

logging.basicConfig(level=logging.INFO)

process_id = f"market-data-{unique_id()}"
store = DataStore()

bootstrap_servers = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
producer = kafka.KafkaProducer(bootstrap_servers=bootstrap_servers)

def consume_updates():
    consumer = kafka.KafkaConsumer("updates",
                                   group_id=process_id,
                                   auto_offset_reset="earliest",
                                   bootstrap_servers=bootstrap_servers)

    for message in consumer:
        item = DataItem.object(json.loads(message.value))

        if item is None:
            continue

        store.put_item(item)

def update_prices():
    bid_prices = [x.price for x in store.get_items(Order) if x.status == "open" and x.action == "buy"]
    ask_prices = [x.price for x in store.get_items(Order) if x.status == "open" and x.action == "sell"]

    curr = MarketData(id="crackers")

    if bid_prices:
        curr.bid_price = max(bid_prices)

    if ask_prices:
        curr.ask_price = min(ask_prices)

    if curr.bid_price and curr.ask_price:
        midpoint = (curr.bid_price + curr.ask_price) / 2
        curr.spread = round((curr.ask_price - curr.bid_price) / midpoint * 100)

    prev = store.get_item(MarketData, "crackers")

    if not prev or (prev and (curr.bid_price != prev.bid_price or curr.ask_price != prev.ask_price)):
        producer.send("updates", curr.json().encode("ascii"))

        print(f"{process_id}: Updated market prices")

if __name__ == "__main__":
    update_thread = threading.Thread(target=consume_updates, daemon=True)
    update_thread.start()

    while True:
        time.sleep(1)
        update_prices()
