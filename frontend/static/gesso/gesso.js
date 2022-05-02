// Licensed to the Apache Software Foundation (ASF) under one
// or more contributor license agreements.  See the NOTICE file
// distributed with this work for additional information
// regarding copyright ownership.  The ASF licenses this file
// to you under the Apache License, Version 2.0 (the
// "License"); you may not use this file except in compliance
// with the License.  You may obtain a copy of the License at
//
//   http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing,
// software distributed under the License is distributed on an
// "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
// KIND, either express or implied.  See the License for the
// specific language governing permissions and limitations
// under the License.

const $ = document.querySelector.bind(document);
const $$ = document.querySelectorAll.bind(document);

Element.prototype.$ = function () {
  return this.querySelector.apply(this, arguments);
};

Element.prototype.$$ = function () {
  return this.querySelectorAll.apply(this, arguments);
};

URL.prototype.$p = function $p(name, defaultValue) {
    let value = this.searchParams.get(name);

    if (value === null || value === undefined) {
        value = defaultValue;
    }

    return value;
}

const $p = function (name, defaultValue) {
    return new URL(window.location).$p(name, defaultValue);
}

function capitalize(string) {
    return string.charAt(0).toUpperCase() + string.slice(1);
}

function nvl(value, replacement) {
    if (value === null || value === undefined) {
        return replacement;
    } else {
        return value;
    }
}

window.$ = $;
window.$$ = $$;
window.$p = $p;
window.capitalize = capitalize;
window.nvl = nvl;

export function createElement(parent, tag, options) {
    const elem = document.createElement(tag);

    if (parent != null) {
        parent.appendChild(elem);
    }

    if (options != null) {
        if (typeof options === "string" || typeof options === "number") {
            createText(elem, options);
        } else if (typeof options === "object") {
            if (options.hasOwnProperty("text")) {
                let text = options["text"];

                if (text != null) {
                    createText(elem, text);
                }

                delete options["text"];
            }

            for (let key of Object.keys(options)) {
                elem.setAttribute(key, options[key]);
            }
        } else {
            throw `illegal argument: ${options}`;
        }
    }

    return elem;
}

export function createText(parent, text) {
    const node = document.createTextNode(text);

    if (parent != null) {
        parent.appendChild(node);
    }

    return node;
}

function setSelector(elem, selector) {
    if (selector == null) {
        return;
    }

    if (selector.startsWith("#")) {
        elem.setAttribute("id", selector.slice(1));
    } else {
        elem.setAttribute("class", selector);
    }
}

export function createDiv(parent, selector, options) {
    const elem = createElement(parent, "div", options);

    setSelector(elem, selector);

    return elem;
}

export function createSpan(parent, selector, options) {
    const elem = createElement(parent, "span", options);

    setSelector(elem, selector);

    return elem;
}

export function createLink(parent, href, options) {
    const elem = createElement(parent, "a", options);

    if (href != null) {
        elem.setAttribute("href", href);
    }

    return elem;
}

export function createTable(parent, headings, rows, options) {
    const elem = createElement(parent, "table", options);
    const thead = createElement(elem, "thead");
    const tbody = createElement(elem, "tbody");

    if (headings) {
        const tr = createElement(thead, "tr");

        for (const heading of headings) {
            createElement(tr, "th", heading);
        }
    }

    for (const row of rows) {
        const tr = createElement(tbody, "tr");

        for (const cell of row) {
            const td = createElement(tr, "td");

            if (cell instanceof Node) {
                td.appendChild(cell);
            } else {
                createText(td, cell);
            }
        }
    }

    return elem;
}

export function createFieldTable(parent, fields, options) {
    const elem = createElement(parent, "table", options);
    const tbody = createElement(elem, "tbody");

    for (const field of fields) {
        const tr = createElement(tbody, "tr");
        const th = createElement(tr, "th", field[0]);
        const td = createElement(tr, "td");

        if (field[1] instanceof Node) {
            td.appendChild(field[1]);
        } else {
            createText(td, field[1]);
        }
    }

    return elem;
}

export function replaceElement(oldElement, newElement) {
    oldElement.parentNode.replaceChild(newElement, oldElement);
}

export function formatDate(date) {
    return date.toISOString().slice(0, 10);
}

export function formatTime(date) {
    return date.toISOString().slice(11, 16);
}

