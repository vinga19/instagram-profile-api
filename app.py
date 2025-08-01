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
MIN_DELAY = 1  # Segundos entre requisições

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
    """Busca perfil usando a API do RapidAPI que você mostrou"""
    
    rapidapi_key = os.environ.get('RAPIDAPI_KEY')
    if not rapidapi_key:
        return {'success': False, 'error': 'missing_key', 'message': 'RAPIDAPI_KEY não configurada'}
    
    # Usando a API que você mostrou na tela: instagram120.p.rapidapi.com
    url = "https://instagram120.p.rapidapi.com/user/info"
    
    querystring = {"username": username}
    
    headers = {
        "x-rapidapi-key": rapidapi_key.strip(),  # Remove espaços extras
        "x-rapidapi-host": "instagram120.p.rapidapi.com"
    }
    
    try:
        response = requests.get(url, headers=headers, params=querystring, timeout=15)
        
        print(f"RapidAPI Response Status: {response.status_code}")
        print(f"RapidAPI Response: {response.text[:500]}...")  # Log para debug
        
        if response.status_code == 200:
            data = response.json()
            return {'success': True, 'data': data}
        elif response.status_code == 429:
            return {'success': False, 'error': 'rate_limit', 'message': 'Rate limit excedido'}
        elif response.status_code == 401:
            return {'success': False, 'error': 'auth_error', 'message': 'Chave da API inválida'}
        elif response.status_code == 403:
            return {'success': False, 'error': 'forbidden', 'message': 'Acesso negado pela API'}
        else:
            return {'success': False, 'error': 'api_error', 'message': f'Status {response.status_code}: {response.text}'}
            
    except requests.exceptions.Timeout:
        return {'success': False, 'error': 'timeout', 'message': 'Timeout na requisição'}
    except requests.exceptions.RequestException as e:
        return {'success': False, 'error': 'connection_error', 'message': f'Erro de conexão: {str(e)}'}

def fetch_instagram_profile_alternative(username):
    """API alternativa usando outra URL"""
    
    rapidapi_key = os.environ.get('RAPIDAPI_KEY')
    if not rapidapi_key:
        return {'success': False, 'error': 'missing_key', 'message': 'RAPIDAPI_KEY não configurada'}
    
    # API alternativa
    url = "https://instagram-scraper-2022.p.rapidapi.com/ig/profile_info"
    
    querystring = {"username_or_id_or_url": username}
    
    headers = {
        "x-rapidapi-key": rapidapi_key.strip(),
        "x-rapidapi-host": "instagram-scraper-2022.p.rapidapi.com"
    }
    
    try:
        response = requests.get(url, headers=headers, params=querystring, timeout=15)
        
        print(f"Alternative API Status: {response.status_code}")
        print(f"Alternative API Response: {response.text[:500]}...")
        
        if response.status_code == 200:
            data = response.json()
            return {'success': True, 'data': data}
        else:
            return {'success': False, 'error': 'api_error', 'message': f'Status {response.status_code}'}
            
    except Exception as e:
        return {'success': False, 'error': 'connection_error', 'message': f'Erro: {str(e)}'}

def normalize_profile_data(api_data, username):
    """Normaliza os dados de diferentes APIs para um formato padrão"""
    
    try:
        # Tenta diferentes estruturas de dados
        user_data = None
        
        if isinstance(api_data, dict):
            # Estrutura 1: {user: {...}}
            if 'user' in api_data:
                user_data = api_data['user']
            # Estrutura 2: {data: {...}}
            elif 'data' in api_data:
                user_data = api_data['data']
            # Estrutura 3: dados diretos
            else:
                user_data = api_data
        
        if not user_data:
            return None
            
        # Extrai dados com múltiplas tentativas de nomes de campos
        profile_data = {
            "username": (
                user_data.get('username') or 
                user_data.get('user_name') or 
                username
            ),
            "full_name": (
                user_data.get('full_name') or 
                user_data.get('name') or 
                user_data.get('fullName') or 
                ''
            ),
            "biography": (
                user_data.get('biography') or 
                user_data.get('bio') or 
                user_data.get('description') or 
                ''
            ),
            "followers": int(
                user_data.get('follower_count') or 
                user_data.get('followers') or 
                user_data.get('followers_count') or 
                0
            ),
            "following": int(
                user_data.get('following_count') or 
                user_data.get('following') or 
                user_data.get('followings') or 
                0
            ),
            "posts_count": int(
                user_data.get('media_count') or 
                user_data.get('posts') or 
                user_data.get('posts_count') or 
                user_data.get('media') or 
                0
            ),
            "profile_pic_url": (
                user_data.get('profile_pic_url') or 
                user_data.get('profile_picture') or 
                user_data.get('avatar') or 
                ''
            ),
            "is_private": bool(
                user_data.get('is_private') or 
                user_data.get('private') or 
                False
            ),
            "is_verified": bool(
                user_data.get('is_verified') or 
                user_data.get('verified') or 
                False
            ),
            "external_url": (
                user_data.get('external_url') or 
                user_data.get('website') or 
                user_data.get('url') or 
                ''
            ),
            "cached": False,
            "timestamp": datetime.now().isoformat(),
            "api_source": "RapidAPI"
        }
        
        return profile_data
        
    except Exception as e:
        print(f"Erro ao normalizar dados: {str(e)}")
        return None

# ENDPOINT PRINCIPAL - MANTÉM O FORMATO ORIGINAL
@app.route('/instagram/<username>', methods=['GET'])
def get_instagram_profile_original(username):
    """Endpoint original que você estava usando"""
    return get_instagram_profile_internal(username)

