Configuration
=============

pydhis2 can be configured through multiple methods: environment variables, configuration files, or directly in code.

Environment Variables
---------------------

The recommended approach for production:

.. code-block:: bash

   export DHIS2_URL="https://your-dhis2-server.com"
   export DHIS2_USERNAME="your_username"
   export DHIS2_PASSWORD="your_password"

Then use in code:

.. code-block:: python

   from pydhis2 import DHIS2Config
   
   config = DHIS2Config()  # Loads from environment

Direct Configuration
--------------------

For development or scripts:

.. code-block:: python

   from pydhis2 import DHIS2Config
   
   config = DHIS2Config(
       base_url="https://your-server.com",
       auth=("username", "password"),
       rps=10,              # Requests per second
       concurrency=10,      # Concurrent connections
       timeout=60,          # Request timeout
       cache_enabled=True,  # Enable HTTP caching
   )

Advanced Options
----------------

Rate Limiting
~~~~~~~~~~~~~

Control request rates to avoid overwhelming the server:

.. code-block:: python

   config = DHIS2Config(
       base_url="https://your-server.com",
       auth=("username", "password"),
       rps=5,  # 5 requests per second
   )

Retry Configuration
~~~~~~~~~~~~~~~~~~~

Customize retry behavior:

.. code-block:: python

   config = DHIS2Config(
       base_url="https://your-server.com",
       auth=("username", "password"),
       max_retries=5,
       retry_backoff=2.0,
   )

Caching
~~~~~~~

Enable HTTP caching for repeated requests:

.. code-block:: python

   config = DHIS2Config(
       base_url="https://your-server.com",
       auth=("username", "password"),
       cache_enabled=True,
       cache_dir=".cache/dhis2",
   )

Timeouts
~~~~~~~~

Set connection and read timeouts:

.. code-block:: python

   config = DHIS2Config(
       base_url="https://your-server.com",
       auth=("username", "password"),
       timeout=120,  # Total request timeout in seconds
   )

Using Configuration Files
--------------------------

You can also use YAML configuration files:

.. code-block:: yaml

   # config.yml
   connection:
     base_url: "https://your-server.com"
     username: "your_username"
     password: "your_password"
     rps: 10
     concurrency: 10
   
   retry:
     max_attempts: 5
     backoff: 2.0
   
   cache:
     enabled: true
     directory: ".cache"

Load it in code:

.. code-block:: python

   import yaml
   from pydhis2 import DHIS2Config
   
   with open('config.yml') as f:
       config_dict = yaml.safe_load(f)
   
   config = DHIS2Config(**config_dict['connection'])

