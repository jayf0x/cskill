#!/usr/bin/env node
// Thin wrapper: locate Python 3, invoke the cskill Python core, forward
// arguments and exit code. No logic lives here.
"use strict";

const { spawnSync } = require("node:child_process");
const path = require("node:path");

const pkgRoot = path.join(__dirname, "..");
const srcDir = path.join(pkgRoot, "src");
const version = require(path.join(pkgRoot, "package.json")).version;

function findPython() {
  for (const candidate of ["python3", "python"]) {
    const probe = spawnSync(candidate, ["-c", "import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)"], { stdio: "ignore" });
    if (probe.status === 0) return candidate;
  }
  return null;
}

const python = findPython();
if (!python) {
  console.error(
    "cskill requires Python 3.9+ but none was found on PATH.\n" +
    "Install it with: brew install python3"
  );
  process.exit(1);
}

const result = spawnSync(python, ["-m", "cskill", ...process.argv.slice(2)], {
  stdio: "inherit",
  env: {
    ...process.env,
    PYTHONPATH: srcDir + (process.env.PYTHONPATH ? path.delimiter + process.env.PYTHONPATH : ""),
    CSKILL_VERSION: version,
  },
});

process.exit(result.status === null ? 1 : result.status);
