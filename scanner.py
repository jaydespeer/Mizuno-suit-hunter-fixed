import os
import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone
from playwright.sync_api import sync_playwright

STATE_FILE = "state.json"
REPORT_FILE = "latest_report.json"
DASHBOARD_FILE = "index.html"

MARKETPLACES = [
    {"name": "Buyee Mercari", "url": "https://buyee.jp/mercari/search?keyword=Mizuno%20GX%20Sonic%20M"},
    {"name": "Buyee Yahoo Auctions", "url": "https://buyee.jp/item/search/query/Mizuno%20GX%20Sonic%20M"},
    {"name": "Buyee Rakuma", "url": "https://buyee.jp/rakuma/search?keyword=Mizuno%20GX%20Sonic%20M"}
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
        .stat-card p { margin:
