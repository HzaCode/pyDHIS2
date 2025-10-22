Metadata
========

The Metadata endpoint provides access to DHIS2 metadata (indicators, data elements, org units, etc.).

Fetching Specific Metadata Types
---------------------------------

.. code-block:: python

   from pydhis2 import get_client, DHIS2Config
   
   AsyncDHIS2Client, _ = get_client()
   config = DHIS2Config()
   
   async with AsyncDHIS2Client(config) as client:
       # Get data elements
       data_elements = await client.metadata.get_data_elements(
           fields="id,name,code,valueType",
           paging=False
       )
       print(data_elements)
       
       # Get indicators
       indicators = await client.metadata.get_indicators(
           fields="id,name,code,numerator,denominator"
       )
       
       # Get organisation units at specific level
       org_units = await client.metadata.get_organisation_units(
           fields="id,name,code,level,path",
           filter={"level": "3"}
       )

Exporting Metadata
------------------

Export metadata to JSON:

.. code-block:: python

   import json
   
   async with AsyncDHIS2Client(config) as client:
       # Export with filters
       metadata = await client.metadata.export(
           fields=":owner",
           filter={"dataElements": "name:like:ANC"}
       )
       
       with open("metadata.json", "w") as f:
           json.dump(metadata, f, indent=2)
       
       # Or use the helper method
       await client.metadata.export_to_file(
           "metadata.json",
           filter={"indicators": "name:like:Malaria"}
       )

Importing Metadata
------------------

Import metadata from JSON:

.. code-block:: python

   import json
   from pydhis2.core.types import ExportFormat
   
   async with AsyncDHIS2Client(config) as client:
       # Direct import
       with open("metadata.json") as f:
           metadata = json.load(f)
       
       summary = await client.metadata.import_(
           metadata,
           strategy="CREATE_AND_UPDATE",
           atomic=True
       )
       print(f"Imported: {summary.imported}")
       print(f"Updated: {summary.updated}")
       
       # Or use the helper method
       summary = await client.metadata.import_from_file("metadata.json")
       
       # Check for errors
       if summary.has_errors:
           conflicts_df = summary.get_conflicts_df()
           print(conflicts_df)

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

