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

def fetch_instagram_flashapi(username):
    """
    Método de busca para a FlashAPI (User Info by username).
    """
    rapidapi_key = os.environ.get('RAPIDAPI_KEY')
    if not rapidapi_key:
        return {'success': False, 'error': 'missing_key', 'message': 'RAPIDAPI_KEY não configurada'}

    # Detalhes da nova API
    api = {
        'name': 'FlashAPI (User Info by username)',
        'host': 'flashapi1.p.rapidapi.com',
        'url': 'https://flashapi1.p.rapidapi.com/ig/info_username',
        'param_name': 'user'
    }

    try:
        print(f"🔍 Tentando API: {api['name']}")
        
        headers = {
            "x-rapidapi-key": rapidapi_key.strip(),
            "x-rapidapi-host": api['host']
        }
        
        querystring = {api['param_name']: username, "nocors": "false"}
        
        response = requests.get(api['url'], headers=headers, params=querystring, timeout=15)
        
        print(f"📊 {api['name']} - Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            if 'user' in data and data.get('status') == 'ok':
                # Passamos o objeto inteiro para a normalização
                return {'success': True, 'data': data, 'method': api['name']}
            else:
                return {'success': False, 'error': 'api_error', 'message': f"Resposta da API com estrutura inválida. JSON: {data}"}
        else:
            print(f"❌ {api['name']} - Status {response.status_code}, Resposta: {response.text}")
            return {'success': False, 'error': 'api_error', 'message': f"Status {response.status_code}: {response.text}"}
            
    except Exception as e:
        print(f"❌ Erro na API {api['name']}: {str(e)}")
        return {'success': False, 'error': 'exception', 'message': f'Erro na requisição: {str(e)}'}

def normalize_profile_data(api_data, username, method):
    """
    Normaliza os dados do perfil para a estrutura da FlashAPI.
    """
    try:
        print(f"🔧 Normalizando dados do método: {method}")
        
        # A estrutura da FlashAPI tem os dados dentro da chave 'user'
        user_data = api_data.get('user')
        
        if not user_data:
            print("❌ Estrutura de dados de usuário não reconhecida. Chave 'user' não encontrada.")
            return None
        
        print(f"✅ User data encontrado - Primeiras chaves: {list(user_data.keys())[:5]}...")
        
        def get_field(field_names, default=''):
            for field in field_names:
                value = user_data.get(field)
                if value is not None:
                    return value
            return default
        
        def get_int_field(field_names, default=0):
            for field in field_names:
                value = user_data.get(field)
                if value is not None:
                    try:
                        return int(value)
                    except (ValueError, TypeError):
                        continue
            return default
        
        def get_bool_field(field_names, default=False):
            for field in field_names:
                value = user_data.get(field)
                if value is not None:
                    return bool(value)
            return default
        
        # Mapeando os campos da nova API. Alguns nomes podem precisar de ajuste
        # dependendo da resposta completa da FlashAPI.
        profile_data = {
            "username": get_field(['username']),
            "user_id": get_field(['pk', 'id']),
            "full_name": get_field(['full_name']),
            "biography": get_field(['biography']),
            "followers": get_int_field(['follower_count']),
            "following": get_int_field(['following_count']),
            "posts_count": get_int_field(['media_count']),
            "profile_pic_url": get_field(['profile_pic_url_hd', 'profile_pic_url']),
            "is_private": get_bool_field(['is_private']),
            "is_verified": get_bool_field(['is_verified']),
            "external_url": get_field(['external_url']),
            "cached": False,
            "timestamp": datetime.now().isoformat(),
            "api_source": method, # Usar o nome do método diretamente
            "data_keys_preview": list(user_data.keys())[:10]
        }
        
        # A API de 'info' geralmente não retorna posts, então retornamos uma lista vazia.
        profile_data['latest_posts_urls'] = []
        
        return profile_data
        
    except Exception as e:
        print(f"❌ Erro ao normalizar dados: {str(e)}")
        return None

@app.route('/instagram/<username>', methods=['GET'])
def get_instagram_profile(username):
    """Lógica principal para buscar perfil com a nova API"""
    try:
        username = username.replace('@', '').strip().lower()
        if not username:
            return jsonify({"error": "Username inválido"}), 400
        
        print(f"🎯 Buscando perfil: {username}")
        
        cached_data = get_cached_profile(username)
        if cached_data:
            print(f"💾 Cache hit para: {username}")
            return jsonify({**cached_data, "cached": True, "last_updated": datetime.now().isoformat()})
        
        rate_limit()
        
        # Usando a nova função como método principal
        result = fetch_instagram_flashapi(username)

        if not result or not result.get('success'):
            return jsonify({
                "error": "Falha ao buscar dados",
                "details": result.get('message', 'Erro desconhecido'),
                "timestamp": datetime.now().isoformat(),
                "suggestion": "Verifique sua chave RapidAPI ou tente novamente mais tarde"
            }), 502
        
        profile_data = normalize_profile_data(result['data'], username, result['method'])
        
        if not profile_data:
            return jsonify({"error": "Não foi possível processar os dados da API", "method_used": result['method'], "raw_response": result.get('data', 'Nenhuma resposta crua disponível.'), "timestamp": datetime.now().isoformat()}), 500
        
        cache_profile(username, profile_data)
        
        print(f"🎉 Perfil obtido com sucesso: {profile_data['username']} ({profile_data['api_source']})")
        return jsonify(profile_data)
        
    except Exception as e:
        print(f"💥 Erro interno no servidor: {str(e)}")
        return jsonify({"error": "Erro interno do servidor", "details": str(e), "timestamp": datetime.now().isoformat()}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Endpoint para verificar se a API está funcionando"""
    rapidapi_key = os.environ.get('RAPIDAPI_KEY')
    rapidapi_configured = bool(rapidapi_key)
    
    return jsonify({
        "status": "🟢 Online",
        "version": "7.0.0 - FlashAPI",
        "api_principal": "⚡ FlashAPI (User Info by username)",
        "rapidapi_configured": rapidapi_configured,
        "rapidapi_key_preview": f"{rapidapi_key[:5]}...{rapidapi_key[-4:]}" if rapidapi_key else "❌ Não configurada",
        "timestamp": datetime.now().isoformat(),
        "cache_size": len(cache)
    })

@app.route('/test/<username>', methods=['GET'])
def test_method(username):
    """Testa o método ativo (FlashAPI) para debug."""
    if not username:
        return jsonify({"error": "Username é obrigatório"}), 400
    
    username = username.replace('@', '').strip().lower()
    
    print(f"🧪 Testando FlashAPI para o usuário: {username}")
    result = fetch_instagram_flashapi(username)
    
    return jsonify({
        "username_testado": username,
        "resultado_fetch": result,
        "timestamp": datetime.now().isoformat()
    })

@app.route('/cache/clear', methods=['POST'])
def clear_cache():
    """Endpoint para limpar o cache"""
    global cache
    cache_size = len(cache)
    cache.clear()
    return jsonify({
        "message": f"Cache limpo com sucesso. {cache_size} entradas removidas.",
        "timestamp": datetime.now().isoformat()
    })

@app.route('/', methods=['GET'])
def index():
    """Página inicial com documentação da API"""
    return jsonify({
        "🚀 API": "Instagram Profile Scraper",
        "version": "7.0.0 - FlashAPI",
        "status": "Online",
        "api_source": "⚡ FlashAPI (User Info by username)",
        "endpoints": {
            "🎯 Perfil": "/instagram/{username}",
            "🧪 Debug": "/test/{username}",
            "❤️ Health": "/health",
            "🧹 Limpar Cache": "/cache/clear (método POST)"
        },
        "exemplo_uso": f"{request.url_root}instagram/nasa",
        "timestamp": datetime.now().isoformat()
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    app.run(host='0.0.0.0', port=port, debug=True)