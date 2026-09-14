name: Daily VCP Stock Scan

on:
  schedule:
    - cron: '30 7 * * 1-5'
  workflow_dispatch:

jobs:
  run-vcp-scan:
    runs-on: ubuntu-latest

    steps:
      - name: Check out repository
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.10'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install requests yfinance pandas

      - name: Run VCP Scanner Script
        run: |
          python main.py
