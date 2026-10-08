import os, re, time, json, logging, threading, sqlite3, unicodedata
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import requests
import telebot

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
LOG=logging.getLogger('uzex')
TOKEN=os.environ['BOT_TOKEN']
CHAT_ID=os.getenv('CHAT_ID','').strip()
INTERVAL=max(300,int(os.getenv('SCAN_INTERVAL_SECONDS','1800')))
PAGE_SIZE=max(10,min(500,int(os.getenv('PAGE_SIZE','100'))))
PAGES=max(1,min(30,int(os.getenv('PAGES_PER_TYPE','5'))))
DB=os.getenv('DB_PATH','/tmp/uzex_seen.sqlite3')
API='https://apietender.uzex.uz/api/common/TradeList'
BOT=telebot.TeleBot(TOKEN, threaded=False)
LOCK=threading.Lock()
KEYWORDS=['burgul','burgil','burgulash','burgilash','бурени','буров','бурғу','бург','portlat','портлат','взрыв','скважин','quduq qaz','қудуқ қаз']
HEADERS={'Accept':'application/json','Content-Type':'application/json; charset=UTF-8','Origin':'https://etender.uzex.uz','Referer':'https://etender.uzex.uz/','User-Agent':'Mozilla/5.0 (compatible; TenderMonitor/1.0)','language':'uzb'}

def normalize(s):
 s=str(s or '').casefold().replace('ʻ',"'").replace('‘',"'").replace('’',"'").replace('ғ','г').replace('ў','у')
 return ''.join(c for c in unicodedata.normalize('NFKD',s) if not unicodedata.combining(c)).replace("'",'')

def matching(title):
 s=normalize(title)
 return any(normalize(k) in s for k in KEYWORDS)

def rows_from(payload):
 if isinstance(payload,list): return payload
 if isinstance(payload,dict):
  for key in ('data','Data','result','Result','items','Items','trades','Trades','list','List'):
   if key in payload:
    result=rows_from(payload[key]);
    if result is not None:return result
 return None

def value(row,*keys):
 for key in keys:
  if key in row and row[key] is not None:return row[key]
 return None

def parse_row(row):
 if not isinstance(row,dict):return None
 lot=value(row,'id','Id','ID','TradeId','tradeId','trade_id')
 title=value(row,'name','Name','TradeName','tradeName','title','Title','LotName','lotName')
 if not lot or not title:return None
 return {'id':str(lot),'title':str(title),'url':f'https://etender.uzex.uz/lot/{lot}'}

def get_page(session,type_id,start,stop):
 r=session.post(API,headers=HEADERS,json={'TypeId':type_id,'From':start,'To':stop,'System_Id':0},timeout=30)
 r.raise_for_status()
 try: data=r.json()
 except ValueError as e:raise RuntimeError(f'API JSON emas: HTTP {r.status_code}, bosh qismi: {r.text[:120]!r}') from e
 rows=rows_from(data)
 if rows is None:raise RuntimeError('Noma’lum API JSON tuzilmasi: '+str(list(data)[:12] if isinstance(data,dict) else type(data).__name__))
 return rows

