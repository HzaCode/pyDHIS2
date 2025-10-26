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
   from pydhis2.core.types import AnalyticsQuery
   from pydhis2.dqr.metrics import CompletenessMetrics, ConsistencyMetrics, TimelinessMetrics
   
   AsyncDHIS2Client, _ = get_client()
   config = DHIS2Config()
   
   async with AsyncDHIS2Client(config) as client:
       # Fetch analytics data
       query = AnalyticsQuery(dx=["indicator_id"], ou="org_unit_id", pe="2023")
       df = await client.analytics.to_pandas(query)
       
       # Run DQR analysis
       completeness = CompletenessMetrics()
       consistency = ConsistencyMetrics()
       timeliness = TimelinessMetrics()
       
       completeness_results = completeness.calculate(df)
       consistency_results = consistency.calculate(df)
       timeliness_results = timeliness.calculate(df)
       
       for result in completeness_results + consistency_results + timeliness_results:
           print(f"{result.metric_name}: {result.value:.2%} ({result.status})")

Completeness Metrics
--------------------

.. code-block:: python

   from pydhis2.dqr.metrics import CompletenessMetrics
   
   completeness = CompletenessMetrics()
   results = completeness.calculate(df)
   
   for result in results:
       print(f"{result.metric_name}: {result.value:.2%}")
       print(f"Status: {result.status}")
       print(f"Message: {result.message}")
       print(f"Details: {result.details}")

Consistency Metrics
-------------------

.. code-block:: python

   from pydhis2.dqr.metrics import ConsistencyMetrics
   
   consistency = ConsistencyMetrics()
   results = consistency.calculate(df)
   
   for result in results:
       print(f"{result.metric_name}: {result.value:.2%}")
       if result.metric_name == "outlier_detection":
           print(f"Outliers detected: {result.details.get('outlier_count')}")

Timeliness Metrics
------------------

.. code-block:: python

   from pydhis2.dqr.metrics import TimelinessMetrics
   
   timeliness = TimelinessMetrics()
   results = timeliness.calculate(df)
   
   for result in results:
       print(f"{result.metric_name}: {result.value:.2%}")
       print(f"Timely records: {result.details.get('timely_records')}/{result.details.get('total_records')}")

Generating Reports
------------------

Collect All Results
~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   import json
   from pydhis2.dqr.metrics import CompletenessMetrics, ConsistencyMetrics, TimelinessMetrics
   
   # Calculate all metrics
   completeness = CompletenessMetrics()
   consistency = ConsistencyMetrics()
   timeliness = TimelinessMetrics()
   
   all_results = (
       completeness.calculate(df) +
       consistency.calculate(df) +
       timeliness.calculate(df)
   )
   
   # Convert to summary dict
   summary = {
       "metrics": [
           {
               "name": r.metric_name,
               "value": r.value,
               "status": r.status,
               "message": r.message,
               "details": r.details
           }
           for r in all_results
       ]
   }
   
   # Save to JSON
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

