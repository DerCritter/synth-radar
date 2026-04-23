# 🎹 SynthRadar: Arbitrage Opportunity Tracker

SynthRadar is a professional-grade tool designed to monitor second-hand synthesizer markets (eBay and Kleinanzeigen) in real-time. It compares listing prices with global market values (Reverb) to identify high-margin arbitrage opportunities.

## 🚀 Features

- **Multi-Platform Scraping**: Real-time monitoring of Kleinanzeigen and eBay Germany (Buy It Now listings).
- **Intelligent Analysis**: Automatically identifies specific synthesizer models using flexible regex matching, ignoring accessories and non-instrument listings.
- **Arbitrage Calculation**: Calculates potential savings and profit margins relative to Reverb Price Guide data.
- **Dynamic Dashboard**: Modern, glassmorphic UI with live filtering by brand, platform, price, and "Hot Deal" status.
- **Smart Tracking**: "NEW" badges for fresh listings and click-to-dismiss persistence.
- **Anti-Bot Tech**: Integrated Playwright-based scraping logic to navigate modern web protections.

## 🛠️ Tech Stack

- **Backend**: Python, Flask
- **Scraper**: Playwright, BeautifulSoup4
- **Frontend**: Vanilla JS, HTML5, CSS3 (Glassmorphism)
- **Data Persistence**: JSON-based local storage (Production-ready for migration to DB)

## 📦 Installation

1. **Clone the repository**:
   ```bash
   git clone git@github.com:DerCritter/synth-radar.git
   cd synth-radar
   ```

2. **Setup virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   playwright install chromium
   ```

## 🎮 Usage

1. **Start the Scraping Engine**:
   ```bash
   python synth_arbitrage.py
   ```

2. **Launch the Dashboard**:
   ```bash
   python backend/app.py
   ```
   Access the dashboard at `http://localhost:8080`.

## 🤝 Contributing

This is a personal project aimed at optimizing gear hunting. Feel free to open issues or submit pull requests for new features or platform integrations.

## ⚖️ License

MIT License - See [LICENSE](LICENSE) for details.
