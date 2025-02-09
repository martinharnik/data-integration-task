import os
import json
import sqlite3
import requests
import pandas as pd
import gspread
from dotenv import load_dotenv
from openai import OpenAI
from datetime import timedelta
from google.oauth2.service_account import Credentials

# Constants
DB_FILE = "crypto_data.db"
COINGECKO_API_URL = "https://api.coingecko.com/api/v3/simple/price"
COINS = "near,bitcoin,dogecoin,litecoin,ethereum,solana,cardano,polkadot,binancecoin,chainlink,tron"
SERVICE_ACCOUNT_FILE = "env/crypto-449410-097b70c23503.json"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

# Load environment variables and authenticate
load_dotenv(dotenv_path="env/.env")
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
gcp_client = gspread.authorize(creds)

##### COINGECKO #####

# Fetch cryptocurrency prices from CoinGecko
def fetch_crypto_prices():
    params = {"ids": COINS, "vs_currencies": "usd", "include_24hr_change": "true", "include_last_updated_at": "true"}
    response = requests.get(COINGECKO_API_URL, params=params)
    return response.json()

data = fetch_crypto_prices()

##### OPENAI #####

# Prepare the prompt for OpenAI API
coin_names = ", ".join(data.keys())
prompt = (
    f"Provide a one-sentence description and the category (choose only from Proof of work or Proof of stake) for each of the following cryptocurrencies: {coin_names}."
    "Return only a valid JSON object, without any markdown formatting, code blocks, or additional text. Each key should be the coin name, and values should contain 'description' and 'category'."
    "Ensure the response is properly formatted as a plain JSON object with no extra characters."
)

# Get additional data from OpenAI
completion = client.chat.completions.create(
    model="gpt-4o-mini",
    max_tokens=575,
    messages=[
        {"role": "system", "content": "You are a helpful assistant providing cryptocurrency descriptions and categories."},
        {"role": "user", "content": prompt}
    ]
)

# Parse the response
raw_response = completion.choices[0].message.content
additional_data = json.loads(raw_response)

# Enhance the response with additional data
for coin in data:
    data[coin]["description"] = additional_data.get(coin, {}).get("description", "N/A")
    data[coin]["category"] = additional_data.get(coin, {}).get("category", "N/A")

##### SQLITE #####

# Function to initialize the SQLite database with history tracking
def initialize_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS crypto_prices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            coin_name TEXT,
            usd_price REAL,
            usd_24h_change REAL,
            last_updated_at INTEGER,
            last_updated_dt TEXT,
            description TEXT,
            category TEXT
        )
    ''')
    conn.commit()
    conn.close()

# Initialize database
initialize_db()

# Function to insert new data (without updating existing records)
def insert_new_data(data):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    for coin, details in data.items():
        cursor.execute('''
            INSERT INTO crypto_prices (coin_name, usd_price, usd_24h_change, last_updated_at, description, category)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            coin, details["usd"], details["usd_24h_change"],
            details["last_updated_at"],  details["description"], details["category"]
        ))

    conn.commit()
    conn.close()

# Insert new data into SQLite database
insert_new_data(data)

# Function to update last_updated_dt field
def update_last_updated_dt():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE crypto_prices 
        SET last_updated_dt = datetime(last_updated_at, 'unixepoch')
        WHERE last_updated_dt IS NULL;
    """)
    conn.commit()
    conn.close()

update_last_updated_dt()

# # Function to fetch all cryptocurrency data from the SQLite database and display it
# # This is useful for checking the state of data inside the database
# def fetch_data():
#     conn = sqlite3.connect(DB_FILE)
#     query = "SELECT * FROM crypto_prices ORDER BY last_updated_dt DESC;"
#     df = pd.read_sql(query, conn)
#     conn.close()

#     print(df)

# fetch_data()

##### DATA PREPARATION FOR GOOGLE SHEETS #####

# Function to aggregate data by category
def aggregate_by_category():
    query = """
    SELECT 
        category, 
        COUNT(DISTINCT coin_name) AS Num_coins,
        ROUND(AVG(usd_price), 2) AS Avg_price, 
        ROUND(AVG(usd_24h_change) / 100, 4) AS Avg_change,
        MAX(last_updated_dt)
    FROM crypto_prices
    GROUP BY Category
    ORDER BY Avg_price DESC;
    """

    # Connect to SQLite and fetch data
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql(query, conn)
    conn.close()
    
    # Format df
    df.columns = ['Category', 'Number of coins', 'Average price (USD)', 'Average change (24h)', 'Last updated']
    df['Last updated'] = pd.to_datetime(df['Last updated']) + timedelta(hours=1)
    df['Last updated'] = pd.to_datetime(df['Last updated']).dt.strftime('%d %b %Y %H:%M')
    
    return df

# Store the aggregated data
aggregated_data = aggregate_by_category()

# Fetch all coins data
def fetch_all_coins():
    query = """
    SELECT 
        cp.coin_name AS Coin, 
        cp.description AS Description,
        cp.usd_price AS Price, 
        ROUND(cp.usd_24h_change / 100, 4) AS Change, 
        cp.last_updated_dt AS LastUpdated
    FROM crypto_prices cp
    INNER JOIN (
        SELECT coin_name, MAX(last_updated_at) AS max_updated
        FROM crypto_prices
        GROUP BY coin_name
    ) latest ON cp.coin_name = latest.coin_name AND cp.last_updated_at = latest.max_updated
    ORDER BY Price DESC;
    """

    # Connect to SQLite and fetch data
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql(query, conn)
    conn.close()
    
    # Format df
    df['Last updated'] = pd.to_datetime(df['LastUpdated']) + timedelta(hours=1)
    df['Last updated'] = pd.to_datetime(df['Last updated']).dt.strftime('%d %b %Y, %H:%M')
    df.drop(columns=["LastUpdated"], inplace=True)
    df['Coin'] = df['Coin'].str.capitalize()
    df.rename(columns={"Price": "Price (USD)", "Change": "Change (24h)"}, inplace=True)
  
    return df

# Fetch all coins data
all_coins_data = fetch_all_coins()

##### UPLOAD DATA TO GOOGLE SHEETS #####

# Function to upload data to Google Sheets
def upload_to_google_sheets(sheet_name, dataframe):
    spreadsheet = gcp_client.open(sheet_name)
    sheet = spreadsheet.sheet1
    sheet.clear()
    
    # Convert DataFrame to a list of lists (Google Sheets format)
    data_list = [dataframe.columns.tolist()] + dataframe.values.tolist()
    
    # Upload data to Google Sheets
    sheet.update(values=data_list, range_name="A1")
    
# Upload the data to respective Google Sheets
upload_to_google_sheets("crypto-aggregated", aggregated_data)
upload_to_google_sheets("crypto-all-coins", all_coins_data)

# Function to format Google Sheets output
def format_google_sheets(sheet_name):
    spreadsheet = gcp_client.open(sheet_name)
    sheet = spreadsheet.sheet1

    sheet.format("C:C", {"numberFormat": {"type": "NUMBER", "pattern": "#,##0.00"}}) 
    sheet.format("D:D", {"numberFormat": {"type": "NUMBER", "pattern": "0.00%"}})  
    sheet.format("E:E", {"numberFormat": {"type": "TEXT"}}) 
    sheet.format("A1:E1", {"textFormat": {"bold": True}})

# Apply formatting to both sheets
format_google_sheets("crypto-aggregated")
format_google_sheets("crypto-all-coins")