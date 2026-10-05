ShopGraph - Add Purchase History Latest-Date Sort to Pipelines

CHANGE
Adds the existing Data Base Builder action "Sort Purchase History by Latest Date" to the ShopGraph Pipelines menu as option 3. Existing pipeline options shift down by one; Return to Capabilities Menu becomes option 12.

The implementation reuses the existing sort_purchase_history_by_latest_date() function from utils/DataBaseBuilder/excel/purchase_history.py. No duplicate sorting algorithm is introduced.

FILES CHANGED
- capabilities/pipelines.py

INSTALL
Import/overlay this ZIP at the ShopGraph project root while preserving paths.
