"use strict";

// All displayed search content is inserted as text, never interpreted as HTML.
for (const input of document.querySelectorAll("[data-filter]")) {
  const list = document.getElementById(input.dataset.filter);
  const counter = document.querySelector(`[data-filter-count="${input.dataset.filter}"]`);
  if (!list) continue;
  const items = [...list.children];
  const filter = () => {
    const words = input.value.toLocaleLowerCase().trim().split(/\s+/).filter(Boolean);
    let visible = 0;
    for (const item of items) {
      const text = item.dataset.filterText || item.textContent.toLocaleLowerCase();
      item.hidden = !words.every(word => text.includes(word));
      if (!item.hidden) visible++;
    }
    if (counter) counter.textContent = `${visible} of ${items.length} shown`;
  };
  input.addEventListener("input", filter);
  filter();
}

for (const link of document.querySelectorAll(".node-jump")) {
  link.addEventListener("click", () => {
    const input = document.getElementById("node-filter");
    if (input) { input.value = ""; input.dispatchEvent(new Event("input")); }
  });
}

// Deep-linked claim records must not be hidden inside a collapsed disclosure.
const revealHash = () => {
  const id = decodeURIComponent(location.hash.slice(1));
  const target = document.getElementById(id);
  if (!target) return;
  for (let item = target; item; item = item.parentElement) {
    if (item.tagName === "DETAILS") item.open = true;
  }
};
addEventListener("hashchange", revealHash);
revealHash();

const nodeSelect = document.getElementById("process-node");
if (nodeSelect) {
  const view = document.getElementById("route-view");
  const status = document.getElementById("route-status");
  const base = document.body.dataset.base;
  fetch(base + "assets/process-index.json").then(response => {
    if (!response.ok) throw new Error("Process index unavailable");
    return response.json();
  }).then(data => {
    const nodes = new Map(data.nodes.map(node => [node.node_id,node]));
    const element = (tag,text,className) => {
      const el = document.createElement(tag); el.textContent = text;
      if (className) el.className = className;
      return el;
    };
    const render = () => {
      const node = nodes.get(nodeSelect.value);
      if (!node) return;
      view.replaceChildren();
      const current = element("div","","route-current");
      current.append(element("span","SELECTED NODE","eyebrow"),element("h2",node.label));
      const source = element("a","Read its controlling module →"); source.href = node.url;
      current.append(source); view.append(current);
      const outgoing = data.edges.filter(edge => edge.from_node === node.node_id);
      const choices = element("div","","route-choices");
      for (const edge of outgoing) {
        const destination = nodes.get(edge.to_node);
        if (!destination) continue;
        const card = element("article","","route-choice");
        card.append(element("span",edge.relationship.replaceAll("_"," "),"eyebrow"),element("p",edge.condition || "No additional condition recorded"));
        const button = element("button",destination.label + " →"); button.type = "button";
        button.addEventListener("click",() => { nodeSelect.value=destination.node_id; render(); });
        card.append(button);
        const refs = element("p","Claims: ","quiet");
        for (const claim of edge.claims) {
          const link = element("a",claim.id); link.href=claim.url;
          refs.append(link,document.createTextNode(" "));
        }
        card.append(refs); choices.append(card);
      }
      if (!outgoing.length) choices.append(element("p","No outgoing relationship is recorded for this node. This is not a conclusion that no other remedy or review exists."));
      view.append(choices);
      status.textContent = `${outgoing.length} recorded outgoing relationships. Check each condition and its source; no outcome is automatic.`;
      const url = new URL(location.href); url.searchParams.set("node",node.node_id); history.replaceState(null,"",url);
    };
    const requested = new URL(location.href).searchParams.get("node");
    if (nodes.has(requested)) nodeSelect.value=requested;
    nodeSelect.addEventListener("change",render); render();
  }).catch(() => { status.textContent="The focused explorer is unavailable. Use the complete relationship register below."; });
}

const form = document.getElementById("search-form");
if (form) {
  const input = document.getElementById("query");
  const results = document.getElementById("search-results");
  const status = document.getElementById("search-status");
  const base = document.body.dataset.base;
  let data;
  let request = 0;
  const search = async () => {
    const current = ++request;
    const query = input.value.trim();
    results.replaceChildren();
    if (!query) { status.textContent = "Enter a term to search the local reference index."; return; }
    status.textContent = "Loading local search index…";
    try {
      if (!data) {
        const response = await fetch(base + "assets/search-index.json");
        if (!response.ok) throw new Error("Index could not be loaded");
        data = await response.json();
      }
      if (current !== request) return;
      const tokens = query.toLocaleLowerCase().split(/\s+/);
      const matches = data.map(row => {
        const title = row.title.toLocaleLowerCase();
        const haystack = (row.title + " " + row.text).toLocaleLowerCase();
        if (!tokens.every(token => haystack.includes(token))) return null;
        return {row, score: tokens.reduce((score,token) => score + (title.includes(token) ? 10 : 1),0)};
      }).filter(Boolean).sort((a,b) => b.score-a.score || a.row.title.localeCompare(b.row.title));
      status.textContent = `${matches.length} matching records${matches.length > 100 ? "; showing the first 100. Refine your search for more specific results." : "."}`;
      for (const {row} of matches.slice(0,100)) {
        if (!row.url.startsWith(base)) continue;
        const item = document.createElement("li");
        const link = document.createElement("a");
        link.href = row.url;
        link.textContent = row.title;
        const meta = document.createElement("span");
        meta.textContent = `${row.kind} · ${row.status} · recorded date ${row.last_verified}`;
        const snippet = document.createElement("p");
        snippet.textContent = row.text.replace(/\s+/g," ").slice(0,230) + "…";
        item.append(link,meta,snippet); results.append(item);
      }
      const url = new URL(location.href); url.searchParams.set("q",query);
      history.replaceState(null,"",url);
    } catch (error) {
      if (current === request) status.textContent = "Search is unavailable. Use the module, authority, and court directories; no content has been removed.";
    }
  };
  form.addEventListener("submit", event => { event.preventDefault(); search(); });
  input.value = new URL(location.href).searchParams.get("q") || "";
  if (input.value) search();
}