export function formatDuration(millis, suffixes) {
    if (millis == null) {
        return "-";
    }

    if (suffixes == null) {
        suffixes = [
            " years",
            " weeks",
            " days",
            " hours",
            " minutes",
            " seconds",
            " millis",
        ];
    }

    let prefix = "";

    if (millis < 0) {
        prefix = "-";
    }

    millis = Math.abs(millis);

    const seconds = Math.round(millis / 1000);
    const minutes = Math.round(millis / 60 / 1000);
    const hours = Math.round(millis / 3600 / 1000);
    const days = Math.round(millis / 86400 / 1000);
    const weeks = Math.round(millis / 604800 / 1000);
    const years = Math.round(millis / 31536000 / 1000);

    if (years >= 1)   return `${prefix}${years}${suffixes[0]}`;
    if (weeks >= 1)   return `${prefix}${weeks}${suffixes[1]}`;
    if (days >= 1)    return `${prefix}${days}${suffixes[2]}`;
    if (hours >= 1)   return `${prefix}${hours}${suffixes[3]}`;
    if (minutes >= 1) return `${prefix}${minutes}${suffixes[4]}`;
    if (seconds >= 1) return `${prefix}${seconds}${suffixes[5]}`;
    if (millis == 0) return "0";

    return `${prefix}${Math.round(millis)}${suffixes[6]}`;
}

export function formatDurationBrief(millis) {
    return formatDuration(millis, ["y", "w", "d", "h", "m", "s", "ms"]);
}

export function formatBoolean(value) {
    if (value) return "Yes";
    else return "No";
}

export function getJson(url, handler) {
    console.log("Getting data from", url);

    fetch(url, {
        method: "GET",
        headers: {"Content-Type": "application/json"},
    })
        .then(response => response.json())
        .then(responseData => {
            if (handler) {
                handler(responseData);
            }
        })
        .catch(error => {
            console.log(error);
        });
}

export function postJson(url, requestData, handler) {
    console.log("Posting data to", url);

    fetch(url, {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(requestData),
    })
        .then(response => response.json())
        .then(responseData => {
            if (handler) {
                handler(responseData)
            }
        })
        .catch(error => {
            console.log(error);
        });
}

export class Page {
    constructor(router, path, html) {
        this.router = router;
        this.path = path;

        const parser = new DOMParser();
        const doc = parser.parseFromString(html, "text/html");

        this.body = doc.activeElement;

        this.router.routes[this.path] = this;
    }

    process() {
        this.render();
        this.update();
    }

    render() {
        replaceElement($("body"), this.body);
    }

    update() {
        const key = this.getContentKey();

        this.updateView();

        if (key !== this.router.previousContentKey) {
            this.updateContent();
        }

        this.router.previousContentKey = key;
    }

    getContentKey() {
        return [this.path].join();
    }

    updateView() {
    }

    updateContent() {
    }
}

export class Router {
    constructor() {
        this.routes = {};
        this.page = null;
        this.previousContentKey = null;

        this.addEventListeners();
    }

    addEventListeners() {
        window.addEventListener("popstate", () => {
            this.route(window.location.pathname, false);
        });

        window.addEventListener("load", () => {
            this.route(window.location.pathname, true);
        });

        window.addEventListener("click", event => {
            if (event.target.tagName === "A") {
                event.preventDefault();
                this.navigate(new URL(event.target.href, window.location));
            }
        });
    }

    route(path) {
        this.page = this.routes[path];
        this.page.process();
    }

    navigate(url) {
        console.log(`Navigating to ${url}`);

        if (url.href === window.location.href) {
            return;
        }

        window.history.pushState({}, null, url);
        this.route(url.pathname);
    }
}

// One column: [title string, data key, optional rendering function]
// Rendering function: render(value, item, context) => value
// Context is whatever the user chooses to pass into update()
export class Table {
    constructor(id, columns) {
        this.id = id;
        this.columns = columns;
    }

    update(items, context) {
        const headings = [];
        const rows = [];
        const div = createDiv(null, `#${this.id}`);

        for (const column of this.columns) {
            headings.push(column[0]);
        }

        for (const item of items) {
            const row = [];

            for (const column of this.columns) {
                let value = item[column[1]];

                if (column.length === 3) {
                    value = column[2](value, item, context);
                }

                row.push(value);
            }

            rows.push(row);
        }

        if (rows.length) {
            createTable(div, headings, rows);
        }

        replaceElement($(`#${this.id}`), div);
    }
}

export class Tabs {
    constructor(id) {
        this.id = id;
    }

    update() {
        const container = $(`div#${this.id}`);
        const links = container.$$(`:scope > nav > a`);
        const tabs = container.$$(`:scope > div`);

        console.assert(links.length > 0);
        console.assert(tabs.length > 0);
        console.assert(links.length === tabs.length);

        for (const link of links) {
            const url = new URL(window.location);
            url.searchParams.set(this.id, link.dataset.tab);

            link.setAttribute("href", url.href);
            link.classList.remove("selected");
        }

        for (const tab of tabs) {
            tab.classList.remove("selected");
        }

        const selectedTab = $p(this.id, links[0].dataset.tab);

        container.$(`:scope > nav > a[data-tab='${selectedTab}']`).classList.add("selected");
        container.$(`:scope > div[data-tab='${selectedTab}']`).classList.add("selected");
    }
}
