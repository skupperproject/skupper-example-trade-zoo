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
import logging
import os
import sys
import threading
import time
import traceback
import uvicorn

from sse_starlette.sse import EventSourceResponse
from starlette.applications import Starlette
from starlette.background import BackgroundTask
from starlette.responses import FileResponse, JSONResponse, RedirectResponse
from starlette.staticfiles import StaticFiles

from animalid import generate_animal_id
from data import *

logging.basicConfig(level=logging.INFO)

store = DataStore()
process_id = f"frontend-{unique_id()}"
update_queues = set()

## Kafka

producer = create_producer(process_id)

def process_updates():
    consumer = create_update_consumer(process_id)

    try:
        while True:
            message = consumer.poll(1)

            if message is None:
                continue

            if message.error():
                print(f"{process_id} Consumer error: {message.error()}")
                continue

            try:
                item = DataItem.object(message.value())
            except:
                traceback.print_exc()
                continue

            store.put_item(item)

            for queue in update_queues:
                asyncio.run(queue.put(item))
    finally:
        consumer.close()

## HTTP

http_host = os.environ.get("HTTP_HOST", "0.0.0.0")
http_port = int(os.environ.get("HTTP_PORT", 8080))

star = Starlette(debug=True)
star.mount("/static", StaticFiles(directory="static"), name="static")

@star.route("/")
async def get_index(request):
    user_id = request.query_params.get("user")

    if user_id is None:
        user = await create_user()
        return RedirectResponse(url=f"?user={user.id}")

    user = await store.await_item(User, user_id, timeout=1)

    if user is None:
        user = await create_user()
        return RedirectResponse(url=f"?user={user.id}")

    return FileResponse("static/index.html")

async def create_user():
    user = User()
    user.name = generate_animal_id()

    producer.produce("updates", user.bytes())

    return await store.await_item(User, user.id)

@star.route("/api/data")
async def get_data(request):
    queue = asyncio.Queue()

    async def generate():
        for item in store.get_items():
            if isinstance(item, Order) and item.execution_time is not None:
                continue

            if isinstance(item, (Order, Trade)) and item.deletion_time is not None:
                continue

            yield {"data": item.json()}

        update_queues.add(queue)

        while True:
            yield {"data": (await queue.get()).json()}

    async def cleanup():
        update_queues.remove(queue)

    return EventSourceResponse(generate(), background=BackgroundTask(cleanup))

@star.route("/api/submit-order", methods=["POST"])
async def submit_order(request):
    order = Order(data=await request.json())
    order.creation_time = time.time()

    producer.produce("orders", order.bytes())

    return JSONResponse({"error": None})

@star.route("/api/delete-order", methods=["POST"])
async def delete_order(request):
    order_id = (await request.json())["order"]
    order = store.get_item(Order, order_id)

    if not order:
        return JSONResponse({"error": "not-found"}, 404)

    order.deletion_time = time.time()

    producer.produce("updates", order.bytes())

    return JSONResponse({"error": None})

@star.route("/api/delete-trade", methods=["POST"])
async def delete_trade(request):
    trade_id = (await request.json())["trade"]
    trade = store.get_item(Trade, trade_id)

    if not trade:
        return JSONResponse({"error": "not-found"}, 404)

    trade.deletion_time = time.time()

    producer.produce("updates", trade.bytes())

    return JSONResponse({"error": None})

if __name__ == "__main__":
    update_thread = threading.Thread(target=process_updates, daemon=True)
    update_thread.start()

    try:
        uvicorn.run(star, host=http_host, port=http_port, log_level="info")
    finally:
        producer.flush()
