import os
import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone

STATE_FILE = "state.json"
REPORT_FILE = "latest_report.json"
DASHBOARD_FILE = "index.html"

MARKETPLACES = [
    {"name": "Buyee Mercari", "url": "https://buyee.jp/mercari/search?keyword=Mizuno+GX+Sonic+M"},
    {"name": "Buyee Yahoo Auctions", "url": "https://buyee.jp/yahoo/search?query=Mizuno+GX+Sonic+M"},
    {"name": "Buyee Rakuma", "url": "https://buyee.jp/rakuma/search?keyword=Mizuno+GX+Sonic+M"}
]

EXCLUDED_TERMS = [
    "lite", "stream", "training", "women", "womens", "lady", "ladies",
    "junior", "jr", "kids", "child", "used", "secondhand", "pre-owned",
    "damaged", "repair", "defect", "レディース", "ジュニア", "中古", "ジャンク"
]

REQUIRED_TERMS = ["mizuno", "gx", "sonic"]

DASHBOARD_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Mizuno GX Sonic Suit Hunter</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #f4f6f8; color: #333; margin: 0; padding: 20px; }
        .container { max-width: 900px; margin: auto; background: #fff; padding: 24px; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.05); }
        h1 { color: #1a365d; font-size: 24px; margin-top: 0; }
        .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 15px; margin-bottom: 24px; }
        .stat-card { background: #edf2f7; padding: 16px; border-radius: 8px; text-align: center; }
        .stat-card h3 { margin: 0 0 8px 0; font-size: 13px; color: #4a5568; text-transform: uppercase; }
        .stat-card p { margin: 0; font-size: 20px; font-weight: bold; color: #2d3748; }
        .section { margin-bottom: 24px; }
        .card { border: 1px solid #e2e8f0; border-radius: 8px; padding: 16px; margin-bottom: 12px; }
        .badge { display: inline-block; padding: 4px 8px; font-size: 12px; font-weight: bold; border-radius: 4px; background: #3182ce; color: white; margin-bottom: 8px; }
        a { color: #3182ce; text-decoration: none; }
        a:hover { text-decoration: underline; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Mizuno GX Sonic Suit Hunter</h1>
        <p>Automated tracker monitoring Buyee marketplaces for genuine men's size M racing suits.</p>
        <div class="stats">
            <div class="stat-card"><h3>Last Scan</h3><p id="last-scan">-</p></div>
            <div class="stat-card"><h3>Marketplaces</h3><p id="marketplaces">-</p></div>
            <div class="stat-card"><h3>Inspected</h3><p id="inspected">-</p></div>
            <div class="stat-card"><h3>Matches</h3><p id="matches">-</p></div>
        </div>
        <div class="section"><h2>Best Overall</h2><div id="best-overall" class="card">No data yet.</div></div>
        <div class="section"><h2>Cheapest Verified</h2><div id="cheapest" class="card">No data yet.</div></div>
        <div class="section"><h2>Needs Manual Review</h2><div id="review"></div></div>
    </div>
    <script>
        fetch('latest_report.json')
            .then(r => r.json())
            .then(data => {
                document.getElementById('last-scan').innerText = data.last_successful_scan ? new Date(data.last_successful_scan).toLocaleTimeString() : 'Never';
                document.getElementById('marketplaces').innerText = data.marketplaces_checked;
                document.getElementById('inspected').innerText = data.listings_inspected;
                document.getElementById('matches').innerText = data.qualifying_matches;

                if (data.best_overall) {
                    document.getElementById('best-overall').innerHTML = `<span class="badge">BEST OVERALL</span><h3><a href="${data.best_overall.url}" target="_blank">${data.best_overall.title}</a></h3><p>¥${data.best_overall.price_jpy.toLocaleString()} (~£${data.best_overall.price_gbp}) • ${data.best_overall.marketplace} • Score: ${data.best_overall.score}</p>`;
                } else {
                    document.getElementById('best-overall').innerHTML = '<p>No qualifying best match found yet.</p>';
                }

                if (data.cheapest_verified) {
                    document.getElementById('cheapest').innerHTML = `<span class="badge" style="background:#38a169;">CHEAPEST VERIFIED</span><h3><a href="${data.cheapest_verified.url}" target="_blank">${data.cheapest_verified.title}</a></h3><p>¥${data.cheapest_verified.price_jpy.toLocaleString()} (~£${data.cheapest_verified.price_gbp}) • ${data.cheapest_verified.marketplace} • Score: ${data.cheapest_verified.score}</p>`;
                } else {
                    document.getElementById('cheapest').innerHTML = '<p>No qualifying cheapest match found yet.</p>';
                }

                const rev = document.getElementById('review');
                if (data.manual_review && data.manual_review.length) {
                    rev.innerHTML = data.manual_review.slice(0, 10).map(i => `<div class="card"><a href="${i.url}" target="_blank">${i.title}</a><p style="font-size:13px;color:#718096;">¥${i.price_jpy.toLocaleString()} • ${i.reason}</p></div>`).join('');
                } else {
                    rev.innerHTML = '<div class="card"><p>No items awaiting manual review.</p></div>';
                }
            });
    </script>
</body>
</html>"""

def load_json(filename, default):
    if os.path.exists(filename):
        try:
            with open(filename, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
