SHOPGRAPH — LOCAL OLLAMA RECEIPT ACQUISITION PIPELINE
=====================================================

PURPOSE
-------

ShopGraph now supports two independent receipt-acquisition engines:

1. Existing OCR Acquisition Pipeline
   - Tesseract / image variants / OCR comparison / reconstruction.
   - Preserved and still available.

2. Ollama Receipt Acquisition Pipeline
   - Uses a vision-capable model running locally through Ollama.
   - No OpenAI API key.
   - No paid cloud AI provider.
   - No automatic cloud fallback.
   - Receipt images are sent only to the configured local Ollama service.

ARCHITECTURE
------------

Receipt Image
    |
    +--> Existing OCR Acquisition Pipeline
    |        |
    |        +--> ShopGraph raw OCR JSON
    |
    +--> Ollama Receipt Acquisition Pipeline
             |
             +--> ShopGraph-compatible raw receipt JSON

Both paths continue into the existing ShopGraph Data Base Builder.

The Data Base Builder remains responsible for:
- deterministic receipt-item interpretation;
- store/date/store-number handling;
- review and correction;
- skip terms;
- duplicate checks;
- Purchase History writing;
- benchmark behavior.

Ollama acquisition does NOT assign Common Name, Sub-Category, or broad Category.

CAPABILITIES MENU
-----------------

=== ShopGraph Capabilities ===

1. OCR Acquisition Pipeline
2. OCR Acquisition Pipeline - All Images
3. OCR Acquisition Pipeline + Data Base Builder
4. OCR Acquisition Pipeline - All Images + Data Base Builder
5. Ollama Receipt Acquisition Pipeline
6. Ollama Receipt Acquisition Pipeline + Data Base Builder
7. Ollama Receipt Acquisition Pipeline - Test Mode
8. Pipelines
0. Return to Utilities Menu

PIPELINES MENU
--------------

=== ShopGraph Pipelines ===

1. Pipeline Part 1
2. Pipeline Part 1 - Ollama Receipt Acquisition
3. Pipeline Export 1
4. Category Manager Completion
5. Pipeline Export 2
6. Finalize Taxonomy + Budgets
0. Return to Capabilities Menu

Pipeline Part 1 remains the original OCR workflow.

Pipeline Part 1 - Ollama Receipt Acquisition reuses the same:
1. Clean Generated Processing Data
2. Clean Current Receipt Images
3. Import Picture
4. Update Purchase History Copy
5. Ollama Receipt Acquisition Pipeline + Data Base Builder
6. Pipeline Export 1

Only acquisition step 5 differs.

OLLAMA SETUP — MACOS
--------------------

Ollama is a local application/system prerequisite. It is not an API key and is
not added to Python requirements.

1. Install Ollama from the official Ollama distribution for macOS.

2. Start Ollama.

3. In Terminal, verify the service/model installation:

       ollama list

4. ShopGraph's default configured vision model is:

       qwen2.5vl:7b

   Pull it once:

       ollama pull qwen2.5vl:7b

5. Run ShopGraph normally:

       python3 main.py

6. Start with:

       Capabilities
       -> Ollama Receipt Acquisition Pipeline - Test Mode
       -> Run Ollama Receipt Acquisition Only

7. After acquisition-only succeeds, test:

       Run Ollama Receipt Acquisition + Data Base Builder Test Mode

8. Use the live Ollama pipeline only after the test path behaves as expected.

CONFIGURATION
-------------

No API key is used.

Optional environment variable:

    SHOPGRAPH_OLLAMA_MODEL

Default:

    qwen2.5vl:7b

Example:

    export SHOPGRAPH_OLLAMA_MODEL="qwen2.5vl:7b"

Optional environment variable:

    SHOPGRAPH_OLLAMA_BASE_URL

Default:

    http://localhost:11434

Example:

    export SHOPGRAPH_OLLAMA_BASE_URL="http://localhost:11434"

The model name and base URL are centralized in:

    capabilities/OllamaReceiptAcquisitionPipeline/ollama_client.py

LOCAL-ONLY BEHAVIOR
-------------------

The new capability uses Ollama's local HTTP service.

ShopGraph does not:
- require OPENAI_API_KEY;
- call OpenAI;
- call Anthropic;
- call Gemini;
- silently fall back to a cloud AI provider;
- automatically download a large Ollama model.

