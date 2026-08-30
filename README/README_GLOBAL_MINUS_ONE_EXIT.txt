ShopGraph - Global -1 Exit Option
=================================

PURPOSE
-------
Every interactive input prompt in ShopGraph now accepts:

    -1

to exit the ENTIRE ShopGraph program immediately.

This applies globally, including:
- Main menu
- Utilities menus
- Capability menus
- OCR sub-task prompts
- Data Base Builder prompts
- receipt selection/review prompts
- confirmation prompts
- text/date/store/tax/category inputs
- Code Update Importer prompts
- other prompts that use Python input()

Each prompt automatically displays:

    [-1 = Exit ShopGraph]

Existing 0 / Cancel / Return behavior is unchanged.

IMPLEMENTATION
--------------
A small central input wrapper is installed when ShopGraph starts. This avoids
duplicating exit logic throughout the codebase and ensures future prompts that
use input() automatically inherit the -1 behavior.

FILES
-----
NEW:
    utils/program_exit.py

UPDATED:
    main.py

DEPENDENCIES
------------
No new dependency is required.

INSTALL
-------
Install with ShopGraph's existing Import Code Update ZIP utility, then restart
ShopGraph so the new startup behavior is loaded.
