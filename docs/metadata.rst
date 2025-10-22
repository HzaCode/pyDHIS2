Metadata
========

The Metadata endpoint provides access to DHIS2 metadata (indicators, data elements, org units, etc.).

Fetching Metadata
-----------------

.. code-block:: python

   from pydhis2 import get_client, DHIS2Config
   
   AsyncDHIS2Client, _ = get_client()
   config = DHIS2Config()
   
   async with AsyncDHIS2Client(config) as client:
       # Get all data elements
       data_elements = await client.metadata.get("dataElements")
       print(data_elements)
       
       # Get specific org units
       org_units = await client.metadata.get(
           "organisationUnits",
           filters=["level:eq:3"]
       )

Exporting Metadata
------------------

Export metadata to JSON:

.. code-block:: python

   metadata = await client.metadata.export(
       resource_types=["indicators", "dataElements"],
       filters={"indicators": ["name:like:ANC"]}
   )
   
   with open("metadata.json", "w") as f:
       json.dump(metadata, f, indent=2)

Importing Metadata
------------------

Import metadata from JSON:

.. code-block:: python

   with open("metadata.json") as f:
       metadata = json.load(f)
   
   response = await client.metadata.import_data(metadata)
   print(response)

Common Metadata Types
---------------------

* ``dataElements`` - Data elements
* ``indicators`` - Indicators
* ``organisationUnits`` - Organisation units
* ``dataSets`` - Data sets
* ``programs`` - Programs
* ``programStages`` - Program stages
* ``trackedEntityTypes`` - Tracked entity types
* ``optionSets`` - Option sets

