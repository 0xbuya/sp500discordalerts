import os
import requests
from dotenv import load_dotenv
from bs4 import BeautifulSoup
import discord
from discord.ext import commands
import tweepy
import pandas as pd
from datetime import datetime, timedelta
from io import StringIO, BytesIO

load_dotenv()

# === CONFIG ===
# do not forget to create an .env file with your keys
# also ensure requirements are installed from requirements.txt
FINNHUB_KEY = os.getenv('FINNHUB_KEY')
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
TWITTER_API_KEY = os.getenv('TWITTER_API_KEY')
TWITTER_API_SECRET = os.getenv('TWITTER_API_SECRET')
TWITTER_ACCESS_TOKEN = os.getenv('TWITTER_ACCESS_TOKEN')
TWITTER_ACCESS_SECRET = os.getenv('TWITTER_ACCESS_SECRET')
DAYS_BACK = int(os.getenv('DAYS_BACK', 7))

if not FINNHUB_KEY:
    raise ValueError("FINNHUB_KEY not found in .env file!")

# === BOT SETUP ===
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)
start_time = datetime.now()

twitter_client = tweepy.Client(
    consumer_key=TWITTER_API_KEY,
    consumer_secret=TWITTER_API_SECRET,
    access_token=TWITTER_ACCESS_TOKEN,
    access_token_secret=TWITTER_ACCESS_SECRET
)

# === 1. Get S&P 500 tickers ===
def get_sp500_tickers():
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"}
    response = requests.get(url, headers=headers, timeout=15)
    print(f"Wikipedia status: {response.status_code}")

    if response.status_code != 200:
        print("Using fallback list.")
        fallback = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA', 'AL', 'CRS', 'NET', 'EWBC']
        return fallback

    soup = BeautifulSoup(response.text, 'html.parser')
    table = soup.find('table', {'id': 'constituents'})
    if not table:
        raise ValueError("Wikipedia table structure changed!")
    
    df = pd.read_html(StringIO(str(table)))[0]
    tickers = df['Symbol'].str.replace('.', '-', regex=False).tolist()
    print(f"Successfully fetched {len(tickers)} S&P 500 tickers from Wikipedia")
    return tickers

# === 2. Fetch insider data ===
def fetch_insider_data(days_back=DAYS_BACK):
    sp500_tickers = get_sp500_tickers()[:50]  # Remove [:50] for full on paid tier
    all_data = []
    start_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')
    end_date = datetime.now().strftime('%Y-%m-%d')
    
    print(f"Fetching Finnhub data for {len(sp500_tickers)} tickers (past {days_back} days)...")
    for ticker in sp500_tickers:
        url = f"https://finnhub.io/api/v1/stock/insider-transactions?symbol={ticker}&from={start_date}&to={end_date}&token={FINNHUB_KEY}"
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json().get('data', [])
                all_data.extend(data)
        except Exception as e:
            print(f"Request failed for {ticker}: {e}")
    
    df = pd.DataFrame(all_data)
    if df.empty:
        print("No insider trades returned.")
        return df

    print("Finnhub columns:", list(df.columns))
    df['ticker'] = df['symbol'].str.upper()
    df['filingDate'] = pd.to_datetime(df['filingDate'], errors='coerce')
    df['transactionDate'] = pd.to_datetime(df['transactionDate'], errors='coerce')
    
    df['net_shares'] = pd.to_numeric(df['change'], errors='coerce').fillna(0)
    
    df = df.drop_duplicates(subset=['ticker', 'filingDate', 'name', 'change'])
    
    cutoff = datetime.now() - timedelta(days=days_back)
    df = df[df['filingDate'] >= cutoff].copy()

    print(f"Fetched and processed {len(df)} unique insider transactions from last {days_back} days")
    return df