If Ollama cannot be reached, ShopGraph prints a controlled error and stops the
Ollama acquisition path.

If the configured model is missing, ShopGraph prints the exact command:

    ollama pull <configured-model>

and stops without changing Purchase History.

OUTPUT COMPATIBILITY
--------------------

Ollama output is normalized into the same minimal raw-receipt contract already
accepted by:

    utils/DataBaseBuilder/receipt_loader.py

The required downstream fields remain:

    top-level "text": list
    each usable line:
        line_number: integer
        text: string

Additional compatibility/provenance fields are retained so the JSON remains
human-reviewable.

Ollama output filenames use:

    <receipt-stem>_ollama_raw_ocr.json

and are written to the existing ShopGraph raw OCR directory. This is deliberate:
the existing Data Base Builder discovers `*_raw_ocr.json`, and the filename
metadata parser still recognizes the original date/store/store-number prefix.

The Ollama filename does not overwrite the normal OCR filename.

CLEANUP
-------

Ollama final raw receipt JSON uses the existing raw OCR directory, so the
existing Clean Generated Processing Data utility treats it with the same
lifecycle as current generated OCR output.

The cleanup utility still preserves:
- Purchase History/database data;
- benchmarks;
- receipt source images under current_pic until source cleanup is requested;
- archives;
- prompts;
- configuration.

TEST MODE
---------

=== Ollama Receipt Acquisition Pipeline - Test Mode ===

1. Run Ollama Receipt Acquisition Only
2. Run Ollama Receipt Acquisition + Data Base Builder Test Mode
0. Return to Capabilities Menu

Option 1:
- writes the normalized raw receipt JSON;
- does not open or modify live Purchase History.

Option 2:
- runs Ollama acquisition;
- passes the result to the existing Data Base Builder;
- explicitly uses:
      data/exports/test_shopgraph_purchase_history.xlsx
- preserves the normal Data Base Builder review prompts;
- does not use live Purchase History.

FAILURE BEHAVIOR
----------------

Before Data Base Builder, the Ollama path stops safely if:
- the image is missing or unsupported;
- Ollama is unavailable;
- the configured model is missing;
- Ollama times out;
- Ollama returns an HTTP error;
- Ollama returns invalid JSON;
- no usable receipt lines are produced;
- the normalized raw JSON cannot be written.

There is no automatic OCR fallback. The user can choose the existing OCR path
manually.

BACKWARD COMPATIBILITY
----------------------

The original OCR functions remain unchanged and selectable.

The old capabilities/AIReceiptAcquisitionPipeline package is retained only as a
backward-compatibility alias. Its former cloud implementation is replaced with
aliases that route to the local Ollama implementation. This prevents stale
imports from reintroducing paid/cloud AI behavior.

FILES ADDED
-----------

capabilities/OllamaReceiptAcquisitionPipeline/__init__.py
capabilities/OllamaReceiptAcquisitionPipeline/main_OllamaReceiptAcquisitionPipeline.py
capabilities/OllamaReceiptAcquisitionPipeline/ollama_client.py
capabilities/OllamaReceiptAcquisitionPipeline/receipt_prompt.py
capabilities/OllamaReceiptAcquisitionPipeline/response_parser.py
capabilities/OllamaReceiptAcquisitionPipeline/raw_receipt_writer.py

FILES CHANGED
-------------

capabilities/pipelines.py
utils/utils_main.py
README/README_AI_RECEIPT_ACQUISITION_PIPELINE.txt

Compatibility-only replacements:
capabilities/AIReceiptAcquisitionPipeline/__init__.py
capabilities/AIReceiptAcquisitionPipeline/ai_client.py
capabilities/AIReceiptAcquisitionPipeline/main_AIReceiptAcquisitionPipeline.py
capabilities/AIReceiptAcquisitionPipeline/receipt_prompt.py
capabilities/AIReceiptAcquisitionPipeline/response_parser.py
capabilities/AIReceiptAcquisitionPipeline/raw_receipt_writer.py

DEPENDENCIES
------------

No new Python dependency is required.

The Ollama client uses Python's standard-library urllib modules. Existing
Pillow/pillow-heif support is reused when HEIC/HEIF or TIFF conversion is needed.

RETURNING TO OCR
----------------

Nothing must be uninstalled or reconfigured.

Choose one of the original OCR menu options or:

    Pipelines
    -> Pipeline Part 1

The original OCR engine remains a separate acquisition path.
