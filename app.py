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
        
def normalize_profile_data(api_data, username, method):
    """Normaliza os dados do perfil e extrai as URLs das postagens."""
    
    try:
        print(f"🔧 Normalizando dados do método: {method}")
        
        user_data = api_data
        
        posts_data = api_data.get('edge_owner_to_timeline_media', {}).get('edges', [])
        
        if not user_data or 'full_name' not in user_data:
            print("❌ Estrutura de dados de usuário não reconhecida. Chave 'full_name' não encontrada no nível superior.")
            return None
        
        print(f"✅ User data encontrado - Keys: {list(user_data.keys())[:5]}...")
        print(f"✅ Posts data encontrado - Itens: {len(posts_data) if posts_data else 0}")
        
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
                        # Adaptação para a estrutura da API
                        if isinstance(value, dict) and 'count' in value:
                            return int(value['count'])
                        elif isinstance(value, dict) and 'edge_count' in value:
                            return int(value['edge_count'])
                        else:
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
        
        profile_data = {
            "username": get_field(['username', 'user_name', 'login'], username),
            "user_id": get_field(['pk', 'id']),
            "full_name": get_field(['full_name', 'fullName', 'display_name']),
            "biography": get_field(['biography', 'bio', 'description', 'about']),
            "followers": get_int_field(['follower_count', 'edge_followed_by']),
            "following": get_int_field(['following_count', 'edge_follow']),
            "posts_count": get_int_field(['media_count', 'edge_owner_to_timeline_media']),
            "profile_pic_url": get_field(['profile_pic_url']),
            "is_private": get_bool_field(['is_private', 'private', 'is_locked']),
            "is_verified": get_bool_field(['is_verified', 'verified']),
            "external_url": get_field(['external_url', 'website', 'url', 'link']),
            "cached": False,
            "timestamp": datetime.now().isoformat(),
            "api_source": f"RapidAPI-{method}",
            "data_keys": list(user_data.keys())[:10]
        }
        
        latest_posts_urls = []
        num_posts_to_get = 10
        
        for post_item in posts_data:
            if 'node' in post_item:
                node = post_item['node']
                url = None
                
                # Prioriza image_versions2 (para imagens/vídeos de posts)
                if 'image_versions2' in node and 'candidates' in node['image_versions2'] and node['image_versions2']['candidates']:
                    url = node['image_versions2']['candidates'][0]['url']
                elif 'video_versions' in node and 'candidates' in node['video_versions'] and node['video_versions']['candidates']:
                    url = node['video_versions']['candidates'][0]['url']
                elif 'display_url' in node: # fallback para URL de exibição, caso não haja versions2
                    url = node['display_url']
                elif 'shortcode' in node: # Outra opção: construir a URL do post
                    url = f"https://www.instagram.com/p/{node['shortcode']}/"

                if url and url not in latest_posts_urls:
                    latest_posts_urls.append(url)
                
                if len(latest_posts_urls) >= num_posts_to_get:
                    break
        
        profile_data['latest_posts_urls'] = latest_posts_urls
        
        return profile_data
        
    except Exception as e:
        print(f"❌ Erro ao normalizar dados: {str(e)}")
        return None

@app.route('/instagram/<username>', methods=['GET'])
def get_instagram_profile_original(username):
    """Lógica principal para buscar perfil"""
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
        
        methods = [
            ("Instagram Looter", fetch_instagram_looter),
            ("Public Scraper", fetch_instagram_public_scraper),
        ]
        
        result = None
        for method_name, method_func in methods:
            print(f"🚀 Tentando {method_name}...")
            result = method_func(username)
            
            if result and result.get('success'):
                print(f"✅ Sucesso com {method_name}!")
                break
            else:
                print(f"❌ {method_name} falhou: {result.get('message', 'Erro desconhecido')}")
                time.sleep(0.5)

        if not result or not result.get('success'):
            return jsonify({
                "error": "Todos os métodos falharam",
                "details": "Nenhuma fonte de dados funcionou",
                "timestamp": datetime.now().isoformat(),
                "suggestion": "Verifique sua chave RapidAPI e tente novamente mais tarde"
            }), 502
        
        profile_data = normalize_profile_data(result['data'], username, result['method'])
        
        if not profile_data:
            return jsonify({"error": "Não foi possível processar os dados", "method_used": result['method'], "raw_response": result['data'], "timestamp": datetime.now().isoformat()}), 500
        
        cache_profile(username, profile_data)
        
        print(f"🎉 Perfil obtido com sucesso: {profile_data['username']} ({profile_data['api_source']})")
        return jsonify(profile_data)
        
    except Exception as e:
        print(f"💥 Erro interno: {str(e)}")
        return jsonify({"error": "Erro interno do servidor", "details": str(e), "timestamp": datetime.now().isoformat()}), 500

@app.route('/api/profile', methods=['GET'])
def get_instagram_profile_api():
    """Endpoint alternativo com parâmetro query"""
    username = request.args.get('username')
    if not username:
        return jsonify({"error": "Parâmetro 'username' é obrigatório"}), 400
    return get_instagram_profile_internal(username)

def get_instagram_profile_internal(username):
    """Lógica auxiliar para evitar duplicação de código"""
    return get_instagram_profile_original(username)

