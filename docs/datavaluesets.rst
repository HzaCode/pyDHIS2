DataValueSets
=============

The DataValueSets endpoint allows you to read and write individual data values.

Pulling (Reading) Data Values
------------------------------

.. code-block:: python

   from pydhis2 import get_client, DHIS2Config
   
   AsyncDHIS2Client, _ = get_client()
   config = DHIS2Config()
   
   async with AsyncDHIS2Client(config) as client:
       # Pull data values - returns DataFrame directly
       df = await client.datavaluesets.pull(
           data_set="dataSetId",
           org_unit="orgUnitId",
           period="202301"
       )
       print(df)
       
       # Pull with date range
       df = await client.datavaluesets.pull(
           data_set="dataSetId",
           org_unit="orgUnitId",
           start_date="2023-01-01",
           end_date="2023-12-31",
           children=True  # Include child org units
       )

Pushing (Writing) Data Values
------------------------------

.. code-block:: python

   from pydhis2.core.types import ImportConfig, ImportStrategy
   
   async with AsyncDHIS2Client(config) as client:
       # Prepare data values
       data_values = {
           "dataSet": "dataSetId",
           "completeDate": "2023-01-31",
           "period": "202301",
           "orgUnit": "orgUnitId",
           "dataValues": [
               {
                   "dataElement": "dataElementId",
                   "value": "100"
               }
           ]
       }
       
       # Push data
       summary = await client.datavaluesets.push(
           data_values,
           config=ImportConfig(
               strategy=ImportStrategy.CREATE_AND_UPDATE,
               dry_run=False
           )
       )
       
       print(f"Imported: {summary.imported}")
       print(f"Updated: {summary.updated}")
       print(f"Conflicts: {len(summary.conflicts)}")
       
       # Check conflicts
       if summary.has_conflicts:
           conflicts_df = summary.conflicts_df
           print(conflicts_df)

Bulk Import with Chunking
-------------------------

Import large datasets efficiently with automatic chunking:

.. code-block:: python

   import pandas as pd
   from pydhis2.core.types import ImportConfig
   
   async with AsyncDHIS2Client(config) as client:
       # Read DataFrame
       df = pd.read_csv("data.csv")
       
       # Push with automatic chunking
       summary = await client.datavaluesets.push(
           df,
           chunk_size=5000,  # Process 5000 records per chunk
           config=ImportConfig(atomic=False)
       )
       
       print(f"Total imported: {summary.imported}")
       print(f"Total updated: {summary.updated}")

Streaming Large Datasets
-------------------------

For very large datasets, stream in pages:

.. code-block:: python

   async with AsyncDHIS2Client(config) as client:
       async for page_df in client.datavaluesets.pull_paginated(
           data_set="dataSetId",
           org_unit="orgUnitId",
           page_size=5000
       ):
           print(f"Processing {len(page_df)} records")
           # Process each page

Export to File
--------------

.. code-block:: python

   from pydhis2.core.types import ExportFormat
   
   async with AsyncDHIS2Client(config) as client:
       await client.datavaluesets.export_to_file(
           "datavalues.parquet",
           format=ExportFormat.PARQUET,
           data_set="dataSetId",
           org_unit="orgUnitId",
           period="202301"
       )

