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

import threading
import time

from data import *

process_id = f"order-processor-{unique_id()}"

store = DataStore()

def log(message):
    print(f"{process_id}: {message}")

def process_updates():
    consumer = create_update_consumer(process_id)

    try:
        for item in consume_items(consumer):
            store.put(item)
    finally:
        consumer.close()

def process_orders():
    consumer = create_order_consumer("order-processors")

    try:
        for order in consume_items(consumer):
            process_order(order)
    finally:
        consumer.close()

def process_order(order):
    log(f"Processing {order}")

    produce_item("updates", order)

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

    log(f"Processed {order}")

def find_matching_sell_order(buy_order):
    sell_orders = [x for x in store.get(Order)
                   if x.action == "sell"
                   and x.quantity == buy_order.quantity
                   and x.price <= buy_order.price
                   and x.execution_time is None
                   and x.deletion_time is None]

    if sell_orders:
        return sell_orders[0]

def find_matching_buy_order(sell_order):
    buy_orders = [x for x in store.get(Order)
                  if x.action == "buy"
                  and x.quantity == sell_order.quantity
                  and x.price >= sell_order.price
                  and x.execution_time is None
                  and x.deletion_time is None]

    if buy_orders:
        return buy_orders[0]

def execute_trade(buy_order, sell_order):
    log("Executing trade")

    trade = Trade()
    trade.buyer_id = buy_order.user_id
    trade.seller_id = sell_order.user_id
    trade.quantity = sell_order.quantity
    trade.price = sell_order.price
    trade.creation_time = time.time()

    buy_order.execution_time = trade.creation_time
    sell_order.execution_time = trade.creation_time

    buyer = store.wait(User, trade.buyer_id)
    buyer.pennies -= trade.quantity * trade.price
    buyer.crackers += trade.quantity

    seller = store.wait(User, trade.seller_id)
    seller.pennies += trade.quantity * trade.price
    seller.crackers -= trade.quantity

    produce_item("updates", trade)
    produce_item("updates", buy_order)
    produce_item("updates", sell_order)
    produce_item("updates", buyer)
    produce_item("updates", seller)

    log(f"Executed {trade}")

if __name__ == "__main__":
    update_thread = threading.Thread(target=process_updates, daemon=True)
    order_thread = threading.Thread(target=process_orders, daemon=True)

    update_thread.start()
    order_thread.run()
