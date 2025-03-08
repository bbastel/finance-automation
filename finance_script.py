import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import os
import json

# Funktion zum Laden der Watchlist
def load_watchlist():
    watchlist = os.environ.get('WATCHLIST', '').split(',')
    return [stock.strip() for stock in watchlist if stock.strip()]

# Funktion zum Abrufen von Finanznachrichten.de
def scrape_finanznachrichten():
    url = "https://www.finanznachrichten.de/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')

        # Extrahiere Nachrichten
        news_items = []
        articles = soup.find_all('article')

        for article in articles:
            headline_tag = article.find('h2') or article.find('h3')
            if headline_tag:
                headline = headline_tag.text.strip()

                # Suche nach Link
                link_tag = headline_tag.find('a')
                link = link_tag['href'] if link_tag and 'href' in link_tag.attrs else ""
                if link and not link.startswith('http'):
                    link = "https://www.finanznachrichten.de" + link

                # Suche nach Beschreibung
                desc_tag = article.find('p')
                description = desc_tag.text.strip() if desc_tag else ""

                news_items.append({
                    'headline': headline,
                    'description': description,
                    'link': link,
                    'source': 'Finanznachrichten.de'
                })

        # Extrahiere Kursveränderungen
        price_changes = []
        tables = soup.find_all('table', class_='table')

        for table in tables:
            rows = table.find_all('tr')
            for row in rows:
                cells = row.find_all('td')
                if len(cells) >= 3:
                    try:
                        stock_name = cells[0].text.strip()
                        price = cells[1].text.strip()
                        change = cells[2].text.strip()

                        # Versuche, den Prozentsatz zu extrahieren
                        import re
                        change_percent = re.search(r'([+-]?\d+,\d+%)', change)
                        if change_percent:
                            change_percent = change_percent.group(1)
                        else:
                            change_percent = change

                        price_changes.append({
                            'stock': stock_name,
                            'price': price,
                            'change': change_percent,
                            'source': 'Finanznachrichten.de'
                        })
                    except:
                        continue

        return news_items, price_changes

    except Exception as e:
        print(f"Fehler beim Abrufen von Finanznachrichten.de: {e}")
        return [], []

# Funktion zum Abrufen von Investing.com
def scrape_investing():
    url = "https://de.investing.com/news/stock-market-news"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')

        # Extrahiere Nachrichten
        news_items = []
        articles = soup.select('div.largeTitle article')

        for article in articles:
            headline_tag = article.select_one('a.title')
            if headline_tag:
                headline = headline_tag.text.strip()

                # Extrahiere Link
                link = headline_tag['href'] if 'href' in headline_tag.attrs else ""
                if link and not link.startswith('http'):
                    link = "https://de.investing.com" + link

                # Extrahiere Beschreibung
                desc_tag = article.select_one('p')
                description = desc_tag.text.strip() if desc_tag else ""

                news_items.append({
                    'headline': headline,
                    'description': description,
                    'link': link,
                    'source': 'Investing.com'
                })

        # Versuche, Marktdaten zu extrahieren
        price_changes = []
        try:
            # Versuche, die Marktübersicht zu finden
            market_overview = soup.select('table.genTbl.closedTbl.crossRatesTbl')
            if market_overview:
                rows = market_overview[0].select('tbody tr')
                for row in rows:
                    cells = row.select('td')
                    if len(cells) >= 3:
                        stock_name = cells[0].text.strip()
                        price = cells[1].text.strip()
                        change = cells[2].text.strip()

                        price_changes.append({
                            'stock': stock_name,
                            'price': price,
                            'change': change,
                            'source': 'Investing.com'
                        })
        except Exception as e:
            print(f"Fehler beim Extrahieren der Marktdaten von Investing.com: {e}")

        return news_items, price_changes

    except Exception as e:
        print(f"Fehler beim Abrufen von Investing.com: {e}")
        return [], []

# Funktion zum Filtern von Nachrichten und Kursen nach Watchlist
def filter_by_watchlist(news_items, price_changes, watchlist):
    if not watchlist:
        return news_items, price_changes

    filtered_news = []
    for news in news_items:
        for stock in watchlist:
            if stock.lower() in news['headline'].lower() or stock.lower() in news['description'].lower():
                news['matched_stock'] = stock
                filtered_news.append(news)
                break

    filtered_prices = []
    for price in price_changes:
        for stock in watchlist:
            if stock.lower() in price['stock'].lower():
                price['matched_stock'] = stock
                filtered_prices.append(price)
                break

    return filtered_news, filtered_prices

