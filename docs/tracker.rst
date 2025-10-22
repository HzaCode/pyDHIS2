Tracker
=======

The Tracker endpoint provides access to DHIS2 individual-level data (events and tracked entities).

Fetching Events
---------------

.. code-block:: python

   from pydhis2 import get_client, DHIS2Config
   
   AsyncDHIS2Client, _ = get_client()
   config = DHIS2Config()
   
   async with AsyncDHIS2Client(config) as client:
       events = await client.tracker.events(
           program="programId",
           orgUnit="orgUnitId",
           startDate="2023-01-01",
           endDate="2023-12-31"
       )
       df = events.to_pandas()
       print(df)

Streaming Events
----------------

For large datasets, stream events in pages:

.. code-block:: python

   async for page in client.tracker.stream_events(
       program="programId",
       page_size=1000
   ):
       print(f"Processing {len(page)} events")
       # Process each page

Creating Events
---------------

.. code-block:: python

   event = {
       "program": "programId",
       "orgUnit": "orgUnitId",
       "eventDate": "2023-01-15",
       "status": "COMPLETED",
       "dataValues": [
           {"dataElement": "dataElementId", "value": "100"}
       ]
   }
   
   response = await client.tracker.create_event(event)

Tracked Entities
----------------

Query tracked entities:

.. code-block:: python

   entities = await client.tracker.tracked_entities(
       trackedEntityType="personId",
       orgUnit="orgUnitId"
   )
   df = entities.to_pandas()

