Quick Start Guide
=================

This guide will help you get started with pydhis2 in minutes.

Basic Example
-------------

Here's a complete example of fetching analytics data:

.. code-block:: python

   import asyncio
   import sys
   from pydhis2 import get_client, DHIS2Config
   from pydhis2.core.types import AnalyticsQuery

   AsyncDHIS2Client, _ = get_client()

   async def main():
       config = DHIS2Config(
           base_url="https://demos.dhis2.org/dq",
           auth=("demo", "District1#")
       )
     
       async with AsyncDHIS2Client(config) as client:
           query = AnalyticsQuery(
               dx=["b6mCG9sphIT"],
               ou="qzGX4XdWufs",
               pe="2023"
           )
           df = await client.analytics.to_pandas(query)
           print(df.head())

   if __name__ == "__main__":
       if sys.platform == 'win32':
           asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
       asyncio.run(main())

Synchronous Client
------------------

If you prefer synchronous code:

.. code-block:: python

   from pydhis2 import get_client, DHIS2Config
   from pydhis2.core.types import AnalyticsQuery

   _, SyncDHIS2Client = get_client()

   config = DHIS2Config(
       base_url="https://demos.dhis2.org/dq",
       auth=("demo", "District1#")
   )

   with SyncDHIS2Client(config) as client:
       query = AnalyticsQuery(
           dx=["b6mCG9sphIT"],
           ou="qzGX4XdWufs",
           pe="2023"
       )
       df = client.analytics.to_pandas(query)
       print(df.head())

Using Environment Variables
----------------------------

For production, use environment variables:

.. code-block:: bash

   export DHIS2_URL="https://your-server.com"
   export DHIS2_USERNAME="your_username"
   export DHIS2_PASSWORD="your_password"

Then in your code:

.. code-block:: python

   from pydhis2 import get_client, DHIS2Config

   config = DHIS2Config()  # Automatically loads from environment
   AsyncDHIS2Client, _ = get_client()
   
   async with AsyncDHIS2Client(config) as client:
       # Your code here
       pass

Next Steps
----------

* Learn about :doc:`configuration` options
* Explore :doc:`analytics` queries
* See :doc:`cli` commands

