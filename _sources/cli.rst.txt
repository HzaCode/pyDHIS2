Command Line Interface
======================

pydhis2 provides a powerful CLI for common data operations.

Installation Verification
--------------------------

Check version:

.. code-block:: bash

   pydhis2 version

Run quick demo:

.. code-block:: bash

   pydhis2 demo quick

Configuration
-------------

Set up DHIS2 connection:

.. code-block:: bash

   pydhis2 config --url "https://your-server.com" --username "user"

Analytics Commands
------------------

Pull Analytics Data
~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   pydhis2 analytics pull \
       --dx "indicator_id" \
       --ou "org_unit_id" \
       --pe "2023Q1:2023Q4" \
       --out analytics.parquet

Query with Multiple Dimensions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   pydhis2 analytics pull \
       --dx "ind1,ind2,ind3" \
       --ou "LEVEL-3" \
       --pe "LAST_12_MONTHS" \
       --format csv \
       --out data.csv

Tracker Commands
----------------

Pull Events
~~~~~~~~~~~

.. code-block:: bash

   pydhis2 tracker events \
       --program "program_id" \
       --status COMPLETED \
       --start-date "2023-01-01" \
       --end-date "2023-12-31" \
       --out events.parquet

Pull Tracked Entities
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   pydhis2 tracker entities \
       --type "person" \
       --ou "org_unit_id" \
       --out entities.parquet

Data Quality Commands
---------------------

Run DQR Analysis
~~~~~~~~~~~~~~~~

.. code-block:: bash

   pydhis2 dqr analyze \
       --input analytics.parquet \
       --html dqr_report.html \
       --json dqr_summary.json

Generate DQR Report
~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   pydhis2 dqr report \
       --input analytics.parquet \
       --output report.html \
       --template custom_template.html

Pipeline Commands
-----------------

Run Analysis Pipeline
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   pydhis2 pipeline run --recipe pipelines/analysis.yml

Validate Pipeline
~~~~~~~~~~~~~~~~~

.. code-block:: bash

   pydhis2 pipeline validate --recipe pipelines/analysis.yml

Project Template
----------------

Create New Project
~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   cookiecutter gh:HzaCode/pyDHIS2 --directory pydhis2/templates

This will prompt you for project details and create a complete project structure.

Help
----

Get help for any command:

.. code-block:: bash

   pydhis2 --help
   pydhis2 analytics --help
   pydhis2 tracker --help

