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

import asyncio as _asyncio
import binascii as _binascii
import collections as _collections
import confluent_kafka as _kafka
import inspect as _inspect
import json as _json
import os as _os
import threading as _threading
import time as _time
import traceback as _traceback
import uuid as _uuid

class DataStore:
    def __init__(self):
        self.data = _collections.defaultdict(dict)
        self.lock = _threading.Lock()

    def put(self, item):
        with self.lock:
            self.data[item.__class__][item.id] = item

    def get(self, cls=None, id=None):
        with self.lock:
            if cls is None:
                items = list()

                for cls in self.data:
                    items.extend(self.data[cls].values())

                return items

            if id is None:
                return list(self.data[cls].values())

            return self.data[cls].get(id)

    def wait(self, cls, id, timeout=None):
        return _asyncio.run(self.wait_async(cls, id, timeout))

    async def wait_async(self, cls, id, timeout=None):
        item = self.get(cls, id)
        start = _time.time()

        while item is None:
            await _asyncio.sleep(0.2)

            item = self.get(cls, id)

            if timeout and _time.time() - start > timeout:
                break

        return item

class DataItem:
    id = None
    creation_time = None
    deletion_time = None

    def __init__(self, data=None, id=None):
        if data is not None:
            for name, default in _item_attributes(self).items():
                setattr(self, name, data.get(name, default))

        if id is not None:
            self.id = id

        if self.id is None:
            self.id = unique_id()
            self.creation_time = _time.time()

    def __repr__(self):
        return f"{self.__class__.__name__}({self.id})"

    def delete(self):
        self.deletion_time = _time.time()

    def data(self):
        attrs = _item_attributes(self)
        attrs["class"] = self.__class__.__name__

        return attrs

    def json(self):
        return _json.dumps(self.data())

    def bytes(self):
        return self.json().encode("utf-8")

    @staticmethod
    def object(bytes):
        data = _json.loads(bytes)
        cls = globals()[data["class"]]

        return cls(data)

def _item_attributes(obj):
    return {k: v for k, v in _inspect.getmembers(obj) if not k.startswith("__") and not _inspect.isroutine(v)}

class User(DataItem):
    name = None
    pennies = 100
    crackers = 10

class Order(DataItem):
    user_id = None
    action = None
    quantity = None
    price = None
    execution_time = None

class Trade(DataItem):
    buyer_id = None
    seller_id = None
    quantity = None
    price = None

class MarketData(DataItem):
    # The ID for this one is always "crackers"
    bid_price = None
    ask_price = None
    high_price = None
    low_price = None

def unique_id():
    uuid_bytes = _uuid.uuid4().bytes
    uuid_bytes = uuid_bytes[-4:]

    return _binascii.hexlify(uuid_bytes).decode("utf-8")

def _kafka_config():
    bootstrap_servers = _os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")

    return {"bootstrap.servers": bootstrap_servers}

def _kafka_consumer_config(group_id):
    config = _kafka_config()
    config["group.id"] = group_id
    config["group.instance.id"] = group_id

    return config

def create_update_consumer(group_id):
    config = _kafka_consumer_config(group_id)
    config["auto.offset.reset"] = "earliest"
    config["enable.auto.commit"] = False

    consumer = _kafka.Consumer(config)
    consumer.subscribe(["updates"])

    return consumer

def create_order_consumer(group_id):
    consumer = _kafka.Consumer(_kafka_consumer_config(group_id))
    consumer.subscribe(["orders"])

    return consumer

def consume_items(consumer):
    while True:
        message = consumer.poll(1)

        if message is None:
            continue

        if message.error():
            print(f"Consumer error: {message.error()}")
            continue

        try:
            yield DataItem.object(message.value())
        except:
            _traceback.print_exc()

_producer = _kafka.Producer(_kafka_config())

def produce_item(topic, item, flush=True):
    _producer.produce(topic, item.bytes())

    if flush:
        _producer.flush()
