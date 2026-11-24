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
            return default
    return default

def save_json(filename, data):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def send_discord_notification(item):
    webhook_url = os.environ.get("DISCORD_WEBHOOK")
    if not webhook_url:
        return

    badge = item.get("badge", "NEW MATCH")
    color = 3066993 if badge == "BEST OVERALL" else (5763719 if badge == "CHEAPEST VERIFIED" else 15844367)

    embed = {
        "title": f"[{badge}] {item['title']}",
        "url": item["url"],
        "color": color,
        "fields": [
            {"name": "Model", "value": item["model"], "inline": True},
            {"name": "Price", "value": f"¥{item['price_jpy']:,} (~£{item['price_gbp']})", "inline": True},
            {"name": "Marketplace", "value": item["marketplace"], "inline": True},
            {"name": "Condition", "value": item["condition"], "inline": True},
            {"name": "Match Score", "value": f"{item['score']}/110", "inline": True},
            {"name": "Why It Passed", "value": item["reason"], "inline": False}
        ],
        "footer": {"text": "Mizuno Suit Hunter"}
    }

    try:
        requests.post(webhook_url, json={"embeds": [embed]}, timeout=10)
    except Exception as e:
        print(f"Discord error: {e}")

def validate_and_score(title, price_jpy):
    text = title.lower()

    for term in EXCLUDED_TERMS:
        if term in text:
            return 0, f"Excluded term found: '{term}'", "Uncertain", "Unknown"

    for term in REQUIRED_TERMS:
        if term not in text:
            return 0, f"Missing required term: '{term}'", "Uncertain", "Unknown"

    has_size_m = any(k in text for k in ["size m", "サイズm", "サイズ m", " m ", "mサイズ"]) or text.endswith(" m")
    has_mens = any(k in text for k in ["men", "メンズ", "jammer", "half-spat", "spats", "ハーフスパッツ"])

    if not has_size_m:
        return 0, "Missing clear Size M evidence", "Uncertain", "GX Sonic"

    model = "GX Sonic (Unspecified Generation)"
    for gen in ["vi", "v", "iv", "iii", "neo", "pro"]:
        if f" {gen}" in text or f"-{gen}" in text or text.endswith(gen):
            model = f"GX Sonic {gen.upper()}"
            break

    score = 70
    if has_size_m:
        score += 15
    if has_mens:
        score += 15

    condition = "New / Unused (Inferred)"
    if any(k in text for k in ["new", "未使用", "新品"]):
        condition = "Brand New / Unused"
        score += 10

    if price_jpy > 45000:
        return 0, f"Above budget threshold: ¥{price_jpy}", "Uncertain", model

    return score, "Verified Men's Size M Mizuno GX Sonic racing suit.", condition, model

def run_scanner():
    state = load_json(STATE_FILE, {"seen_item_ids": []})
    seen_ids = set(state.get("seen_item_ids", []))

    report = {
        "last_successful_scan": datetime.now(timezone.utc).isoformat(),
        "marketplaces_checked": 0,
        "listings_inspected": 0,
        "qualifying_matches": 0,
        "best_overall": None,
        "cheapest_verified": None,
        "manual_review": [],
        "all_matches": [],
        "errors": []
    }

    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    all_valid_items = []

    for source in MARKETPLACES:
        report["marketplaces_checked"] += 1
        try:
            resp = requests.get(source["url"], headers=headers, timeout=15)
            if resp.status_code != 200:
                report["errors"].append(f"{source['name']} returned HTTP {resp.status_code}")
                continue

            soup = BeautifulSoup(resp.text, "html.parser")
            items = soup.select(".itemCard, .searchItemBox, li[data-item-id]")

            for item in items[:20]:
                report["listings_inspected"] += 1

                title_elem = item.select_one(".itemCard__title, .title, a")
                title = title_elem.get_text(strip=True) if title_elem else ""
                if not title:
                    continue

                link_elem = item.select_one("a")
                item_url = link_elem.get("href", "") if link_elem else source["url"]
                if item_url.startswith("/"):
                    item_url = "https://buyee.jp" + item_url

                item_id = item.get("data-item-id", item_url)
                if item_id in seen_ids:
                    continue

                price_elem = item.select_one(".itemCard__price, .price")
                price_text = price_elem.get_text(strip=True) if price_elem else "0"
                price_clean = "".join(filter(str.isdigit, price_text))
                price_jpy = int(price_clean) if price_clean else 0
                if price_jpy == 0:
                    continue

                score, reason, condition, model = validate_and_score(title, price_jpy)
                price_gbp = round(price_jpy * 0.0052, 2)

                item_data = {
                    "id": item_id,
                    "title": title,
                    "model": model,
                    "price_jpy": price_jpy,
                    "price_gbp": price_gbp,
                    "condition": condition,
                    "marketplace": source["name"],
                    "url": item_url,
                    "score": score,
                    "reason": reason
                }

                seen_ids.add(item_id)

                if score >= 85:
                    all_valid_items.append(item_data)
                else:
                    report["manual_review"].append(item_data)

        except Exception as e:
            report["errors"].append(f"{source['name']} error: {str(e)}")

    if all_valid_items:
        all_valid_items.sort(key=lambda x: (x["score"], -x["price_jpy"]), reverse=True)
        all_valid_items[0]["badge"] = "BEST OVERALL"
        report["best_overall"] = all_valid_items[0]

        cheapest = min(all_valid_items, key=lambda x: x["price_jpy"])
        if cheapest["id"] != all_valid_items[0]["id"]:
            cheapest["badge"] = "CHEAPEST VERIFIED"
        report["cheapest_verified"] = cheapest

        report["qualifying_matches"] = len(all_valid_items)
        report["all_matches"] = all_valid_items

        for item in all_valid_items:
            send_discord_notification(item)

    save_json(STATE_FILE, {"seen_item_ids": list(seen_ids)})
    save_json(REPORT_FILE, report)

    with open(DASHBOARD_FILE, "w", encoding="utf-8") as f:
        f.write(DASHBOARD_TEMPLATE)

if __name__ == "__main__":
    run_scanner()
