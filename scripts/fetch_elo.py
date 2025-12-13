#!/usr/bin/env python3
"""
Script to fetch the latest NFL upcoming games data from Neil Paine's Substack.
Automatically finds the current version number and downloads the CSV.
"""

import re
import requests
import pandas as pd
from io import StringIO

def get_chart_version(chart_id, max_version=100):
    """
    Find the latest version of a Datawrapper chart by searching backwards from max_version.

    Args:
        chart_id: The Datawrapper chart ID (e.g., 'adIaC')
        max_version: Maximum version number to check (default 100)

    Returns:
        The version number as a string, or None if not found
    """
    print(f"Searching for latest version of chart {chart_id}...")

    # Search backwards from max_version to find the latest working version
    for v in range(max_version, 0, -1):
        test_url = f"https://datawrapper.dwcdn.net/{chart_id}/{v}/data.csv"
        try:
            test_response = requests.head(test_url, timeout=2)
            if test_response.status_code == 200:
                print(f"Found latest chart version: {v}")
                return str(v)
        except:
            continue

    print(f"Could not find any working version for chart {chart_id}")
    return None

def download_csv(chart_id, version, output_file=None):
    """
    Download the CSV data from Datawrapper.

    Args:
        chart_id: The Datawrapper chart ID
        version: The version number
        output_file: Optional filename to save the CSV (if None, returns DataFrame)

    Returns:
        pandas DataFrame with the data
    """
    csv_url = f"https://datawrapper.dwcdn.net/{chart_id}/{version}/data.csv"
    print(f"Downloading CSV from: {csv_url}")

    try:
        # Use requests to download the CSV content
        response = requests.get(csv_url)
        response.raise_for_status()

        # Parse CSV content with pandas
        df = pd.read_csv(StringIO(response.text))
        print(f"Successfully downloaded data: {len(df)} rows, {len(df.columns)} columns")

        if output_file:
            df.to_csv(output_file, index=False)
            print(f"Saved to: {output_file}")

        return df

    except Exception as e:
        print(f"Error downloading CSV: {e}")
        return None

def main():
    # Configuration
    CHART_ID = "adIaC"  # Upcoming NFL games chart from Neil Paine's Substack
    OUTPUT_FILE = "nfl_upcoming_games.csv"

    print("Fetching NFL upcoming games data from Neil Paine's ELO ratings...")
    print("Source: https://neilpaine.substack.com/p/2025-nfl-power-ratings-and-projections\n")

    # Get the current version number
    version = get_chart_version(CHART_ID)
    
    if version:
        # Download the CSV
        df = download_csv(CHART_ID, version, OUTPUT_FILE)
        
        if df is not None:
            print("\nPreview of data:")
            print(df.head())
            print(f"\nColumns: {list(df.columns)}")
    else:
        print("Failed to fetch data.")

if __name__ == "__main__":
    main()