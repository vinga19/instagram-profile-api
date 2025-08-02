from flask import Flask, request, jsonify
import requests
import time
import random
from datetime import datetime, timedelta
import os
import json

app = Flask(__name__)

# Cache simples para evitar requisições repetidas
cache = {}
CACHE_DURATION = 300  # 5 minutos

# Controle de rate limiting
last_request_time = 0
MIN_DELAY = 1

def get_cached_profile(username):
    """Verifica se o perfil está no cache e ainda é válido"""
    if username in cache:
        cached_data, timestamp = cache[username]
        if datetime.now() - timestamp < timedelta(seconds=CACHE_DURATION):
            return cached_data
    return None

def cache_profile(username, data):
    """Salva o perfil no cache"""
    cache[username] = (data, datetime.now())

def rate_limit():
    """Implementa delay entre requisições"""
    global last_request_time
    current_time = time.time()
    time_since_last = current_time - last_request_time
    
    if time_since_last < MIN_DELAY:
        sleep_time = MIN_DELAY - time_since_last + random.uniform(0.1, 0.5)
        time.sleep(sleep_time)
    
    last_request_time = time.time()

def fetch_instagram_rapidapi_free(username):
    """
    Método de busca para a Instagram Scraper Stable API.
    Esta é a única fonte de dados configurada.
    """
    
    rapidapi_key = os.environ.get('RAPIDAPI_KEY')
    if not rapidapi_key:
        return {'success': False, 'error': 'missing_key', 'message': 'RAPIDAPI_KEY não configurada'}
    
    api = {
        'name': 'Instagram Scraper Stable API (ig_get_fb_profile_hover)',
        'host': 'instagram-scraper-stable-api.p.rapidapi.com',
        'url': 'https://instagram-scraper-stable-api.p.rapidapi.com/ig_get_fb_profile_hover.php',
        'param_name': 'Username_or_url'
    }
    
    try:
        print(f"🔍 Tentando API: {api['name']}")
        
        headers = {
            "x-rapidapi-key": rapidapi_key.strip(),
            "x-rapidapi-host": api['host']
        }
        
        querystring = {api['param_name']: username}
        
        response = requests.get(api['url'], headers=headers, params=querystring, timeout=15)
        
        print(f"📊 {api['name']} - Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            if 'user_data' in data and 'user_posts' in data:
                return {'success': True, 'data': data, 'method': api['name']}
            else:
                # Mesmo com status 200, a resposta pode não ser o que esperamos
                print(f"⚠️ {api['name']} - Resposta com estrutura inválida. JSON: {data}")
                return {'success': False, 'error': 'api_error', 'message': f"Resposta da API com estrutura inválida. JSON keys: {list(data.keys())}"}
        else:
            print(f"❌ {api['name']} - Status {response.status_code}, Resposta: {response.text}")
            return {'success': False, 'error': 'api_error', 'message': f"Status {response.status_code}: {response.text}"}
            
    except Exception as e:
        print(f"❌ Erro na API {api['name']}: {str(e)}")
        return {'success': False, 'error': 'exception', 'message': f'Erro na requisição: {str(e)}'}
        
def fetch_instagram_public_scraper(username):
    """Método 2: Scraper público via proxy (sem API key)"""
    
    try:
        print(f"🔍 Tentando scraper público para: {username}")
        
        # Simula um browser real
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        }
        
        # Usando endpoint público (sem garantias, mas às vezes funciona)
        public_apis = [
            f"https://www.instagram.com/{username}/?__a=1", # Isso pode ser bloqueado
            f"https://i.instagram.com/api/v1/users/web_profile_info/?username={username}", # Isso pode ser bloqueado
        ]
        
        for api_url in public_apis:
            try:
                print(f"🌐 Tentando endpoint público: {api_url}")
                response = requests.get(api_url, headers=headers, timeout=10)
                
                print(f"📊 Status: {response.status_code}")
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                        return {'success': True, 'data': data, 'method': 'public_scraper'}
                    except json.JSONDecodeError:
                        print("❌ Resposta não é JSON válido")
                        continue
                        
            except Exception as e:
                print(f"❌ Erro no endpoint público: {str(e)}")
                continue
        
        return {'success': False, 'error': 'public_blocked', 'message': 'Endpoints públicos bloqueados'}
        
    except Exception as e:
        return {'success': False, 'error': 'scraper_error', 'message': f'Erro no scraper: {str(e)}'}


def normalize_profile_data(api_data, username, method):
    """Normaliza os dados do perfil e extrai as URLs das postagens."""
    
    try:
        print(f"🔧 Normalizando dados do método: {method}")

        # --- INÍCIO DA MODIFICAÇÃO PARA TESTE ---

        # 1. Verificamos se a resposta é um dicionário antes de prosseguir
        if not isinstance(api_data, dict):
            print(f"❌ ERRO CRÍTICO: A resposta da API não é um dicionário. Resposta recebida: {api_data}")
            return None

        print(f"DEBUG: Chaves recebidas na normalização: {list(api_data.keys())}")

        user_data = api_data.get('user_data')
        
        if not user_data:
            print("❌ ERRO CRÍTICO: A chave 'user_data' não foi encontrada na resposta da API.")
            return None