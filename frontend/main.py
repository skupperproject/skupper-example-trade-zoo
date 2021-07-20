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
import os
import threading
import time
import uvicorn

from sse_starlette.sse import EventSourceResponse
from starlette.applications import Starlette
from starlette.background import BackgroundTask
from starlette.responses import Response, FileResponse, JSONResponse, RedirectResponse
from starlette.staticfiles import StaticFiles

from animalid import generate_animal_id
from data import *

process_id = f"frontend-{unique_id()}"

store = DataStore()
data_request_queues = set()

def log(message):
    print(f"{process_id}: {message}")

## Kafka

def process_updates():
    consumer = create_update_consumer(process_id)

    try:
        for item in consume_items(consumer):
            store.put(item)

            for queue in data_request_queues:
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

    user = await store.wait_async(User, user_id, timeout=1)

    if user is None:
        user = await create_user()
        return RedirectResponse(url=f"?user={user.id}")

    return FileResponse("static/index.html")

@star.route("/admin")
async def get_admin(request):
    user_id = request.query_params.get("user")

    if user_id != "animal":
        return Response("Forbidden", 403)

    return FileResponse("static/admin.html")

async def create_user():
    log("Creating user")

    user = User()
    user.name = generate_animal_id()
    user.creation_time = time.time()

    produce_item("updates", user)

    user = await store.wait_async(User, user.id)

    log(f"Created {user}")

    return user

@star.route("/api/data")
async def get_data(request):
    queue = asyncio.Queue()

    async def generate():
        for item in store.get():
            if isinstance(item, Order) and item.execution_time is not None:
                continue

            if item.deletion_time is not None:
                continue

            yield {"data": item.json()}

        data_request_queues.add(queue)

        while True:
            yield {"data": (await queue.get()).json()}

    async def cleanup():
        data_request_queues.remove(queue)

    return EventSourceResponse(generate(), background=BackgroundTask(cleanup))

@star.route("/api/submit-order", methods=["POST"])
async def submit_order(request):
    log("Submitting order")

    order = Order(data=await request.json())
    produce_item("orders", order)

    log(f"Submitted {order}")

    return JSONResponse({"error": None})

@star.route("/api/cancel-order", methods=["POST"])
async def delete_order(request):
    order_id = (await request.json())["order"]
    order = store.get(Order, order_id)

    if not order:
        return JSONResponse({"error": "not-found"}, 404)

    order.delete()
    produce_item("updates", order)

    return JSONResponse({"error": None})

@star.route("/api/delete-users", methods=["POST"])
async def delete_users(request):
    for user in store.get(User):
        user.delete()
        produce_item("updates", user, flush=False)

    return JSONResponse({"error": None})

@star.route("/api/delete-orders", methods=["POST"])
async def delete_orders(request):
    for order in store.get(Order):
        order.delete()
        produce_item("updates", order, flush=False)

    return JSONResponse({"error": None})

@star.route("/api/delete-trades", methods=["POST"])
async def delete_trades(request):
    for trade in store.get(Trade):
        trade.delete()
        produce_item("updates", trade, flush=False)

    return JSONResponse({"error": None})

if __name__ == "__main__":
    update_thread = threading.Thread(target=process_updates, daemon=True)
    update_thread.start()

    uvicorn.run(star, host=http_host, port=http_port, log_level="info")
