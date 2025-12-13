# S&P 500 discord alerts bot

Connect with me on X: @0xbuya | Instagram: YungTripoli | YouTube: https://youtube.com/yungtripoli

Free • Open Source • SEC Form 4 Tracker

<img width="1400" height="1400" alt="sp500 trade tracker bot ss from discord" src="https://github.com/user-attachments/assets/35ed7ada-c9b9-44ba-a291-425d1e5e134b" />


A free Discord bot that pulls and organizes data from two sources, a list of the S&P 500 index from Wikipedia (as it's a commonly updated sources), and a configurable API (currently Finnhub) tracking SEC Form 4 reporting. SEC Form 4 pertains to insider trading, which can be used as a research source prior to making market decisions. Researching market impact, which also presents inferable movement.

## Features
- On-demand commands: `!insider [days]` for summaries (default 7 days).
- Significant net buys/sells for S&P 500.
- Recent insider acquisitions and dispositions with details (names, shares, prices, ownership).
- Saves raw CSV locally for verification.
- Posts to Twitter/X.
- Configurable via .env (days back, API key).

## Setup Tutorial
### 1. Prerequisites
- Python 3.8+.
- Discord account and server.
- Finnhub API key (free at finnhub.io).
- Optional: Twitter API keys for posting.

### 2. Install Dependencies
pip install discord.py requests beautifulsoup4 tweepy pandas python-dotenv

### 3. Configure .env
Create `.env` file:

FINNHUB_KEY=keyhere

DISCORD_TOKEN=keyhere

DISCORD_CHANNEL_ID=channelIDhere

TWITTER_API_KEY=keyhere

TWITTER_API_SECRET=keyhere

TWITTER_ACCESS_TOKEN=keyhere

TWITTER_ACCESS_SECRET=keyhere


### 4. Create Discord Bot
- Go to discord.com/developers/applications > New App > Bot tab > Add Bot.
- Enable Message Content Intent.
- Copy Token to .env.
- OAuth2 URL Generator: bot scope, Send Messages permission > Invite to server.

### 5. Run Locally

python bot.py

- Bot online — type `!insider` in Discord.

### 6. Host 24/7
- Use Replit (free): Create repl, upload code, add .env secrets, "Always On".
- Or Render.com: GitHub repo > New Background Worker > Python > Add .env > `python bot.py`.

## Usage
- `!insider 30`: Past 30 days summary.
- CSV saved for verification.


Not financial advice. Data from public SEC filings via Finnhub.

Insider trading data is a powerful research signal — many studies show clustered buys/sells can precede market moves. Use responsibly for due diligence (not financial advice).

The ethos behind the making of this python bot is to support data analysts and market researchers seeking to unveil the smoke and mirrors behind recent market movements. Simplifying this data for researchers making use of massive online platforms like Discord allows us to host communities that are informed. The choice to publish this code which organizes public data is aligned with the SEC's intentions of reporting market makers movements. I hope you found this helpful and feel free to make improvements.

Do not forget to implement your own API keys respectively to see this particular configuration work.

