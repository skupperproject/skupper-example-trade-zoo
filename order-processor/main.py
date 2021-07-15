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
import traceback

from data import *

# logging.basicConfig(level=logging.INFO)

process_id = f"order-processor-{unique_id()}"
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

def consume_orders():
    consumer = create_order_consumer("order-processors")

    for message in consumer:
        try:
            order = Order(data=json.loads(message.value))
        except:
            traceback.print_exc()
            continue

        process_order(order)

def process_order(order):
    print(f"{process_id}: Processing {order}")

    producer.send("updates", order.json().encode("ascii"))

    time.sleep(1)

    buy_order = None
    sell_order = None

    if order.action == "buy":
        buy_order = order
        sell_order = find_matching_sell_order(order)

    if order.action == "sell":
        buy_order = find_matching_buy_order(order)
        sell_order = order

    if buy_order and sell_order:
        execute_trade(buy_order, sell_order)
    else:
        print(f"{process_id}: No match for {order}")

    print(f"{process_id}: Processed {order}")

def find_matching_sell_order(buy_order):
    sell_orders = [x for x in store.get_items(Order)
                   if x.action == "sell"
                   and x.quantity == buy_order.quantity
                   and x.price <= buy_order.price
                   and x.execution_time is None
                   and x.deletion_time is None]

    if sell_orders:
        return sell_orders[0]

def find_matching_buy_order(sell_order):
    buy_orders = [x for x in store.get_items(Order)
                  if x.action == "buy"
                  and x.quantity == sell_order.quantity
                  and x.price >= sell_order.price
                  and x.execution_time is None
                  and x.deletion_time is None]

    if buy_orders:
        return buy_orders[0]

def execute_trade(buy_order, sell_order):
    print(f"{process_id}: Executing trade")

    trade = Trade()
    trade.buyer_id = buy_order.user_id
    trade.seller_id = sell_order.user_id
    trade.quantity = sell_order.quantity
    trade.price = sell_order.price
    trade.creation_time = time.time()

    buy_order.execution_time = trade.creation_time
    sell_order.execution_time = trade.creation_time

    buyer = asyncio.run(store.await_item(User, trade.buyer_id))
    buyer.pennies -= trade.quantity * trade.price
    buyer.crackers += trade.quantity

    seller = asyncio.run(store.await_item(User, trade.seller_id))
    seller.pennies += trade.quantity * trade.price
    seller.crackers -= trade.quantity

    producer.send("updates", trade.json().encode("ascii"))
    producer.send("updates", buy_order.json().encode("ascii"))
    producer.send("updates", sell_order.json().encode("ascii"))
    producer.send("updates", buyer.json().encode("ascii"))
    producer.send("updates", seller.json().encode("ascii"))

    print(f"{process_id}: Executed {trade}")

if __name__ == "__main__":
    update_thread = threading.Thread(target=consume_updates, daemon=True)
    order_thread = threading.Thread(target=consume_orders, daemon=True)

    update_thread.start()
    order_thread.run()
