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

    const userId = new URLSearchParams(window.location.search).get("user");

    function cap(string) {
        return string.charAt(0).toUpperCase() + string.slice(1);
    }

    function nvl(value, replacement) {
        if (value === null || value === undefined) {
            return replacement;
        }

        return value;
    }

    function renderUser() {
        const users = data.get("User");

        if (users.has(userId)) {
            const user = users.get(userId);

            $("#user").textContent = user.name;
            $("#pennies").textContent = user.pennies;
            $("#crackers").textContent = user.crackers;
        }
    }

    function renderOrders() {
        const orders = data.get("Order");
        const users = data.get("User");
        const headings = ["ID", "User", "Offer", "Price", "Actions"];
        const rows = new Array();

        for (let order of orders.values()) {
            if (order.execution_time !== null || order.deletion_time !== null) {
                continue;
            }

            const user = users.get(order.user_id);
            let userName = "-";

            if (user) {
                userName = user.name;
            }

            let link = "-";

            if (order.user_id == userId) {
                link = gesso.createLink(null, "", {class: "action-link"});
                gesso.createText(link, "Cancel");

                link.addEventListener("click", event => {
                    event.preventDefault();

                    fetch("/api/cancel-order", {
                        method: "POST",
                        headers: {"Content-Type": "application/json"},
                        body: JSON.stringify({order: order.id}),
                    }).then(response => response.json());
                });
            }

            rows.push([order.id, userName, cap(order.action), order.price, link]);
        }

        rows.reverse();

        const div = gesso.createDiv(null, "#orders");

        if (rows.length) {
            gesso.createTable(div, headings, rows);
        }

        gesso.replaceElement($("#orders"), div);
    }

    function renderTrades() {
        const trades = data.get("Trade");
        const users = data.get("User");
        const headings = ["ID", "Buyer", "Seller", "Price"];
        const rows = new Array();

        for (let trade of trades.values()) {
            if (trade.deletion_time !== null) {
                continue;
            }

            const buyer = users.get(trade.buyer_id);
            const seller = users.get(trade.seller_id);

            rows.push([trade.id, buyer.name, seller.name, trade.price]);
        }

        rows.reverse();

        const div = gesso.createDiv(null, "#trades");

        if (rows.length) {
            gesso.createTable(div, headings, rows);
        }

        gesso.replaceElement($("#trades"), div);
    }

    function renderMarketPrices() {
        const market = data.get("MarketData").get("crackers");

        if (market) {
            $("#bid").textContent = nvl(market.bid_price, "-");
            $("#ask").textContent = nvl(market.ask_price, "-");
            $("#low").textContent = nvl(market.low_price, "-");
            $("#high").textContent = nvl(market.high_price, "-");
        }
    }

    dataSource.onmessage = event => {
        const item = JSON.parse(event.data);

        data.get(item.class).set(item.id, item);

        switch (item.class) {
        case "User":
            renderUser();
            break;
        case "Order":
            renderOrders();
            break;
        case "Trade":
            renderTrades();
            break;
        case "MarketData":
            renderMarketPrices();
            break;
        }
    };

    $("#order-form").addEventListener("submit", event => {
        event.preventDefault();

        const data = {
            "user_id": userId,
            "action": event.submitter.value,
            "quantity": 1,
            "price": parseInt(event.target.price.value),
        }

        fetch("/api/submit-order", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify(data),
        }).then(response => response.json());
    });

    $("#admin-link").addEventListener("click", event => {
        const password = prompt("Password");

        if (password === null) {
            event.preventDefault();
            return;
        }

        if (password == "animal") {
            event.preventDefault();
            window.location.href = "/admin?user=animal";
            return;
        }
    });
});
