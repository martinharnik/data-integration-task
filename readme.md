# Cryptocurrency Data Integration Task

This project fetches cryptocurrency data from the CoinGecko API, enhances it with additional information from OpenAI, stores it in an SQLite database, and uploads the aggregated data to Google Sheets.

## Features

1. **Fetch Cryptocurrency Prices**: Retrieves the latest prices and 24-hour changes for a list of cryptocurrencies from the CoinGecko API.
2. **Enhance Data with OpenAI**: Uses OpenAI to provide a description and category for each cryptocurrency.
3. **Store Data in SQLite**: Saves the fetched and enhanced data in an SQLite database.
4. **Aggregate Data**: Aggregates the data by category and calculates average prices and changes.
5. **Upload to Google Sheets**: Uploads both the aggregated data and detailed coin data to Google Sheets.
6. **Format Google Sheets**: Applies formatting to the uploaded data in Google Sheets for better readability.

## Setup

1. **Environment Variables**: Create a `.env` file in the `env` directory with the following variables:
    ```
    OPENAI_API_KEY=your_openai_api_key
    ```

2. **Service Account File**: Place your Google Cloud service account JSON file in the `env` directory and update the `SERVICE_ACCOUNT_FILE` constant in the code.

3. **Install Dependencies**: Install the required Python packages using pip:
    ```bash
    pip install -r requirements.txt
    ```

## Usage

1. **Run the Script**: Execute the main script to fetch, enhance, store, aggregate, and upload the data:
    ```bash
    python main.py
    ```

2. **Check Google Sheets**: Verify the uploaded data in your specified Google Sheets.

## Code Overview

- **Fetch Cryptocurrency Prices**: The `fetch_crypto_prices` function retrieves data from the CoinGecko API.
- **Enhance Data with OpenAI**: The OpenAI API is used to get descriptions and categories for each cryptocurrency.
- **Store Data in SQLite**: The `initialize_db` and `insert_new_data` functions handle database initialization and data insertion.
- **Aggregate Data**: The `aggregate_by_category` function aggregates the data by category.
- **Upload to Google Sheets**: The `upload_to_google_sheets` function uploads the data to Google Sheets.
- **Format Google Sheets**: The `format_google_sheets` function applies formatting to the Google Sheets.