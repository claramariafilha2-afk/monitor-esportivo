"""Monitor neutro de partidas usando API-Football v3. Sem apostas."""
import os, json, time, urllib.request, urllib.parse, urllib.error
from datetime import datetime, timezone
from pathlib import Path

BASE='https://v3.football.api-sports.io'
OUT=Path(__file__).resolve().parent/'dados'
OUT.mkdir(exist_ok=True)

def get_json(url, headers=None, data=None):
    req=urllib.request.Request(url, data=data, headers=headers or {}, method='POST' if data is not None else 'GET')
    with urllib.request.urlopen(req, timeout=25) as res:
        return json.load(res)

def fixtures_live(api_key):
    data=get_json(BASE+'/fixtures?live=all', {'x-apisports-key':api_key})
    if data.get('errors'):
        raise RuntimeError('Erro da API: '+str(data['errors']))
    return data.get('response',[])

def format_match(x):
    fixture=x.get('fixture') or {}; league=x.get('league') or {}; teams=x.get('teams') or {}; goals=x.get('goals') or {}
    return {'id':fixture.get('id'), 'liga':league.get('name'), 'pais':league.get('country'),
            'mandante':(teams.get('home') or {}).get('name'), 'visitante':(teams.get('away') or {}).get('name'),
            'gols_mandante':goals.get('home'), 'gols_visitante':goals.get('away'),
            'minuto':(fixture.get('status') or {}).get('elapsed'), 'fase':(fixture.get('status') or {}).get('short')}

def telegram_send(token, chat_id, message):
    url='https://api.telegram.org/bot'+token+'/sendMessage'
    data=urllib.parse.urlencode({'chat_id':chat_id,'text':message[:3900]}).encode()
    get_json(url, {'Content-Type':'application/x-www-form-urlencoded'},data)

def run_once():
    key=os.getenv('API_FOOTBALL_KEY')
    if not key: raise RuntimeError('Defina API_FOOTBALL_KEY no ambiente.')
    now=datetime.now(timezone.utc).isoformat()
    games=[format_match(x) for x in fixtures_live(key)]
    snapshot={'coletado_em_utc':now,'total':len(games),'jogos':games}
    file=OUT/('jogos_'+datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')+'.json')
    file.write_text(json.dumps(snapshot,ensure_ascii=False,indent=2),encoding='utf-8')
    print(f'{now}: {len(games)} partidas ao vivo; salvo em {file.name}')
    token=os.getenv('TELEGRAM_BOT_TOKEN'); chat=os.getenv('TELEGRAM_CHAT_ID')
    if token and chat:
        # Apenas resumo de placares, sem sinais, probabilidades ou recomendações.
        lines=[f"{g['mandante']} {g['gols_mandante']}-{g['gols_visitante']} {g['visitante']} ({g['minuto'] or '?'}', {g['fase']})" for g in games[:15]]
        telegram_send(token,chat,'Monitor esportivo | partidas ao vivo: '+str(len(games))+'\n'+'\n'.join(lines))

if __name__=='__main__':
    interval=int(os.getenv('INTERVALO_MINUTOS','10'))
    if interval < 5: raise RuntimeError('INTERVALO_MINUTOS deve ser >= 5.')
    if os.getenv('MODO_CONTINUO','0')=='1':
        while True:
            try: run_once()
            except (RuntimeError,urllib.error.URLError,TimeoutError) as exc: print('Falha:',exc)
            time.sleep(interval*60)
    else: run_once()
