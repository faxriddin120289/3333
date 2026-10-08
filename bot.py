"""Uzbekistan tender monitor. Public HTML sources; no undocumented API assumptions."""
import hashlib
import html
import logging
import os
import re
import sqlite3
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import time
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import telebot
from telebot import types

load_dotenv()
TOKEN = os.getenv('BOT_TOKEN', '').strip()
if not TOKEN:
    raise SystemExit('BOT_TOKEN ni .env fayliga kiriting')
DB_PATH = os.getenv('DB_PATH', 'tenders.sqlite3')
INTERVAL = max(15, int(os.getenv('CHECK_INTERVAL_MINUTES', '60')))
TIMEOUT = 20
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
log = logging.getLogger('tenderbot')
bot = telebot.TeleBot(TOKEN, threaded=True)
http = requests.Session()
http.headers.update({'User-Agent': 'Mozilla/5.0 (compatible; TenderMonitor/2.0; public-information-monitor)', 'Accept-Language': 'uz,ru;q=0.8,en;q=0.5'})
DB_LOCK = threading.RLock()
SCAN_LOCK = threading.Lock()
DEFAULT_KEYWORDS = ['burg', 'бур', 'скважин', 'bvr', 'бвр', 'взрыв', 'portlat', 'karyer', 'карьер', 'геолог', 'буров', 'quduq']
# Only publicly accessible listing pages. Pages may change their markup or access policy.
SOURCES = {
    'etender': ('UZEX eTender', 'https://etender.uzex.uz/'),
    'xarid': ('UZEX xarid', 'https://xarid.uzex.uz/'),
}

@dataclass(frozen=True)
class Lot:
    source: str
    title: str
    url: str
    number: str = ''
    amount: str = ''
    deadline: str = ''
    customer: str = ''


def connect():
    con = sqlite3.connect(DB_PATH, timeout=30)
    con.row_factory = sqlite3.Row
    return con


def init_db():
    with DB_LOCK, connect() as con:
        con.execute('CREATE TABLE IF NOT EXISTS users (chat_id INTEGER PRIMARY KEY, keywords TEXT NOT NULL, alerts INTEGER NOT NULL DEFAULT 0)')
        con.execute('CREATE TABLE IF NOT EXISTS seen (chat_id INTEGER NOT NULL, lot_key TEXT NOT NULL, first_seen TEXT NOT NULL, PRIMARY KEY(chat_id,lot_key))')


def ensure_user(chat_id):
    with DB_LOCK, connect() as con:
        con.execute('INSERT OR IGNORE INTO users(chat_id,keywords) VALUES (?,?)', (chat_id, '\n'.join(DEFAULT_KEYWORDS)))


def get_user(chat_id):
    ensure_user(chat_id)
    with DB_LOCK, connect() as con:
        return con.execute('SELECT * FROM users WHERE chat_id=?', (chat_id,)).fetchone()


def norm(s):
    s = unicodedata.normalize('NFKC', str(s or '')).casefold()
    return re.sub(r'\s+', ' ', s).strip().replace('ʻ', "'").replace('‘', "'").replace('’', "'")


def matches(lot, keywords):
    haystack = norm(' '.join([lot.title, lot.customer]))
    return [k for k in keywords if norm(k) and norm(k) in haystack]


def lot_key(lot):
    base = f'{lot.source}|{lot.number or lot.url}|{norm(lot.title)}'
    return hashlib.sha256(base.encode()).hexdigest()


