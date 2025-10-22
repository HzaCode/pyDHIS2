Analytics
=========

The Analytics endpoint provides access to DHIS2 aggregated analytics data.

Basic Query
-----------

.. code-block:: python

   from pydhis2 import get_client, DHIS2Config
   from pydhis2.core.types import AnalyticsQuery

   AsyncDHIS2Client, _ = get_client()
   config = DHIS2Config()

   async with AsyncDHIS2Client(config) as client:
       query = AnalyticsQuery(
           dx=["indicator_id"],  # Data dimension
           ou=["org_unit_id"],   # Organisation unit
           pe="2023"             # Period
       )
       df = await client.analytics.to_pandas(query)
       print(df)

Query Parameters
----------------

dx (Data Dimension)
~~~~~~~~~~~~~~~~~~~

Indicators, data elements, or data sets:

.. code-block:: python

   query = AnalyticsQuery(
       dx=["b6mCG9sphIT", "fbfJHSPpUQD"],  # Multiple data elements
       ou="qzGX4XdWufs",
       pe="2023"
   )

ou (Organisation Units)
~~~~~~~~~~~~~~~~~~~~~~~

Specific org units or levels:

.. code-block:: python

   query = AnalyticsQuery(
       dx=["b6mCG9sphIT"],
       ou=["LEVEL-3", "OU_GROUP-abc123"],  # Level or group
       pe="2023"
   )

pe (Periods)
~~~~~~~~~~~~

Various period formats:

.. code-block:: python

   # Single year
   pe="2023"
   
   # Multiple periods
   pe=["2022", "2023"]
   
   # Quarterly
   pe="2023Q1;2023Q2;2023Q3;2023Q4"
   
   # Monthly
   pe="202301;202302;202303"
   
   # Relative periods
   pe="LAST_12_MONTHS"

DataFrame Conversion
--------------------

Convert directly to pandas DataFrame:

.. code-block:: python

   df = await client.analytics.to_pandas(query)
   print(df.columns)
   # ['dx', 'ou', 'pe', 'value']

Export Formats
--------------

Parquet
~~~~~~~

.. code-block:: python

   from pydhis2.core.types import ExportFormat
   
   await client.analytics.export_to_file(
       query,
       "output.parquet",
       format=ExportFormat.PARQUET
   )

CSV
~~~

.. code-block:: python

   from pydhis2.core.types import ExportFormat
   
   await client.analytics.export_to_file(
       query,
       "output.csv",
       format=ExportFormat.CSV
   )

Arrow
~~~~~

.. code-block:: python

   table = await client.analytics.to_arrow(query)
   print(table.schema)

Pagination and Streaming
-------------------------

For large datasets:

.. code-block:: python

   async with AsyncDHIS2Client(config) as client:
       async for page_df in client.analytics.stream_paginated(
           query,
           page_size=1000,
           max_pages=10
       ):
           print(f"Processing {len(page_df)} records")
           # Process each page DataFrame
           # page_df is a pandas DataFrame

Filters
-------

Add filters to your query:

.. code-block:: python

   query = AnalyticsQuery(
       dx=["b6mCG9sphIT"],
       ou="qzGX4XdWufs",
       pe="2023",
       filters={"age": "AGE_0_4", "sex": "FEMALE"}
   )

Advanced Options
----------------

Skip Metadata
~~~~~~~~~~~~~

.. code-block:: python

   query = AnalyticsQuery(
       dx=["b6mCG9sphIT"],
       ou="qzGX4XdWufs",
       pe="2023",
       skip_meta=True  # Don't include metadata
   )

Hierarchy Meta
~~~~~~~~~~~~~~

.. code-block:: python

   query = AnalyticsQuery(
       dx=["b6mCG9sphIT"],
       ou="qzGX4XdWufs",
       pe="2023",
       hierarchy_meta=True  # Include org unit hierarchy
   )

