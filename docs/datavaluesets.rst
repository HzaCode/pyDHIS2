DataValueSets
=============

The DataValueSets endpoint allows you to read and write individual data values.

Reading Data Values
-------------------

.. code-block:: python

   from pydhis2 import get_client, DHIS2Config
   
   AsyncDHIS2Client, _ = get_client()
   config = DHIS2Config()
   
   async with AsyncDHIS2Client(config) as client:
       data = await client.datavaluesets.get(
           dataSet="dataSetId",
           orgUnit="orgUnitId",
           period="202301"
       )
       df = data.to_pandas()
       print(df)

Writing Data Values
-------------------

.. code-block:: python

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
   
   response = await client.datavaluesets.post(data_values)
   print(response)

Bulk Import
-----------

Import large datasets efficiently:

.. code-block:: python

   import pandas as pd
   
   df = pd.read_csv("data.csv")
   
   async with AsyncDHIS2Client(config) as client:
       await client.datavaluesets.bulk_import(df, chunk_size=1000)

