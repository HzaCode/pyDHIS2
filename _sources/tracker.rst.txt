Tracker
=======

The Tracker endpoint provides access to DHIS2 individual-level data (events and tracked entities).

Fetching Events as Raw JSON
----------------------------

.. code-block:: python

   from pydhis2 import get_client, DHIS2Config
   
   AsyncDHIS2Client, _ = get_client()
   config = DHIS2Config()
   
   async with AsyncDHIS2Client(config) as client:
       # Get raw JSON response
       events = await client.tracker.events(
           program="programId",
           org_unit="orgUnitId",
           start_date="2023-01-01",
           end_date="2023-12-31",
           page_size=100
       )
       print(events)

Fetching Events as DataFrame
-----------------------------

.. code-block:: python

   # Get events directly as DataFrame
   async with AsyncDHIS2Client(config) as client:
       df = await client.tracker.events_to_pandas(
           program="programId",
           org_unit="orgUnitId",
           status="COMPLETED",
           paging_size=200
       )
       print(df)

Streaming Events
----------------

For large datasets, stream events in pages:

.. code-block:: python

   async with AsyncDHIS2Client(config) as client:
       async for page_df in client.tracker.stream_events(
           program="programId",
           org_unit="orgUnitId",
           page_size=200
       ):
           print(f"Processing {len(page_df)} events")
           # Process each page DataFrame
           # page_df is a pandas DataFrame

Creating Events
---------------

.. code-block:: python

   async with AsyncDHIS2Client(config) as client:
       event = {
           "program": "programId",
           "orgUnit": "orgUnitId",
           "occurredAt": "2023-01-15T10:00:00",
           "status": "COMPLETED",
           "dataValues": [
               {"dataElement": "dataElementId", "value": "100"}
           ]
       }
       
       response = await client.tracker.create_event(event)
       print(response)

Tracked Entities (Raw JSON)
----------------------------

Query tracked entities as raw JSON:

.. code-block:: python

   async with AsyncDHIS2Client(config) as client:
       entities = await client.tracker.tracked_entities(
           tracked_entity_type="personId",
           org_unit="orgUnitId",
           page_size=50
       )
       print(entities)

Tracked Entities (DataFrame)
-----------------------------

Query tracked entities and convert to DataFrame:

.. code-block:: python

   async with AsyncDHIS2Client(config) as client:
       df = await client.tracker.tracked_entities_to_pandas(
           org_unit="orgUnitId",
           program="programId",
           paging_size=200
       )
       print(df)

Export to File
--------------

.. code-block:: python

   from pydhis2.core.types import ExportFormat
   
   async with AsyncDHIS2Client(config) as client:
       # Export events to Parquet
       await client.tracker.export_events_to_file(
           "events.parquet",
           format=ExportFormat.PARQUET,
           program="programId",
           org_unit="orgUnitId"
       )
       
       # Export tracked entities to CSV
       await client.tracker.export_tracked_entities_to_file(
           "entities.csv",
           format=ExportFormat.CSV,
           org_unit="orgUnitId"
       )

