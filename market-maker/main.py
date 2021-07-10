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
import time

from data import *

logging.basicConfig(level=logging.INFO)

process_id = f"market-maker-{unique_id()}"
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

        if item:
            store.put_item(item)

if __name__ == "__main__":
    update_thread = threading.Thread(target=consume_updates, daemon=True)
    update_thread.start()

    while True:
        time.sleep(1)