# Funktion zum Erstellen des E-Mail-Inhalts
def create_email_content(fn_news, fn_prices, inv_news, inv_prices, watchlist_news, watchlist_prices):
    now = datetime.now().strftime("%d.%m.%Y %H:%M")

    html = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; }}
            h1, h2, h3 {{ color: #333366; }}
            table {{ border-collapse: collapse; width: 100%; margin-bottom: 20px; }}
            th, td {{ text-align: left; padding: 8px; border-bottom: 1px solid #ddd; }}
            th {{ background-color: #f2f2f2; }}
            tr:hover {{ background-color: #f5f5f5; }}
            .positive {{ color: green; }}
            .negative {{ color: red; }}
            .source {{ color: gray; font-size: 0.8em; }}
        </style>
    </head>
    <body>
        <h1>Finanzmarkt-Zusammenfassung vom {now}</h1>
    """

    # Watchlist-Bereich
    if watchlist_news or watchlist_prices:
        html += "<h2>Deine Watchlist</h2>"

        if watchlist_prices:
            html += """
            <h3>Kursbewegungen deiner beobachteten Aktien</h3>
            <table>
                <tr>
                    <th>Aktie</th>
                    <th>Kurs</th>
                    <th>Veränderung</th>
                    <th>Quelle</th>
                </tr>
            """

            for price in watchlist_prices:
                change_class = ""
                if "+" in price['change']:
                    change_class = "positive"
                elif "-" in price['change']:
                    change_class = "negative"

                html += f"""
                <tr>
                    <td>{price['stock']}</td>
                    <td>{price['price']}</td>
                    <td class="{change_class}">{price['change']}</td>
                    <td class="source">{price['source']}</td>
                </tr>
                """

            html += "</table>"

        if watchlist_news:
            html += "<h3>Nachrichten zu deinen beobachteten Aktien</h3>"

            for news in watchlist_news:
                html += f"""
                <div>
                    <h4><a href="{news['link']}">{news['headline']}</a></h4>
                    <p>{news['description']}</p>
                    <p class="source">Quelle: {news['source']} | Aktie: {news.get('matched_stock', '')}</p>
                </div>
                <hr>
                """

    # Finanznachrichten.de Bereich
    html += "<h2>Finanznachrichten.de</h2>"

    if fn_prices:
        html += """
        <h3>Auffällige Kursbewegungen</h3>
        <table>
            <tr>
                <th>Aktie</th>
                <th>Kurs</th>
                <th>Veränderung</th>
            </tr>
        """

        for price in fn_prices[:10]:  # Begrenze auf 10 Einträge
            change_class = ""
            if "+" in price['change']:
                change_class = "positive"
            elif "-" in price['change']:
                change_class = "negative"

            html += f"""
            <tr>
                <td>{price['stock']}</td>
                <td>{price['price']}</td>
                <td class="{change_class}">{price['change']}</td>
            </tr>
            """

        html += "</table>"

    if fn_news:
        html += "<h3>Aktuelle Nachrichten</h3>"

        for news in fn_news[:5]:  # Begrenze auf 5 Einträge
            html += f"""
            <div>
                <h4><a href="{news['link']}">{news['headline']}</a></h4>
                <p>{news['description']}</p>
            </div>
            <hr>
            """

    # Investing.com Bereich
    html += "<h2>Investing.com</h2>"

    if inv_prices:
        html += """
        <h3>Auffällige Kursbewegungen</h3>
        <table>
            <tr>
                <th>Aktie</th>
                <th>Kurs</th>
                <th>Veränderung</th>
            </tr>
        """

        for price in inv_prices[:10]:  # Begrenze auf 10 Einträge
            change_class = ""
            if "+" in price['change']:
                change_class = "positive"
            elif "-" in price['change']:
                change_class = "negative"

            html += f"""
            <tr>
                <td>{price['stock']}</td>
                <td>{price['price']}</td>
                <td class="{change_class}">{price['change']}</td>
            </tr>
            """

        html += "</table>"

    if inv_news:
        html += "<h3>Aktuelle Nachrichten</h3>"

        for news in inv_news[:5]:  # Begrenze auf 5 Einträge
            html += f"""
            <div>
                <h4><a href="{news['link']}">{news['headline']}</a></h4>
                <p>{news['description']}</p>
            </div>
            <hr>
            """

    html += """
        <p>Diese E-Mail wurde automatisch generiert.</p>
    </body>
    </html>
    """

    # Speichere den HTML-Inhalt in einer Datei
    with open('report.html', 'w', encoding='utf-8') as f:
        f.write(html)

    print("Bericht wurde in report.html gespeichert")
    return html

# Hauptfunktion
def main():
    print("Finanzmarkt-Automatisierung gestartet")

    # Lade die Watchlist
    watchlist = load_watchlist()
    print(f"Watchlist geladen: {watchlist}")

    # Abrufen der Daten
    fn_news, fn_prices = scrape_finanznachrichten()
    inv_news, inv_prices = scrape_investing()

    # Filtern nach Watchlist
    watchlist_news, watchlist_prices = [], []
    if watchlist:
        watchlist_news_fn, watchlist_prices_fn = filter_by_watchlist(fn_news, fn_prices, watchlist)
        watchlist_news_inv, watchlist_prices_inv = filter_by_watchlist(inv_news, inv_prices, watchlist)

        watchlist_news = watchlist_news_fn + watchlist_news_inv
        watchlist_prices = watchlist_prices_fn + watchlist_prices_inv

    # Erstellen des Berichts
    now = datetime.now()
    subject = f"Finanzmarkt-Zusammenfassung {now.strftime('%d.%m.%Y %H:%M')}"
    create_email_content(fn_news, fn_prices, inv_news, inv_prices, watchlist_news, watchlist_prices)

    print("Verarbeitung abgeschlossen")

if __name__ == "__main__":
    main()
