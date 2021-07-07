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
import sys
import uvicorn

from sse_starlette.sse import EventSourceResponse
from starlette.applications import Starlette
from starlette.background import BackgroundTask
from starlette.responses import FileResponse, JSONResponse, RedirectResponse
from starlette.staticfiles import StaticFiles
from threading import Thread

from animalid import generate_animal_id
from data import *

process_id = f"frontend-{unique_id()}"
store = DataStore()
update_queues = set()

## Kafka

producer = kafka.KafkaProducer(bootstrap_servers="localhost:9092")

def consume_updates():
    consumer = kafka.KafkaConsumer("updates",
                                   group_id=process_id,
                                   auto_offset_reset="earliest",
                                   bootstrap_servers="localhost:9092")

    for message in consumer:
        item = DataItem.object(json.loads(message.value))

        if item is None:
            continue

        store.put_item(item)

        for queue in update_queues:
            asyncio.run(queue.put(item))

## HTTP

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

    producer.send("updates", user.json().encode("ascii"))

    return await store.await_item(User, user.id)

@star.route("/api/data")
async def get_data(request):
    queue = asyncio.Queue()

    async def generate():
        update_queues.add(queue)

        for item in store.get_items():
            yield {"data": item.json()}

        while True:
            yield {"data": (await queue.get()).json()}

    async def cleanup():
        update_queues.remove(queue)

    return EventSourceResponse(generate(), background=BackgroundTask(cleanup))

@star.route("/api/send-order", methods=["POST"])
async def send_order(request):
    order = Order(data=await request.json())

    producer.send("orders", order.json().encode("ascii"))

    return JSONResponse({"error": None})

if __name__ == "__main__":
    try:
        port = int(sys.argv[1])
    except KeyError:
        port = 8080

    update_thread = Thread(target=consume_updates, daemon=True)
    update_thread.start()

    uvicorn.run(star, host="0.0.0.0", port=port, log_level="info")