# === 3. Summarize ===
def summarize_insiders(df, sp500_tickers):
    if df.empty:
        return "No recent insider transactions found."

    # Net activity in S&P 500
    sp500_df = df[df['ticker'].isin(sp500_tickers)].copy()
    net_summary = "No insider activity in S&P 500 recently.\n\n"
    if not sp500_df.empty:
        grouped = sp500_df.groupby('ticker')['net_shares'].sum().reset_index()
        significant = grouped[grouped['net_shares'].abs() >= 10000]
        if not significant.empty:
            significant = significant.sort_values('net_shares', key=abs, ascending=False).head(10)
            lines = [f"{row['ticker']:5} → {'Net Buy' if row['net_shares'] > 0 else 'Net Sell'} {abs(row['net_shares']):,} shares" for _, row in significant.iterrows()]
            net_summary = "Significant Net Activity in S&P 500:\n" + "\n".join(lines) + "\n\n"

    # Recent Buys (positive change or code 'P')
    buys_df = df[(df['net_shares'] > 0) | (df['transactionCode'] == 'P')].copy()
    acquisition_lines = ["Recent Insider Acquisitions (Buys):"]
    if not buys_df.empty:
        buys_df = buys_df.sort_values('filingDate', ascending=False).head(20)
        for _, row in buys_df.iterrows():
            ticker = row.get('ticker', 'UNK')
            insider = row.get('name', 'Insider')
            shares = int(abs(row['net_shares'])) if row['net_shares'] != 0 else 0
            price = f" @ ${float(row.get('transactionPrice', 0)):.2f}" if row.get('transactionPrice') else ''
            date_str = row['filingDate'].strftime('%Y-%m-%d') if pd.notnull(row['filingDate']) else 'Unknown'
            owned_str = f" — Now owns {int(row.get('share', 0)):,}" if row.get('share') else ''
            line = f"{ticker:5} → {insider}: +{shares:,} shares{price} ({date_str}){owned_str}"
            acquisition_lines.append(line)
    else:
        acquisition_lines.append("No recent insider acquisitions found.")

    # Recent Sells (negative change or code 'S')
    sales_df = df[(df['net_shares'] < 0) | (df['transactionCode'] == 'S')].copy()
    sales_lines = ["\nRecent Insider Dispositions (Sales):"]
    if not sales_df.empty:
        sales_df = sales_df.sort_values('filingDate', ascending=False).head(20)
        for _, row in sales_df.iterrows():
            ticker = row.get('ticker', 'UNK')
            insider = row.get('name', 'Insider')
            shares = int(abs(row['net_shares'])) if row['net_shares'] != 0 else 0
            price = f" @ ${float(row.get('transactionPrice', 0)):.2f}" if row.get('transactionPrice') else ''
            date_str = row['filingDate'].strftime('%Y-%m-%d') if pd.notnull(row['filingDate']) else 'Unknown'
            owned_str = f" — Now owns {int(row.get('share', 0)):,}" if row.get('share') else ''
            line = f"{ticker:5} → {insider}: -{shares:,} shares{price} ({date_str}){owned_str}"
            sales_lines.append(line)
    else:
        sales_lines.append("No recent insider dispositions found.")

    return net_summary + "\n".join(acquisition_lines + sales_lines)

# === 4. Main execution ===
@bot.event
async def on_ready():
    print(f'{bot.user} is online!')

# === Command: !insider [days] ===
@bot.command(name='insider')
async def insider(ctx, days: int = DAYS_BACK):
    await ctx.send(f"Fetching insider data for past {days} days...")
    channel = ctx.channel
    try:
        sp500_tickers = get_sp500_tickers()
        df = fetch_insider_data(days_back=days)
        summary = summarize_insiders(df, sp500_tickers)

        date_str = datetime.now().strftime('%Y-%m-%d')
        full_message = f"**S&P 500 Insider Trading Summary (Past {days} Days) — {date_str}**\n```{summary}```"

        # Save CSV
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        csv_filename = f"insider_trades_raw_{timestamp}.csv"
        df.to_csv(csv_filename, index=False)
        print(f"Full data saved to {csv_filename} ({len(df)} rows)")

        # Send to Discord
        if len(full_message) <= 2000:
            await channel.send(full_message)
        else:
            header = f"**S&P 500 Insider Trading Summary (Past {days} Days) — {date_str}**\nFull summary attached."
            bio = BytesIO(summary.encode('utf-8'))
            bio.seek(0)
            await channel.send(header, file=discord.File(bio, "summary.txt"))
            with open(csv_filename, 'rb') as f:
                await channel.send("Raw data:", file=discord.File(f, csv_filename))
        print("Sent to Discord")

        # Tweet - note that presently this function is one I have disabled but it would work the same as the discord bot, except it's an X account
        try:
            tweet = f"S&P 500 Insider Moves (Past {days} Days as of {datetime.now().strftime('%b %d')}):\n{summary.replace('→', '->')[:200]}..."
            twitter_client.create_tweet(text=tweet)
            print("Posted to X")
        except Exception as e:
            print(f"Twitter failed: {e}")

    except Exception as e:
        await channel.send(f"Error: {e}")

bot.run(DISCORD_TOKEN)
