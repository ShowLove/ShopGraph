ShopGraph - Code Update ZIP Importer
======================================

PURPOSE
-------
Adds a ShopGraph utility that installs project-overlay ZIP updates generated for ShopGraph.

Menu:
    Main -> Utilities -> Utilities -> 7. Import Code Update ZIP

Submenu:
    1. Import Update ZIP
    2. Change Default Import Location
    0. Return to Utilities

PROJECT ROOT
------------
The ShopGraph codebase path is never hardcoded. It is derived every run from
utils/code_update_importer.py using Path(__file__).resolve().parents[1].

IMPORT LOCATION
---------------
Default: ~/Downloads
Saved in: utils/config.txt

On first use, ~/Downloads is checked. If it exists, it is saved automatically.
If it does not exist, the user is prompted for a valid folder. If a configured
folder later becomes unavailable, the user is prompted for a replacement.

The submenu option "Change Default Import Location" updates this value.

IMPORT FLOW
-----------
The importer lists ZIP files in the configured folder, newest first, and prompts
which ZIP to use. The user can also choose another folder for that one import.

It supports the ShopGraph overlay ZIP formats used by generated updates:
    utils/...
    README/...

or a single wrapper folder containing those project-relative paths.

Before applying an update it displays every file that will be added/replaced and
asks for confirmation. Files absent from the ZIP are not deleted.

DATA SAFETY
-----------
- Rejects path traversal and absolute/drive-style paths.
- Validates ZIP integrity.
- Protects local utils/config.txt from update ZIPs.
- Stages files before installation.
- Uses temporary rollback copies for touched existing files.
- Rolls back touched files if an installation write fails.
- Creates no permanent backup folder.

After success, restart ShopGraph so replaced Python modules are reloaded.

DEPENDENCIES
------------
No new pip package is required. Standard library only.

FILES
-----
NEW:     utils/code_update_importer.py
UPDATED: utils/utils_main.py
NEW:     README/README_CODE_UPDATE_IMPORTER.txt
RUNTIME: utils/config.txt (created automatically; not shipped in this ZIP)
