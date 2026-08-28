ShopGraph - Clarified Capability Modes Update
=============================================

Capabilities menu:

1. OCR Acquisition Pipeline
   Original behavior: choose ONE image, run OCR Stages 1-7, return.

2. OCR Acquisition Pipeline - All Images
   New: process ALL images in data/current_pic/, then return.

3. OCR Acquisition Pipeline + Data Base Builder
   New: choose ONE image, run Stages 1-7, then continue directly into
   Add Receipt to Purchase History.

4. OCR Acquisition Pipeline - All Images + Data Base Builder
   New: process ALL images, then review each successful result in
   DataBaseBuilder.

The standalone DataBaseBuilder menu remains unchanged.

Filename metadata:
- Auto-detect only if the raw OCR filename starts with:
    MMDDYY_Store_StoreNumber...
    MMDDYYYY_Store_StoreNumber...
- If the pattern/date is invalid or absent, the ORIGINAL manual prompts remain:
    Select receipt type
    Store Number
    Receipt date

Cleanup:
- Clears regeneratable processing data.
- Preserves data/current_pic/, data/benchmarks/, data/pdf_files/,
  data/database/, and data/prompts/.
