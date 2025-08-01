from flask import Flask, request, jsonify
import requests
import time
import random
from datetime import datetime, timedelta
import os

app = Flask(__name__)

# Cache simples para evitar requisições repetidas
cache = {}
CACHE_DURATION = 300  # 5 minutos

# Controle de rate limiting
last_request_time = 0
MIN_DELAY = 1  # Segundos entre requisições (reduzido para APIs externas)

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

def fetch_instagram_profile_rapidapi(username):
    """Busca perfil usando RapidAPI Instagram API"""
    
    # Configurações da API (você precisará configurar essas variáveis no Railway)
    rapidapi_key = os.environ.get('RAPIDAPI_KEY', 'SUA_CHAVE_AQUI')
    
    # Opção 1: Instagram Profile API
    url = "https://instagram-scraper-2022.p.rapidapi.com/ig/profile_info"
    
    querystring = {"username_or_id_or_url": username}
    
    headers = {
        "x-rapidapi-key": rapidapi_key,
        "x-rapidapi-host": "instagram-scraper-2022.p.rapidapi.com"
    }
    
    try:
        response = requests.get(url, headers=headers, params=querystring, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            return {'success': True, 'data': data}
        elif response.status_code == 429:
            return {'success': False, 'error': 'rate_limit', 'message': 'API rate limit exceeded'}
        elif response.status_code == 401:
            return {'success': False, 'error': 'auth_error', 'message': 'API key inválida ou expirada'}
        else:
            return {'success': False, 'error': 'api_error', 'message': f'API retornou status {response.status_code}'}
            
    except requests.exceptions.Timeout:
        return {'success': False, 'error': 'timeout', 'message': 'Timeout na requisição para a API'}
    except requests.exceptions.RequestException as e:
        return {'success': False, 'error': 'connection_error', 'message': f'Erro de conexão: {str(e)}'}

def fetch_instagram_profile_alternative(username):
    """API alternativa caso a primeira falhe"""
    
    rapidapi_key = os.environ.get('RAPIDAPI_KEY', 'SUA_CHAVE_AQUI')
    
    # Opção 2: Instagram API alternativa
    url = "https://instagram120.p.rapidapi.com/user/info"
    
    querystring = {"username": username}
    
    headers = {
        "x-rapidapi-key": rapidapi_key,
        "x-rapidapi-host": "instagram120.p.rapidapi.com"
    }
    
    try:
        response = requests.get(url, headers=headers, params=querystring, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            return {'success': True, 'data': data}
        else:
            return {'success': False, 'error': 'api_error', 'message': f'API retornou status {response.status_code}'}
            
    except Exception as e:
        return {'success': False, 'error': 'connection_error', 'message': f'Erro: {str(e)}'}

@app.route('/api/profile', methods=['GET'])
def get_instagram_profile():
    try:
        # Validação do parâmetro
        username = request.args.get('username')
        if not username:
            return jsonify({"error": "Parâmetro 'username' é obrigatório"}), 400
        
        # Remove @ se houver
        username = username.replace('@', '').strip().lower()
        
        # Verifica cache primeiro
        cached_data = get_cached_profile(username)
        if cached_data:
            return jsonify({
                **cached_data,
                "cached": True,
                "timestamp": datetime.now().isoformat()
            })
        
        # Rate limiting
        rate_limit()
        
        # Busca o perfil via RapidAPI
        result = fetch_instagram_profile_rapidapi(username)
        
        # Se a primeira API falhar, tenta a alternativa
        if not result['success']:
            time.sleep(1)  # Pequeno delay antes de tentar a alternativa
            result = fetch_instagram_profile_alternative(username)
        
        if not result['success']:
            error_messages = {
                'rate_limit': {
                    'error': 'Rate limit da API excedido',
                    'suggestion': 'Aguarde alguns minutos antes de tentar novamente',
                    'retry_after': 300
                },
                'auth_error': {
                    'error': 'Erro de autenticação da API',
                    'suggestion': 'Chave da API pode estar inválida ou expirada'
                },
                'api_error': {
                    'error': 'Erro na API externa',
                    'suggestion': 'Tente novamente em alguns instantes'
                },
                'timeout': {
                    'error': 'Timeout na requisição',
                    'suggestion': 'A API externa demorou para responder'
                },
                'connection_error': {
                    'error': 'Erro de conexão',
                    'suggestion': 'Problema de conectividade com a API externa'
                }
            }
            
            error_info = error_messages.get(result['error'], {
                'error': 'Erro desconhecido',
                'suggestion': 'Tente novamente mais tarde'
            })
            
            return jsonify({
                **error_info,
                'details': result['message'],
                'timestamp': datetime.now().isoformat()
            }), 503
        
        # Processa os dados retornados
        api_data = result['data']
        
        # Normaliza os dados (diferentes APIs podem ter estruturas diferentes)
        try:
            # Tenta extrair dados da estrutura mais comum
            if 'user' in api_data:
                user_data = api_data['user']
            elif 'data' in api_data:
                user_data = api_data['data']
            else:
                user_data = api_data
            
            profile_data = {
                "username": user_data.get('username', username),
                "full_name": user_data.get('full_name') or user_data.get('name', ''),
                "biography": user_data.get('biography') or user_data.get('bio', ''),
                "followers": user_data.get('follower_count') or user_data.get('followers', 0),
                "following": user_data.get('following_count') or user_data.get('following', 0),
                "posts_count": user_data.get('media_count') or user_data.get('posts', 0),
                "profile_pic_url": user_data.get('profile_pic_url') or user_data.get('profile_picture', ''),
                "is_private": user_data.get('is_private', False),
                "is_verified": user_data.get('is_verified', False),
                "external_url": user_data.get('external_url', ''),
                "cached": False,
                "timestamp": datetime.now().isoformat(),
                "api_source": "RapidAPI"
            }
            
            # Salva no cache
            cache_profile(username, profile_data)
            
            return jsonify(profile_data)
            
        except KeyError as e:
            return jsonify({
                "error": "Erro ao processar dados da API",
                "details": f"Campo não encontrado: {str(e)}",
                "raw_data": api_data,
                "timestamp": datetime.now().isoformat()
            }), 500
            
    except Exception as e:
        return jsonify({
            "error": "Erro interno do servidor",
            "details": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Endpoint para verificar se a API está funcionando"""
    rapidapi_configured = bool(os.environ.get('RAPIDAPI_KEY'))
    
    return jsonify({
        "status": "online",
        "rapidapi_configured": rapidapi_configured,
        "timestamp": datetime.now().isoformat(),
        "cache_size": len(cache),
        "version": "2.0.0 - RapidAPI"
    })

@app.route('/api/cache/clear', methods=['POST'])
def clear_cache():
    """Endpoint para limpar o cache"""
    global cache
    cache.clear()
    return jsonify({
        "message": "Cache limpo com sucesso",
        "timestamp": datetime.now().isoformat()
    })

@app.route('/setup', methods=['GET'])
def setup_guide():
    """Guia de configuração da API"""
    return jsonify({
        "title": "Configuração da API Instagram",
        "steps": [
            "1. Crie uma conta no RapidAPI.com",
            "2. Inscreva-se em uma API do Instagram (muitas têm plano gratuito)",
            "3. Copie sua chave da API (X-RapidAPI-Key)",
            "4. No Railway, vá em Variables e adicione: RAPIDAPI_KEY = sua_chave",
            "5. Faça redeploy da aplicação",
            "6. Teste com: /api/profile?username=instagram"
        ],
        "recommended_apis": [
            "Instagram Scraper 2022",
            "Instagram120", 
            "Instagram Profile Data"
        ],
        "free_limits": "A maioria oferece 100-1000 requisições gratuitas por mês",
        "timestamp": datetime.now().isoformat()
    })

@app.route('/', methods=['GET'])
def index():
    """Página inicial com documentação"""
    rapidapi_configured = bool(os.environ.get('RAPIDAPI_KEY'))
    
    return jsonify({
        "message": "API Instagram Profile - RapidAPI Version",
        "version": "2.0.0",
        "rapidapi_configured": rapidapi_configured,
        "endpoints": {
            "profile": "/api/profile?username=USUARIO",
            "health": "/api/health",
            "clear_cache": "/api/cache/clear (POST)",
            "setup": "/setup"
        },
        "features": [
            "RapidAPI integration (no blocks!)",
            "Fallback to alternative APIs",
            "Request caching (5 min)", 
            "Rate limiting protection",
            "Better error handling"
        ],
        "setup_required": not rapidapi_configured,
        "next_step": "/setup" if not rapidapi_configured else "Ready to use!",
        "timestamp": datetime.now().isoformat()
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    app.run(host='0.0.0.0', port=port, debug=False)