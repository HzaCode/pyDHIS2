# Methods

## Methodology Overview

This study adheres to the principles of reproducibility in computational science. To ensure the reliability and repeatability of the results, all tests were conducted in a fully documented environment with fixed parameters.

## Statistical Analysis Methods

### Confidence Interval Estimation

-   **Method**: Bootstrap (Efron, 1979).
-   **Samples**: 1,000 bootstrap resamples.
-   **Confidence Level**: 95% (two-sided).
-   **Correction**: Bias-corrected and accelerated (BCa) method.

### Effect Size Calculation

-   **Execution Time**: Cliff's delta (a non-parametric effect size).
-   **Data Integrity**: Cohen's d (a parametric effect size).
-   **Threshold Interpretation**: An effect is considered medium when |δ| > 0.33.

## Quality Control

### Reproducibility Assurance

-   **Random Seed**: Fixed to `20250904` (in accordance with the ISO 80000-2 standard).
-   **Environment Snapshot**: Complete version records of all dependencies.
-   **Configuration Backup**: All test parameters were serialized into JSON format for backup.

### Validation Mechanisms

-   **Baseline Consistency**: The accuracy of the baseline data was re-validated before each run.
-   **Result Verification**: Multi-dimensional validation was performed on the results returned by the clients.
-   **Exception Handling**: Comprehensive capture and logging of all potential errors.

## Data Management

### Output Files

-   `manifest.json`: Records the test environment and dependency versions.
-   `experiment_config.json`: Contains the complete experiment configuration.
-   `raw_experiment_results.csv`: Includes all raw experimental data.
-   `requests_trace.jsonl`: Logs detailed request traces.
-   `comprehensive_comparison_report.md`: The final comprehensive comparison report.

### Data Source

-   **DHIS2 Instance**: `https://play.im.dhis2.org/stable-2-42-1`
-   **API Version**: Auto-detected.
-   **Timestamps**: All time records use the UTC ISO format.

## Ethics and Transparency

This research adheres to the principles of open science; all code, data, and methods are publicly available. The study does not involve human subjects and therefore requires no ethics review. The research data can be made available to other researchers upon reasonable request.