# ENDPOINT ALTERNATIVO
@app.route('/api/profile', methods=['GET'])
def get_instagram_profile_api():
    """Endpoint alternativo com parâmetro query"""
    username = request.args.get('username')
    if not username:
        return jsonify({"error": "Parâmetro 'username' é obrigatório"}), 400
    return get_instagram_profile_internal(username)

def get_instagram_profile_internal(username):
    """Lógica principal para buscar perfil"""
    try:
        # Remove @ se houver
        username = username.replace('@', '').strip().lower()
        
        if not username:
            return jsonify({"error": "Username inválido"}), 400
        
        # Verifica cache primeiro
        cached_data = get_cached_profile(username)
        if cached_data:
            return jsonify({
                **cached_data,
                "cached": True,
                "last_updated": datetime.now().isoformat()
            })
        
        # Rate limiting
        rate_limit()
        
        # Busca o perfil via RapidAPI
        result = fetch_instagram_profile_rapidapi(username)
        
        # Se a primeira API falhar, tenta a alternativa
        if not result['success']:
            print(f"Primeira API falhou: {result.get('message', 'Erro desconhecido')}")
            time.sleep(1)
            result = fetch_instagram_profile_alternative(username)
        
        if not result['success']:
            error_responses = {
                'missing_key': ("Chave da API não configurada", 503),
                'rate_limit': ("Rate limit excedido - tente novamente em alguns minutos", 429),
                'auth_error': ("Chave da API inválida ou expirada", 401),
                'forbidden': ("Acesso negado pela API", 403),
                'timeout': ("Timeout na requisição", 504),
                'connection_error': ("Erro de conexão com a API", 502),
                'api_error': ("Erro na API externa", 502)
            }
            
            error_msg, status_code = error_responses.get(
                result['error'], 
                ("Erro desconhecido", 500)
            )
            
            return jsonify({
                "error": error_msg,
                "details": result.get('message', ''),
                "timestamp": datetime.now().isoformat()
            }), status_code
        
        # Normaliza os dados
        profile_data = normalize_profile_data(result['data'], username)
        
        if not profile_data:
            return jsonify({
                "error": "Não foi possível processar os dados da API",
                "raw_response": result['data'],
                "timestamp": datetime.now().isoformat()
            }), 500
        
        # Salva no cache
        cache_profile(username, profile_data)
        
        return jsonify(profile_data)
        
    except Exception as e:
        print(f"Erro interno: {str(e)}")
        return jsonify({
            "error": "Erro interno do servidor",
            "details": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Endpoint para verificar se a API está funcionando"""
    rapidapi_key = os.environ.get('RAPIDAPI_KEY')
    rapidapi_configured = bool(rapidapi_key)
    
    return jsonify({
        "status": "online",
        "rapidapi_configured": rapidapi_configured,
        "rapidapi_key_preview": f"{rapidapi_key[:10]}..." if rapidapi_key else "Not configured",
        "timestamp": datetime.now().isoformat(),
        "cache_size": len(cache),
        "version": "2.1.0 - RapidAPI Fixed"
    })

@app.route('/cache/clear', methods=['POST'])
def clear_cache():
    """Endpoint para limpar o cache"""
    global cache
    cache_size = len(cache)
    cache.clear()
    return jsonify({
        "message": f"Cache limpo - {cache_size} entradas removidas",
        "timestamp": datetime.now().isoformat()
    })

@app.route('/setup', methods=['GET'])
def setup_guide():
    """Guia de configuração da API"""
    rapidapi_key = os.environ.get('RAPIDAPI_KEY')
    
    return jsonify({
        "title": "🔧 Configuração da API Instagram",
        "current_status": {
            "rapidapi_configured": bool(rapidapi_key),
            "key_preview": f"{rapidapi_key[:15]}..." if rapidapi_key else "❌ Não configurada"
        },
        "steps": [
            "1. 📝 Crie conta no RapidAPI.com",
            "2. 🔍 Procure por 'Instagram120' ou 'Instagram Profile'",
            "3. 📋 Copie sua X-RapidAPI-Key",
            "4. ⚙️ No Railway: Variables → Add → RAPIDAPI_KEY = sua_chave",
            "5. 🚀 Redeploy automático",
            "6. ✅ Teste: /instagram/cristiano"
        ],
        "test_endpoints": [
            "/instagram/cristiano - Formato original",
            "/api/profile?username=nasa - Formato alternativo",
            "/health - Status da API"
        ],
        "recommended_apis": [
            "instagram120.p.rapidapi.com (principal)",
            "instagram-scraper-2022.p.rapidapi.com (backup)"
        ],
        "timestamp": datetime.now().isoformat()
    })

@app.route('/', methods=['GET'])
def index():
    """Página inicial com documentação"""
    rapidapi_key = os.environ.get('RAPIDAPI_KEY')
    rapidapi_configured = bool(rapidapi_key)
    
    return jsonify({
        "🚀 API": "Instagram Profile Scraper",
        "version": "2.1.0 - RapidAPI Integration",
        "status": "✅ Online" if rapidapi_configured else "⚠️ Configuração pendente",
        "endpoints": {
            "🎯 Principal": "/instagram/{username}",
            "📊 Alternativo": "/api/profile?username={username}",
            "❤️ Health": "/health",
            "🧹 Cache": "/cache/clear (POST)",
            "⚙️ Setup": "/setup"
        },
        "features": [
            "✅ RapidAPI integration",
            "✅ Dual API fallback", 
            "✅ Smart caching (5min)",
            "✅ Rate limiting",
            "✅ Error handling",
            "✅ Response normalization"
        ],
        "next_step": "/setup" if not rapidapi_configured else "🎉 Pronto para usar!",
        "example": f"{request.url_root}instagram/cristiano",
        "timestamp": datetime.now().isoformat()
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    app.run(host='0.0.0.0', port=port, debug=True)