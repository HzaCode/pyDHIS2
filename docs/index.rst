pydhis2 Documentation
=====================

.. image:: https://img.shields.io/pypi/v/pydhis2?style=flat&color=blue
   :target: https://pypi.org/project/pydhis2
   :alt: PyPI version

.. image:: https://img.shields.io/pypi/pyversions/pydhis2?style=flat&color=blue
   :target: https://pypi.org/project/pydhis2/
   :alt: Python versions

.. image:: https://img.shields.io/pepy/dt/pydhis2?style=flat&color=blue
   :target: https://pepy.tech/project/pydhis2
   :alt: Downloads

.. image:: https://img.shields.io/badge/tests-passing-brightgreen?style=flat
   :target: https://github.com/HzaCode/pyDHIS2/actions/workflows/ci.yml
   :alt: Tests

.. image:: https://img.shields.io/badge/license-Apache%202.0-green?style=flat
   :target: https://opensource.org/licenses/Apache-2.0
   :alt: License

**pydhis2** is a next-generation Python library for interacting with `DHIS2 <https://www.dhis2.org/>`_, 
the world's largest health information management system. It provides a clean, modern, and efficient API 
for data extraction, analysis, and management, with a strong emphasis on creating reproducible workflows—a 
critical need in scientific research and public health analysis, especially in Low and Middle-Income Country 
(LMIC) contexts.

Features
--------

🚀 **Modern & Asynchronous**
   Built with ``asyncio`` for high-performance, non-blocking I/O, making it ideal for large-scale data operations. 
   A synchronous client is also provided for simplicity in smaller scripts.

📊 **Reproducible by Design**
   From project templates to a powerful CLI, pydhis2 is built to support standardized, shareable, and verifiable 
   data analysis pipelines.

🐼 **Seamless DataFrame Integration**
   Natively convert DHIS2 analytics data into Pandas DataFrames with a single method call (``.to_pandas()``), 
   connecting you instantly to the PyData ecosystem.

🔧 **Powerful Command Line Interface**
   Automate common tasks like data pulling and configuration directly from your terminal.

Quick Start
-----------

Installation
~~~~~~~~~~~~

Install pydhis2 directly from PyPI:

.. code-block:: bash

   pip install pydhis2

Verify Installation
~~~~~~~~~~~~~~~~~~~

Use the built-in CLI to run a quick demo:

.. code-block:: bash

   # Check the installed version
   pydhis2 version

   # Run the quick demo
   pydhis2 demo quick

Basic Usage Example
~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   import asyncio
   import sys
   from pydhis2 import get_client, DHIS2Config
   from pydhis2.core.types import AnalyticsQuery

   # pydhis2 provides both an async and a sync client
   AsyncDHIS2Client, _ = get_client()

   async def main():
       # 1. Configure the connection to a DHIS2 server
       config = DHIS2Config(
           base_url="https://demos.dhis2.org/dq",
           auth=("demo", "District1#")
       )
     
       async with AsyncDHIS2Client(config) as client:
           # 2. Define the query parameters
           query = AnalyticsQuery(
               dx=["b6mCG9sphIT"],   # Data element
               ou="qzGX4XdWufs",     # Org unit
               pe="2023"             # Period
           )

           # 3. Fetch data and convert directly to DataFrame
           df = await client.analytics.to_pandas(query)

           # 4. Analyze and display
           print("✅ Data fetched successfully!")
           print(f"Retrieved {len(df)} records.")
           print(df.head())

   if __name__ == "__main__":
       if sys.platform == 'win32':
           asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
       asyncio.run(main())

Table of Contents
-----------------

.. toctree::
   :maxdepth: 2
   :caption: User Guide

   installation
   quickstart
   configuration
   analytics
   datavaluesets
   tracker
   metadata
   dqr
   cli

.. toctree::
   :maxdepth: 2
   :caption: API Reference

   api/client
   api/endpoints
   api/types
   api/io

.. toctree::
   :maxdepth: 1
   :caption: Developer Guide

   contributing
   changelog

Supported Endpoints
-------------------

+-------------------+------+-------+-----------+------------+-----------+
| Endpoint          | Read | Write | DataFrame | Pagination | Streaming |
+===================+======+=======+===========+============+===========+
| **Analytics**     | ✅   | \-    | ✅        | ✅         | ✅        |
+-------------------+------+-------+-----------+------------+-----------+
| **DataValueSets** | ✅   | ✅    | ✅        | ✅         | ✅        |
+-------------------+------+-------+-----------+------------+-----------+
| **Tracker Events**| ✅   | ✅    | ✅        | ✅         | ✅        |
+-------------------+------+-------+-----------+------------+-----------+
| **Metadata**      | ✅   | ✅    | ✅        | \-         | \-        |
+-------------------+------+-------+-----------+------------+-----------+

Compatibility
-------------

* **Python**: ≥ 3.9
* **DHIS2**: ≥ 2.36
* **Platforms**: Windows, Linux, macOS

Community & Support
-------------------

* 📖 `Documentation <https://pydhis2.readthedocs.io>`_
* 🐛 `GitHub Issues <https://github.com/HzaCode/pyDHIS2/issues>`_
* 💬 `GitHub Discussions <https://github.com/HzaCode/pyDHIS2/discussions>`_
* 📝 `Changelog <https://github.com/HzaCode/pyDHIS2/blob/main/CHANGELOG.md>`_

License
-------

This project is licensed under the **Apache License 2.0**. See the `LICENSE <https://github.com/HzaCode/pyDHIS2/blob/main/LICENSE>`_ file for details.

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

