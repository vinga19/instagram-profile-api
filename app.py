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

def fetch_instagram_looter(username):
    """
    Método de busca para a Instagram Looter API (Corrigido com a URL do cURL).
    """
    
    rapidapi_key = os.environ.get('RAPIDAPI_KEY')
    if not rapidapi_key:
        return {'success': False, 'error': 'missing_key', 'message': 'RAPIDAPI_KEY não configurada'}
    
    api = {
        'name': 'Instagram Looter',
        'host': 'instagram-looter2.p.rapidapi.com',
        'url': 'https://instagram-looter2.p.rapidapi.com/profile',
        'param_name': 'username'
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
            if 'full_name' in data and 'username' in data:
                return {'success': True, 'data': data, 'method': api['name']}
            else:
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
            'Accept': 'text/html,application/xhtml+xml,application/xm