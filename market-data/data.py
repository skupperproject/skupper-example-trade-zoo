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
import logging as _logging
import os as _os
import threading as _threading
import time as _time
import traceback as _traceback
import uuid as _uuid

_log = _logging.getLogger("data")

class DataItem:
    def __init__(self, data=None, id=None):
        if data is not None:
            for name, default in _item_attributes(self).items():
                setattr(self, name, data.get(name, default))

        if id is not None:
            self.id = id

        if self.id is None:
            self.id = unique_id()

    def __repr__(self):
        return f"{self.__class__.__name__}({self.id})"

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

class DataStore:
    def __init__(self):
        self.data = _collections.defaultdict(dict)
        self.lock = _threading.Lock()

    def put_item(self, item):
        with self.lock:
            self.data[item.__class__][item.id] = item

    def get_item(self, cls, id):
        with self.lock:
            return self.data[cls].get(id)

    def get_items(self, cls=None):
        with self.lock:
            if cls is not None:
                return list(self.data[cls].values())
            else:
                items = list()

                for cls in self.data:
                    items.extend(self.data[cls].values())

                return items

    async def await_item(self, cls, id, timeout=None):
        item = self.get_item(cls, id)
        start = _time.time()

        while item is None:
            await _asyncio.sleep(0.2)

            item = self.get_item(cls, id)

            if timeout and _time.time() - start > timeout:
                break

        return item

class User(DataItem):
    id = None
    name = None
    pennies = 100
    crackers = 10

class Order(DataItem):
    id = None
    user_id = None
    action = None
    quantity = None
    price = None
    creation_time = None
    execution_time = None
    deletion_time = None

class Trade(DataItem):
    id = None
    buyer_id = None
    seller_id = None
    quantity = None
    price = None
    creation_time = None
    deletion_time = None

class MarketData(DataItem):
    # The ID for this one is always "crackers"
    id = None
    bid_price = None
    ask_price = None
    high_price = None
    low_price = None

def unique_id():
    uuid_bytes = _uuid.uuid4().bytes
    uuid_bytes = uuid_bytes[-4:]

    return _binascii.hexlify(uuid_bytes).decode("utf-8")

def create_producer(process_id):
    bootstrap_servers = _os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")

    config = {
        "bootstrap.servers": bootstrap_servers,
        "connections.max.idle.ms": 10_000,
        "socket.timeout.ms": 10_000,
        "metadata.max.age.ms": 10_000,
        "api.version.request": False,
    }

    return _kafka.Producer(config)

def create_update_consumer(group_id):
    bootstrap_servers = _os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")

    config = {
        "bootstrap.servers": bootstrap_servers,
        "group.id": group_id,
        "auto.offset.reset": "earliest",
        "enable.auto.commit": False,
        "connections.max.idle.ms": 10_000,
        "socket.timeout.ms": 10_000,
        "metadata.max.age.ms": 10_000,
        "api.version.request": False,
    }

    consumer = _kafka.Consumer(config)
    consumer.subscribe(["updates"])

    return consumer

def create_order_consumer(group_id):
    bootstrap_servers = _os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")

    config = {
        "bootstrap.servers": bootstrap_servers,
        "group.id": group_id,
    }

    consumer = _kafka.Consumer(config)
    consumer.subscribe(["orders"])

    return consumer