@app.route('/health', methods=['GET'])
def health_check():
    """Endpoint para verificar se a API está funcionando"""
    rapidapi_key = os.environ.get('RAPIDAPI_KEY')
    rapidapi_configured = bool(rapidapi_key)
    
    return jsonify({
        "status": "🟢 Online",
        "rapidapi_configured": rapidapi_configured,
        "rapidapi_key_preview": f"{rapidapi_key[:10]}***{rapidapi_key[-5:]}" if rapidapi_key else "❌ Não configurada",
        "timestamp": datetime.now().isoformat(),
        "cache_size": len(cache),
        "version": "7.0.1 - Corrigido Instagram Looter",
        "methods": [
            "🌟 Instagram Looter",
            "🌐 Scraper público (backup)"
        ],
        "note": "Esta versão não utiliza dados mock, retornando erro se todas as fontes falharem."
    })

@app.route('/test/<username>', methods=['GET'])
def test_all_methods(username):
    """
    Testa todos os métodos para debug.
    """
    if not username:
        return jsonify({"error": "Username é obrigatório"}), 400
    
    username = username.replace('@', '').strip().lower()
    
    results = {}
    
    print("🧪 Testando Instagram Looter...")
    result1 = fetch_instagram_looter(username)
    profile_data1 = normalize_profile_data(result1.get('data'), username, result1.get('method'))
    results['instagram_looter'] = {
        'success': result1['success'],
        'error': result1.get('error', ''),
        'message': result1.get('message', ''),
        'method': result1.get('method', ''),
        'has_data': bool(result1.get('data')),
        'profile_data_extracted': bool(profile_data1),
        'posts_extracted': len(profile_data1.get('latest_posts_urls', [])) if profile_data1 else 0,
        'raw_response_keys': list(result1.get('data').keys()) if result1.get('data') else []
    }
    
    time.sleep(1)
    
    print("🧪 Testando Scraper Público...")
    result2 = fetch_instagram_public_scraper(username)
    profile_data2 = normalize_profile_data(result2.get('data'), username, result2.get('method'))
    results['public_scraper'] = {
        'success': result2['success'],
        'error': result2.get('error', ''),
        'message': result2.get('message', ''),
        'method': result2.get('method', ''),
        'has_data': bool(result2.get('data')),
        'profile_data_extracted': bool(profile_data2),
        'posts_extracted': len(profile_data2.get('latest_posts_urls', [])) if profile_data2 else 0
    }
    
    return jsonify({
        "username": username,
        "test_results": results,
        "timestamp": datetime.now().isoformat(),
        "summary": {
            "working_methods": sum(1 for r in results.values() if r['success']),
            "total_methods": len(results),
            "best_option": "instagram_looter" if results['instagram_looter']['success'] and results['instagram_looter']['profile_data_extracted'] else 
                          "public_scraper" if results['public_scraper']['success'] and results['public_scraper']['profile_data_extracted'] else 
                          "falha"
        }
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
        "title": "🛠️ Guia de Configuração - API Instagram 2025",
        "current_status": {
            "rapidapi_configured": bool(rapidapi_key),
            "key_preview": f"{rapidapi_key[:10]}...{rapidapi_key[-5:]}" if rapidapi_key else "❌ Não configurada"
        },
        "setup_steps": [
            "1. 🌐 Vá para rapidapi.com e crie uma conta",
            "2. 🔍 Procure por 'Instagram Looter'",
            "3. 📋 Subscribe no plano GRATUITO (Basic/Free tier)",
            "4. 📝 Copie sua X-RapidAPI-Key",
            "5. ⚙️ Railway: Vá no seu projeto, clique no serviço 'web', vá em 'Variables' → Adicione RAPIDAPI_KEY = sua_chave",
            "6. 🚀 Faça um commit e push para o GitHub do seu código atualizado. O Railway fará o deploy automático.",
            "7. ✅ Teste: /instagram/cristiano"
        ],
        "important_notes": [
            "⚠️ Esta versão tenta várias APIs, mas a RapidAPI é a primeira opção",
            "❌ Não há fallbacks para dados mock nesta versão, retornando erro se todas as fontes falharem."
        ],
        "test_endpoints": [
            "/instagram/cristiano - Teste completo",
            "/test/cristiano - Debug detalhado",
            "/health - Status geral"
        ],
        "timestamp": datetime.now().isoformat()
    })

@app.route('/', methods=['GET'])
def index():
    """Página inicial com documentação"""
    rapidapi_key = os.environ.get('RAPIDAPI_KEY')
    rapidapi_configured = bool(rapidapi_key)
    
    return jsonify({
        "🚀 API": "Instagram Profile Scraper - VERSÃO DE TESTE",
        "version": "7.0.1 - Corrigido Instagram Looter",
        "status": "✅ Funciona!" if rapidapi_configured else "⚠️ Configuração pendente",
        "guarantee": "🛡️ Dependente da sua chave RapidAPI - sem fallbacks",
        "endpoints": {
            "🎯 Principal": "/instagram/{username}",
            "📊 API Style": "/api/profile?username={username}",
            "🧪 Debug": "/test/{username}",
            "❤️ Health": "/health",
            "🧹 Cache": "/cache/clear (POST)",
            "⚙️ Setup": "/setup"
        },
        "data_sources": [
            "1. 🌟 Instagram Looter",
            "2. 🌐 Scraper público (backup)"
        ],
        "features": [
            "✅ Cache inteligente (5min)",
            "✅ Rate limiting",
            "✅ Dados reais (se a chave RapidAPI for válida)",
            "✅ Extrai URLs das últimas postagens"
        ],
        "next_step": "/setup" if not rapidapi_configured else "🎉 Funciona: /instagram/cristiano",
        "demo": f"{request.url_root}instagram/nasa",
        "timestamp": datetime.now().isoformat()
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    app.run(host='0.0.0.0', port=port, debug=True)