def parse_table(source, url, soup):
    """Extract tender-like rows only; never turn navigation links into fake tenders."""
    lots = []
    for table in soup.select('table'):
        headers = [norm(th.get_text(' ', strip=True)) for th in table.select('thead th')]
        for tr in table.select('tbody tr'):
            cells = tr.find_all('td', recursive=False)
            if len(cells) < 3:
                continue
            values = [td.get_text(' ', strip=True) for td in cells]
            if not any(values):
                continue
            def col(*terms):
                for i, header in enumerate(headers):
                    if any(term in header for term in terms) and i < len(values):
                        return values[i]
                return ''
            title = col('lot nomi', 'tovar nomi', 'nomlanishi', 'наименование', 'предмет закуп')
            number = col('lot raqami', 'номер лота', 'lot №')
            amount = col('boshlang', 'narx', 'цена', 'сумма')
            deadline = col('tugash', 'окончания', 'yakun')
            customer = col('buyurtmachi nomi', 'заказчик')
            if not title:
                # For unfamiliar table schemas, require a lot-number-like cell.
                if not any(re.fullmatch(r'\d{6,20}', v.strip()) for v in values):
                    continue
                title = max((v for v in values if len(v) > 15), key=len, default='')
            if not title or len(title) < 5:
                continue
            anchor = tr.select_one('a[href]')
            link = urljoin(url, anchor.get('href', '')) if anchor else url
            if urlparse(link).netloc != urlparse(url).netloc:
                link = url
            if not number:
                number = next((v for v in values if re.fullmatch(r'\d{6,20}', v.strip())), '')
            lots.append(Lot(source, title[:600], link, number[:60], amount[:100], deadline[:100], customer[:200]))
    return lots


def parse_cards(source, url, soup):
    """Read publicly visible UZEX lot cards without treating navigation as lots."""
    result = []
    for node in soup.select('a, article, div'):
        text = node.get_text(' ', strip=True)
        if len(text) > 1200 or len(text) < 35:
            continue
        number = re.search(r'(?:Lot raqami|Номер лота|Lot number)\\s*:?\\s*(\\d{8,20})', text, re.I)
        if not number:
            continue
        # Reject parent containers holding several cards.
        if len(re.findall(r'(?:Lot raqami|Номер лота|Lot number)', text, re.I)) != 1:
            continue
        title = re.search(r'(?:Lot raqami|Номер лота|Lot number)\\s*:?\\s*\\d{8,20}\\s*(.*?)(?:Boshlang.?ich narx|Начальная цена|Tugash sanasi|Дата окончания|$)', text, re.I)
        name = (title.group(1) if title else '').strip(' :-')
        if len(name) < 5:
            continue
        a = node if node.name == 'a' else node.select_one('a[href]')
        link = urljoin(url, a.get('href', '')) if a else url
        if urlparse(link).netloc not in ('etender.uzex.uz', 'xarid.uzex.uz'):
            link = url
        amount = re.search(r'(?:Boshlang.?ich narx|Начальная цена)\\s*:?\\s*([\\d ,.]+\\s*(?:UZS|сум)?)', text, re.I)
        deadline = re.search(r'(?:Tugash sanasi|Дата окончания)\\s*:?\\s*([\\d.: /-]+)', text, re.I)
        result.append(Lot(source, name[:600], link, number.group(1),
                          amount.group(1).strip() if amount else '',
                          deadline.group(1).strip() if deadline else '', ''))
    return list({lot_key(x): x for x in result}.values())


def fetch_source(key):
    name, url = SOURCES[key]
    errors = []
    try:
        response = http.get(url, timeout=TIMEOUT)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        lots = parse_table(key, url, soup) + parse_cards(key, url, soup)
        if lots:
            return list({lot_key(x): x for x in lots}.values()), None
    except requests.RequestException as exc:
        errors.append(f'HTTP: {type(exc).__name__}')
    # Render JS apps can have empty initial HTML. Render them with Chromium.
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-dev-shm-usage'])
            page = browser.new_page(locale='uz-UZ', viewport={'width': 1280, 'height': 900})
            page.goto(url, wait_until='domcontentloaded', timeout=45000)
            page.wait_for_timeout(9000)
            html_text = page.content()
            browser.close()
        soup = BeautifulSoup(html_text, 'html.parser')
        lots = parse_table(key, url, soup) + parse_cards(key, url, soup)
        if lots:
            return list({lot_key(x): x for x in lots}.values()), None
        errors.append('JavaScript sahifasi ochildi, ammo lotlar olinmadi (API, filtr yoki himoya sababli)')
    except Exception as exc:
        log.exception('Browser fetch failed for %s', key)
        errors.append(f'Chromium: {type(exc).__name__}')
    return [], f'{name}: ' + '; '.join(errors)