def scan():
 if not LOCK.acquire(blocking=False):return {'error':'Oldingi qidiruv hali tugamagan'}
 try:
  result={'checked':0,'matched':0,'sent':0,'errors':[],'samples':[]}
  with requests.Session() as session:
   for type_id in (1,2):
    for page in range(PAGES):
     try: rows=get_page(session,type_id,page*PAGE_SIZE,(page+1)*PAGE_SIZE)
     except Exception as exc:
      LOG.exception('API xatosi type=%s page=%s',type_id,page)
      result['errors'].append(f'Type {type_id}, sahifa {page+1}: {type(exc).__name__}: {str(exc)[:180]}')
      break
     if not rows:break
     for raw in rows:
      result['checked']+=1
      item=parse_row(raw)
      if not item:
       if len(result['samples'])<2 and isinstance(raw,dict):result['samples'].append(', '.join(list(raw)[:15]))
       continue
      if not matching(item['title']):continue
      result['matched']+=1
      with sqlite3.connect(DB) as db:
       exists=db.execute('SELECT 1 FROM seen WHERE id=?',(item['id'],)).fetchone()
       if exists:continue
       if CHAT_ID:
        try:BOT.send_message(CHAT_ID,f"🔎 Yangi mos tender\n№ {item['id']}\n{item['title']}\n{item['url']}",disable_web_page_preview=True)
        except Exception as exc:
         result['errors'].append('Telegram yuborish: '+str(exc)[:120]);continue
        result['sent']+=1
       db.execute('INSERT OR IGNORE INTO seen(id) VALUES(?)',(item['id'],))
     if len(rows)<PAGE_SIZE:break
  return result
 finally:LOCK.release()

def format_result(x):
 if 'error' in x:return x['error']
 s=f"Tekshirilgan: {x['checked']}\nMos: {x['matched']}\nYuborilgan: {x['sent']}"
 if x['errors']:s+='\n\n⚠️ API xatolari:\n'+'\n'.join(x['errors'][:4])
 if x['samples']:s+='\n\n⚠️ Lot maydonlari tanilmadi: '+x['samples'][0]
 if not CHAT_ID:s+='\n\n⚠️ CHAT_ID o‘rnatilmagan: avtomatik xabar yuborilmaydi.'
 return s

@BOT.message_handler(commands=['start','help'])
def help_cmd(m):
 BOT.reply_to(m,'Tender monitor. /scan — qidirish, /status — sozlamalar, /lot 515315 — havola. Avtomatik xabar uchun Render Environment ga CHAT_ID qo‘ying.')
@BOT.message_handler(commands=['status'])
def status(m):
 BOT.reply_to(m,f'CHAT_ID: {"bor" if CHAT_ID else "yo‘q"}\nSizning chat ID: {m.chat.id}\nInterval: {INTERVAL} soniya\nSahifalar: {PAGES} × {PAGE_SIZE} × 2 tur\nDB: {DB}')
@BOT.message_handler(commands=['lot'])
def lot(m):
 match=re.search(r'\b(\d{3,})\b',m.text or '')
 if not match:BOT.reply_to(m,'Masalan: /lot 515315');return
 BOT.reply_to(m,'Lot havolasi: https://etender.uzex.uz/lot/'+match.group(1)+'\nBu buyruq lot tafsilotlarini API orqali tekshirmaydi.')
@BOT.message_handler(commands=['scan'])
def scan_cmd(m):
 BOT.reply_to(m,'UZEX API tekshirilmoqda...')
 BOT.send_message(m.chat.id,format_result(scan()))

class Health(BaseHTTPRequestHandler):
 def do_GET(self):
  self.send_response(200);self.end_headers();self.wfile.write(b'OK')
 def log_message(self,*args):pass

def run_health():
 ThreadingHTTPServer(('0.0.0.0',int(os.getenv('PORT','10000'))),Health).serve_forever()

def monitor():
 while True:
  try:
   if CHAT_ID:LOG.info('Avtomatik qidiruv: %s',format_result(scan()))
   else:LOG.warning('CHAT_ID belgilanmagan, avtomatik qidiruv o‘tkazilmadi')
  except Exception:LOG.exception('Monitor xatosi')
  time.sleep(INTERVAL)

def main():
 with sqlite3.connect(DB) as db:db.execute('CREATE TABLE IF NOT EXISTS seen (id TEXT PRIMARY KEY)')
 threading.Thread(target=run_health,daemon=True).start()
 threading.Thread(target=monitor,daemon=True).start()
 while True:
  try:BOT.infinity_polling(timeout=20,long_polling_timeout=20)
  except Exception:LOG.exception('Telegram polling xatosi');time.sleep(10)

if __name__=='__main__':main()
