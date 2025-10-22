Data Quality Review (DQR)
=========================

pydhis2 includes built-in Data Quality Review metrics based on WHO standards.

Overview
--------

The DQR module helps you assess data quality across three dimensions:

* **Completeness**: Are all expected data values present?
* **Consistency**: Are the data values reasonable and consistent?
* **Timeliness**: Are the data submitted on time?

Basic Usage
-----------

.. code-block:: python

   from pydhis2 import get_client, DHIS2Config
   from pydhis2.dqr import DQRMetrics
   
   AsyncDHIS2Client, _ = get_client()
   config = DHIS2Config()
   
   async with AsyncDHIS2Client(config) as client:
       # Fetch analytics data
       query = AnalyticsQuery(dx=["..."], ou="...", pe="...")
       df = await client.analytics.to_pandas(query)
       
       # Run DQR analysis
       dqr = DQRMetrics(df)
       results = dqr.assess_all()
       print(results)

Completeness Metrics
--------------------

.. code-block:: python

   dqr = DQRMetrics(df)
   
   # Reporting completeness
   completeness = dqr.reporting_completeness()
   print(f"Completeness: {completeness:.2%}")
   
   # Missing data analysis
   missing = dqr.missing_data_analysis()
   print(missing)

Consistency Metrics
-------------------

.. code-block:: python

   # Outlier detection
   outliers = dqr.detect_outliers(threshold=3.0)
   print(f"Found {len(outliers)} outliers")
   
   # Variance analysis
   variance = dqr.variance_analysis()
   print(variance)

Timeliness Metrics
------------------

.. code-block:: python

   # Submission timeliness
   timeliness = dqr.submission_timeliness()
   print(f"On-time submissions: {timeliness:.2%}")

Generating Reports
------------------

HTML Report
~~~~~~~~~~~

.. code-block:: python

   dqr.generate_report(output="dqr_report.html", format="html")

JSON Summary
~~~~~~~~~~~~

.. code-block:: python

   import json
   
   summary = dqr.summary()
   with open("dqr_summary.json", "w") as f:
       json.dump(summary, f, indent=2)

Configuration
-------------

Customize DQR thresholds in ``configs/dqr.yml``:

.. code-block:: yaml

   completeness:
     thresholds:
       pass: 0.90
       warn: 0.70
   
   consistency:
     thresholds:
       outlier: 3.0
       variance: 0.5
   
   timeliness:
     thresholds:
       pass: 0.80
       max_delay_days: 30

