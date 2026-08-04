#!/usr/bin/env node
"use strict";

const fs = require("fs");
const vm = require("vm");
const source = fs.readFileSync("dist/js/file-preview.js", "utf8");

function element(attributes) {
  const values = { ...attributes };
  return {
    getAttribute(name) {
      return values[name] ?? null;
    },
    setAttribute(name, value) {
      values[name] = value;
    },
    get href() {
      return values.href;
    },
    set href(value) {
      values.href = value;
    },
  };
}

function simulate(pathname, protocol, hrefs) {
  const anchors = hrefs.map((href) => element({ href }));
  const stylesheet = element({ href: "/dist/css/screen.css" });
  const document = {
    querySelectorAll(selector) {
      if (selector === "a[href]") return anchors;
      if (selector === 'link[rel="stylesheet"][href]') return [stylesheet];
      if (selector === '[src^="/"]') return [];
      throw new Error(`Unexpected selector: ${selector}`);
    },
  };
  vm.runInNewContext(source, {
    URL,
    document,
    window: { location: { pathname, protocol } },
  });
  return {
    hrefs: anchors.map((anchor) => anchor.href),
    stylesheet: stylesheet.href,
  };
}

const root = simulate("/C:/workspace/akira-l.github.io/index.html", "file:", [
  "research/",
  "research-notes/",
  "#about",
]);
const preview = simulate(
  "/C:/workspace/akira-l.github.io/.preview-site/index.html",
  "file:",
  [
    "research/video-generation-world-models/",
    "/research-notes/teleboost/",
    "https://akira-l.github.io/zh/research/",
  ]
);
const http = simulate("/index.html", "https:", [
  "research/",
  "research-notes/",
]);

const checks = [
  [
    "root Research",
    root.hrefs[0],
    "file:///C:/workspace/akira-l.github.io/.preview-site/research/index.html",
  ],
  [
    "root Research Notes",
    root.hrefs[1],
    "file:///C:/workspace/akira-l.github.io/.preview-site/research-notes/index.html",
  ],
  [
    "preview Path",
    preview.hrefs[0],
    "file:///C:/workspace/akira-l.github.io/.preview-site/research/video-generation-world-models/index.html",
  ],
  [
    "preview Note",
    preview.hrefs[1],
    "file:///C:/workspace/akira-l.github.io/.preview-site/research-notes/teleboost/index.html",
  ],
  [
    "preview Chinese hub",
    preview.hrefs[2],
    "file:///C:/workspace/akira-l.github.io/.preview-site/zh/research/index.html",
  ],
  [
    "preview stylesheet",
    preview.stylesheet,
    "file:///C:/workspace/akira-l.github.io/.preview-site/dist/css/screen.css",
  ],
  ["HTTP Research unchanged", http.hrefs[0], "research/"],
  ["HTTP Research Notes unchanged", http.hrefs[1], "research-notes/"],
];

const failures = checks.filter(([, actual, expected]) => actual !== expected);
if (failures.length) {
  for (const [name, actual, expected] of failures) {
    console.error(`${name}: expected ${expected}, received ${actual}`);
  }
  process.exit(1);
}
console.log(
  "Validated file:// routing into the local review site and unchanged HTTP links."
);