def collect(keys=None):
    found, errors = [], []
    for key in (keys or SOURCES):
        lots, error = fetch_source(key)
        found.extend(lots)
        if error:
            errors.append(error)
    unique = {lot_key(lot): lot for lot in found}
    return list(unique.values()), errors


def keyboard():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add('🔎 Hozir qidirish', '🔔 Kuzatuvni yoqish', '🔕 Kuzatuvni o‘chirish', '📋 Kalit so‘zlar', '✏️ Kalit so‘zlarni o‘zgartirish', '📊 Holat')
    return kb


def send(chat_id, text):
    bot.send_message(chat_id, text[:4000], parse_mode='HTML', disable_web_page_preview=True)


def render(lot, matched):
    e = html.escape
    parts = [f'📌 <b>{e(lot.title)}</b>', f'🌐 {e(SOURCES[lot.source][0])}']
    if lot.number: parts.append(f'🔢 Lot: {e(lot.number)}')
    if lot.amount: parts.append(f'💰 Narx: {e(lot.amount)}')
    if lot.deadline: parts.append(f'⏰ Tugash: {e(lot.deadline)}')
    if lot.customer: parts.append(f'🏢 Buyurtmachi: {e(lot.customer)}')
    parts.extend([f'🔎 Mos so‘zlar: {e(", ".join(matched))}', f'🔗 <a href="{e(lot.url, quote=True)}">Tenderni ochish</a>'])
    return '\n'.join(parts)


def scan_chat(chat_id, automatic=False):
    user = get_user(chat_id)
    keywords = [x for x in user['keywords'].splitlines() if x]
    if not automatic: send(chat_id, '🔍 Tender sahifalari tekshirilmoqda...')
    with SCAN_LOCK:
        lots, errors = collect()
    matched = [(lot, matches(lot, keywords)) for lot in lots]
    matched = [(lot, words) for lot, words in matched if words]
    delivered = 0
    for lot, words in matched[:30]:
        key = lot_key(lot)
        with DB_LOCK, connect() as con:
            exists = con.execute('SELECT 1 FROM seen WHERE chat_id=? AND lot_key=?', (chat_id, key)).fetchone()
        if automatic and exists:
            continue
        try:
            send(chat_id, render(lot, words))
        except Exception as exc:
            log.warning('Telegram send error: %s', exc)
            break
        with DB_LOCK, connect() as con:
            con.execute('INSERT OR IGNORE INTO seen VALUES (?,?,?)', (chat_id, key, datetime.now(timezone.utc).isoformat()))
        delivered += 1
    if not automatic:
        summary = f'📊 Tekshirilgan lotlar: {len(lots)}\n🎯 Mos lotlar: {len(matched)}\n📨 Yuborilgan: {delivered}'
        if len(matched) > 30: summary += '\nℹ️ Dastlabki 30 tasi ko‘rsatildi.'
        if errors: summary += '\n\n⚠️ Manba muammolari:\n' + '\n'.join(html.escape(x) for x in errors)
        if not matched and not errors: summary += '\nMos lot topilmadi (faqat o‘qilgan sahifalar bo‘yicha).'
        send(chat_id, summary)
    elif errors:
        log.warning('Scan errors: %s', errors)


@bot.message_handler(commands=['start', 'help'])
def start(message):
    ensure_user(message.chat.id)
    bot.send_message(message.chat.id, 'Assalomu alaykum! Tender monitoring botiga xush kelibsiz.\nSaytlar holatini /status orqali ko‘ring.', reply_markup=keyboard())


