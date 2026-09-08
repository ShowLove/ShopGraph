ShopGraph Ollama Context Window Fix
======================================

Problem
-------
The Ollama receipt request could fail with an error such as:

    request (...) exceeds the available context size (4096 tokens)

Fix
---
This update changes the Ollama request so ShopGraph explicitly requests an
8192-token context window.

Default:
    SHOPGRAPH_OLLAMA_NUM_CTX = 8192

Optional override
-----------------
You can override the context size before launching ShopGraph:

    export SHOPGRAPH_OLLAMA_NUM_CTX=16384

Then run ShopGraph from the same Terminal session.

Files changed
-------------
capabilities/OllamaReceiptAcquisitionPipeline/ollama_client.py

No other ShopGraph behavior is changed.
The original OCR pipeline remains untouched.
The Ollama model remains qwen2.5vl:7b unless separately configured.
