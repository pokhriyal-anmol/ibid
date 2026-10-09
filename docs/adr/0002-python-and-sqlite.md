# 0002: Python, SQLite and uv

Ibid is a Python library with a command line, storing its index in a single SQLite file (FTS5 for keyword search, a vector extension later). Packages are managed with `uv`.

**Why:** one local file is easy to snapshot and compare byte for byte, and Python has the most local-embedding tooling for Apple silicon (MLX). The parser, graph and eval harness all fit one language.

**Cost:** slower than a compiled core, and a UI needs a separate layer. A chat front end such as LibreChat (MIT) is deferred and would reach Ibid through an MCP server, not by embedding it.

**Rule:** reuse MIT or Apache-licensed parts only after a quick license and maintenance check.