@bot.message_handler(commands=['status'])
def status(message):
    u = get_user(message.chat.id)
    send(message.chat.id, f'📊 Kuzatuv: {"yoqilgan" if u["alerts"] else "o‘chirilgan"}\n⏱ Interval: {INTERVAL} daqiqa\n🌐 Manbalar: {", ".join(SOURCES)}')


@bot.message_handler(commands=['keywords'])
def keywords_cmd(message):
    u = get_user(message.chat.id)
    send(message.chat.id, '📋 Kalit so‘zlar:\n' + '\n'.join('• ' + html.escape(x) for x in u['keywords'].splitlines()))


@bot.message_handler(commands=['setkeywords'])
def setkeywords_cmd(message):
    raw = message.text.partition(' ')[2].strip()
    if not raw:
        send(message.chat.id, 'Namuna: /setkeywords burg, бур, скважин, portlatish')
        return
    items = list(dict.fromkeys(x.strip() for x in raw.replace('\n', ',').split(',') if x.strip()))
    if len(items) > 40 or any(len(x) > 70 for x in items):
        send(message.chat.id, '❌ Eng ko‘pi 40 ta kalit so‘z, har biri 70 belgidan oshmasin.')
        return
    ensure_user(message.chat.id)
    with DB_LOCK, connect() as con:
        con.execute('UPDATE users SET keywords=? WHERE chat_id=?', ('\n'.join(items), message.chat.id))
    send(message.chat.id, f'✅ {len(items)} ta kalit so‘z saqlandi.')


@bot.message_handler(commands=['on', 'off'])
def alerts_cmd(message):
    ensure_user(message.chat.id)
    enabled = int(message.text.split()[0] == '/on')
    with DB_LOCK, connect() as con:
        con.execute('UPDATE users SET alerts=? WHERE chat_id=?', (enabled, message.chat.id))
    send(message.chat.id, '🔔 Avtomatik kuzatuv yoqildi.' if enabled else '🔕 Avtomatik kuzatuv o‘chirildi.')


@bot.message_handler(commands=['scan'])
def scan_cmd(message):
    scan_chat(message.chat.id)


@bot.message_handler(content_types=['text'])
def menu(message):
    t = message.text or ''
    if 'Hozir qidirish' in t: scan_chat(message.chat.id)
    elif 'Kuzatuvni yoqish' in t: message.text = '/on'; alerts_cmd(message)
    elif 'Kuzatuvni o‘chirish' in t: message.text = '/off'; alerts_cmd(message)
    elif 'Kalit so‘zlar' in t and 'o‘zgartirish' not in t: keywords_cmd(message)
    elif 'o‘zgartirish' in t: send(message.chat.id, '✏️ Quyidagicha yuboring:\n/setkeywords burg, бур, скважин, portlatish')
    elif 'Holat' in t: status(message)
    else: send(message.chat.id, 'Buyruqlar: /scan /on /off /keywords /setkeywords /status')


def monitor():
    while True:
        time.sleep(INTERVAL * 60)
        with DB_LOCK, connect() as con:
            users = [row['chat_id'] for row in con.execute('SELECT chat_id FROM users WHERE alerts=1')]
        for chat_id in users:
            try: scan_chat(chat_id, automatic=True)
            except Exception: log.exception('Monitor failed for %s', chat_id)


class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path not in ('/', '/health'):
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header('Content-Type', 'text/plain; charset=utf-8')
        self.end_headers()
        self.wfile.write(b'Tender monitor process is running; source health is reported in Telegram.')

    def log_message(self, *_args):
        pass


def run_health_server():
    port = int(os.getenv('PORT', '10000'))
    ThreadingHTTPServer(('0.0.0.0', port), HealthHandler).serve_forever()


if __name__ == '__main__':
    init_db()
    threading.Thread(target=run_health_server, daemon=True).start()
    threading.Thread(target=monitor, daemon=True).start()
    log.info('Tender monitor started; %s minute interval', INTERVAL)
    bot.remove_webhook()
    bot.infinity_polling(timeout=30, long_polling_timeout=30, skip_pending=True)
