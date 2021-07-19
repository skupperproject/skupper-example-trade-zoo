/*
 *
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing,
 * software distributed under the License is distributed on an
 * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 * KIND, either express or implied.  See the License for the
 * specific language governing permissions and limitations
 * under the License.
 *
 */

"use strict";

window.addEventListener("load", () => {
    const gesso = new Gesso();
    const dataSource = new EventSource("/api/data");
    const data = new Map();

    data.set("User", new Map());
    data.set("Order", new Map());
    data.set("Trade", new Map());
    data.set("MarketData", new Map());

    function renderUsers() {
        const users = data.get("User");
        const headings = ["ID", "Name", "Pennies", "Crackers"];
        const rows = new Array();

        for (let user of users.values()) {
            if (user.deletion_time !== null) {
                continue;
            }

            rows.push([user.id, user.name, user.pennies, user.crackers]);
        }

        rows.sort((a, b) => (a[2] < b[2]) ? 1 : -1)

        const div = gesso.createDiv(null, "#users");

        if (rows.length) {
            gesso.createTable(div, headings, rows);
        }

        gesso.replaceElement($("#users"), div);
    }

    dataSource.onmessage = event => {
        const item = JSON.parse(event.data);

        data.get(item.class).set(item.id, item);

        switch (item.class) {
        case "User":
            renderUsers();
            break;
        }
    };

    $("#action-form").addEventListener("submit", event => {
        event.preventDefault();

        switch (event.submitter.value) {
        case "delete-users":
            fetch("/api/delete-users", {
                method: "POST",
            }).then(response => response.json());
            break;
        case "delete-orders":
            fetch("/api/delete-orders", {
                method: "POST",
            }).then(response => response.json());
            break;
        case "delete-trades":
            fetch("/api/delete-trades", {
                method: "POST",
            }).then(response => response.json());
            break;
        }
    });
});
