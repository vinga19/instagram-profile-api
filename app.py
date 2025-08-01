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
    """Método 1: Procura APIs gratuitas no RapidAPI que realmente funcionam"""
    
    rapidapi_key = os.environ.get('RAPIDAPI_KEY')
    if not rapidapi_key:
        return {'success': False, 'error': 'missing_key', 'message': 'RAPIDAPI_KEY não configurada'}
    
    # Lista de APIs realmente gratuitas e funcionais (2025)
    # AJUSTADO para priorizar o "Instagram Scraper Stable API" com o endpoint "Basic User + Posts"
    free_apis = [
        {
            'name': 'Instagram Scraper Stable API (Basic User + Posts)',
            'host': 'instagram-scraper-stable-api.p.rapidapi.com',
            'url': 'https://instagram-scraper-stable-api.p.rapidapi.com/basic-user-posts',
            'param_name': 'username_or_url' # Conforme a imagem image_3a0a4c.png
        },
        {
            'name': 'Instagram Looter',
            'host': 'instagram-looter.p.rapidapi.com',
            'url': 'https://instagram-looter.p.rapidapi.com/user',
            'param_name': 'username'
        },
        {
            'name': 'FlashAPI Instagram',
            'host': 'flashapi.p.rapidapi.com',
            'url': 'https://flashapi.p.rapidapi.com/instagram/profile',
            'param_name': 'username'
        },
        {
            'name': 'Mediafy API',
            'host': 'mediafy-api.p.rapidapi.com',
            'url': 'https://mediafy-api.p.rapidapi.com/instagram/profile',
            'param_name': 'username'
        }
    ]
    
    for api in free_apis:
        try:
            print(f"🔍 Tentando API gratuita: {api['name']}")
            
            headers = {
                "x-rapidapi-key": rapidapi_key.strip(),
                "x-rapidapi-host": api['host']
            }
            
            querystring = {api['param_name']: username}
            
            response = requests.get(api['url'], headers=headers, params=querystring, timeout=15)
            
            print(f"📊 {api['name']} - Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                return {'success': True, 'data': data, 'method': api['name']}
            elif response.status_code == 401:
                print(f"❌ {api['name']} - Chave inválida ou endpoint não acessível")
            elif response.status_code == 403:
                print(f"❌ {api['name']} - Endpoint bloqueado no plano atual")
            else:
                print(f"❌ {api['name']} - Status {response.status_code}")
                
        except Exception as e:
            print(f"❌ Erro na API {api['name']}: {str(e)}")
            continue
    
    return {'success': False, 'error': 'no_free_apis', 'message': 'Nenhuma API gratuita funcionou'}

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

def fetch_instagram_mock_data(username):
    """Método 3: Dados mock para demonstração (quando nada mais funciona)"""
    
    print(f"🎭 Gerando dados mock para: {username}")
    
    # Lista de usuários famosos com dados aproximados (para demonstração)
    mock_profiles = {
        "cristiano": {
            "username": "cristiano",
            "full_name": "Cristiano Ronaldo",
            "biography": "Footballer @manchesterunited⚽️",
            "followers": 500000000,
            "following": 500,
            "posts_count": 3200,
            "is_verified": True,
            "is_private": False,
            "latest_posts_urls": [
                "https://mock-image.com/cristiano_post1.jpg",
                "https://mock-image.com/cristiano_post2.jpg",
                "https://mock-image.com/cristiano_post3.jpg"
            ]
        },
        "nasa": {
            "username": "nasa",
            "full_name": "NASA",
            "biography": "🚀 Exploring the universe and our home planet Earth",
            "followers": 70000000,
            "following": 70,
            "posts_count": 4500,
            "is_verified": True,
            "is_private": False,
            "latest_posts_urls": [
                "https://mock-image.com/nasa_post1.jpg",
                "https://mock-image.com/nasa_post2.jpg"
            ]
        },
        "instagram": {
            "username": "instagram",
            "full_name": "Instagram",
            "biography": "Bringing you closer to the people and things you love ❤️",
            "followers": 600000000,
            "following": 0,
            "posts_count": 7000,
            "is_verified": True,
            "is_private": False,
            "latest_posts_urls": [
                "https://mock-image.com/instagram_post1.jpg"
            ]
        }
    }
    
    if username.lower() in mock_profiles:
        mock_data = mock_profiles[username.lower()]
        return {'success': True, 'data': mock_data, 'method': 'mock_data'}
    else:
        # Gera dados genéricos para qualquer usuário
        mock_data = {
            "username": username,
            "full_name": f"User {username.title()}",
            "biography": "Profile demonstration (mock data)",
            "followers": random.randint(100, 50000),
            "following": random.randint(50, 1000),
            "posts_count": random.randint(10, 500),
            "is_verified": False,
            "is_private": random.choice([True, False]),
            "latest_posts_urls": [
                f"https://mock-image.com/{username}_post_generic1.jpg",
                f"https://mock-image.com/{username}_post_generic2.jpg"
            ]
        }
        return {'success': True, 'data': mock_data, 'method': 'mock_data'}

def normalize_profile_data(api_data, username, method):
    """Normaliza os dados de diferentes APIs e métodos, incluindo URLs das postagens."""
    
    try:
        print(f"🔧 Normalizando dados do método: {method}")
        
        # Se já são dados mock, usa diretamente
        if method == 'mock_data':
            profile_data = {
                **api_data,
                "profile_pic_url": api_data.get("profile_pic_url", f"https://via.placeholder.com/150x150?text={username[0].upper()}"),
                "external_url": api_data.get("external_url", ""),
                "cached": False,
                "timestamp": datetime.now().isoformat(),
                "api_source": "Mock Data (demonstração)",
                "note": "⚠️ Dados de demonstração - configure uma chave RapidAPI válida para dados reais"
            }
            return profile_data
        
        # Para APIs reais, tenta extrair dados
        user_data = None
        posts_data = [] # Lista para armazenar dados das postagens
        
        if isinstance(api_data, dict):
            # Para a "Instagram Scraper Stable API (Basic User + Posts)", o perfil está em 'user_data'
            user_data = api_data.get('user_data')
            # E as postagens estão em 'user_posts'
            posts_data = api_data.get('user_posts', [])

            # Fallback para outras estruturas caso venha de outra API que não a Instagram Scraper Stable
            if not user_data:
                possible_user_paths = [
                    api_data.get('user'),
                    api_data.get('data'),
                    api_data.get('profile'),
                    api_data.get('graphql', {}).get('user'),
                    api_data
                ]
                for data_path in possible_user_paths:
                    if data_path and isinstance(data_path, dict):
                        user_data = data_path
                        break
            
            if not posts_data: # Se 'user_posts' não foi encontrado, tenta outros caminhos para posts
                possible_posts_paths = [
                    api_data.get('media', {}).get('data'),
                    api_data.get('posts'),
                    (user_data.get('edge_owner_to_timeline_media', {}) if user_data else {}).get('edges'),
                    api_data.get('items')
                ]
                for posts_path in possible_posts_paths:
                    if isinstance(posts_path, list):
                        posts_data = posts_path
                        break
                    elif isinstance(posts_path, dict) and 'data' in posts_path and isinstance(posts_path['data'], list):
                        posts_data = posts_path['data']
                        break
        
        if not user_data:
            print("❌ Estrutura de dados de usuário não reconhecida")
            return None
        
        print(f"✅ User data encontrado - Keys: {list(user_data.keys())[:5]}...")
        print(f"✅ Posts data encontrado - Itens: {len(posts_data) if posts_data else 0}")
        
        # Extrai campos do perfil com múltiplas tentativas
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
                        # Extrai 'count' se for um dicionário como {'count': X}
                        if isinstance(value, dict) and 'count' in value:
                            return int(value['count'])
                        # Extrai 'count' se for um dicionário como {'edges': [], 'count': X}
                        elif isinstance(value, dict) and 'edge_count' in value:
                            return int(value['edge_count'])
                        elif isinstance(value, dict) and 'data' in value and 'count' in value['data']:
                            return int(value['data']['count'])
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
            "username": get_field(['username', 'user_name', 'login', 'name'], username),
            "user_id": get_field(['pk', 'id']), # Tenta pegar o user_id numérico
            "full_name": get_field(['full_name', 'fullName', 'display_name']),
            "biography": get_field(['biography', 'bio', 'description', 'about']),
            "followers": get_int_field(['follower_count', 'followers', 'followers_count', 'edge_followed_by']),
            "following": get_int_field(['following_count', 'following', 'followings', 'edge_follow']),
            "posts_count": get_int_field(['media_count', 'posts', 'posts_count', 'edge_owner_to_timeline_media']),
            "profile_pic_url": get_field(['profile_pic_url', 'profile_picture', 'avatar', 'profile_image', 'picture']),
            "is_private": get_bool_field(['is_private', 'private', 'is_locked']),
            "is_verified": get_bool_field(['is_verified', 'verified', 'is_blue_verified']),
            "external_url": get_field(['external_url', 'website', 'url', 'link']),
            "cached": False,
            "timestamp": datetime.now().isoformat(),
            "api_source": f"RapidAPI-{method}",
            "data_keys": list(user_data.keys())[:10]  # Primeiras 10 chaves para debug
        }
        
        # === Extração das URLs das últimas postagens com base no JSON fornecido ===
        latest_posts_urls = []
        num_posts_to_get = 10 # Limite para 10 postagens, conforme sua necessidade
        
        # O JSON mostra que as postagens estão em 'user_posts', e a URL de imagem em 'node' -> 'image_versions2' -> 'candidates' -> [0] -> 'url'
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

                if url and url not in latest_posts_urls: # Evitar duplicatas
                    latest_posts_urls.append(url)
                
                if len(latest_posts_urls) >= num_posts_to_get:
                    break # Parar quando tiver o número desejado de posts
        
        profile_data['latest_posts_urls'] = latest_posts_urls
        # ==========================================================
        
        return profile_data
        
    except Exception as e:
        print(f"❌ Erro ao normalizar dados: {str(e)}")
        # Para debug, você pode querer incluir o raw_response aqui
        return None

@app.route('/instagram/<username>', methods=['GET'])
def get_instagram_profile_original(username):
    """Endpoint original que você estava usando"""
    return get_instagram_profile_internal(username)

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
        
        print(f"🎯 Buscando perfil: {username}")
        
        # Verifica cache primeiro
        cached_data = get_cached_profile(username)
        if cached_data:
            print(f"💾 Cache hit para: {username}")
            return jsonify({
                **cached_data,
                "cached": True,
                "last_updated": datetime.now().isoformat()
            })
        
        # Rate limiting
        rate_limit()
        
        # Tenta diferentes métodos sequencialmente
        methods = [
            ("RapidAPI Free", fetch_instagram_rapidapi_free),
            ("Public Scraper", fetch_instagram_public_scraper),
            ("Mock Data", fetch_instagram_mock_data)  # Sempre funciona como fallback
        ]
        
        result = None
        for method_name, method_func in methods:
            print(f"🚀 Tentando {method_name}...")
            result = method_func(username)
            
            if result['success']:
                print(f"✅ Sucesso com {method_name}!")
                break
            else:
                print(f"❌ {method_name} falhou: {result.get('message', 'Erro desconhecido')}")
                time.sleep(0.5)
        
        if not result or not result['success']:
            return jsonify({
                "error": "Todos os métodos falharam",
                "details": "Nenhuma fonte de dados funcionou",
                "timestamp": datetime.now().isoformat(),
                "suggestion": "Verifique sua chave RapidAPI ou tente novamente mais tarde"
            }), 502
        
        # Normaliza os dados
        profile_data = normalize_profile_data(result['data'], username, result.get('method', 'unknown'))
        
        if not profile_data:
            return jsonify({
                "error": "Não foi possível processar os dados",
                "method_used": result.get('method', 'unknown'),
                "raw_response": result['data'],
                "timestamp": datetime.now().isoformat()
            }), 500
        
        # Salva no cache
        cache_profile(username, profile_data)
        
        print(f"🎉 Perfil obtido com sucesso: {profile_data['username']} ({profile_data['api_source']})")
        return jsonify(profile_data)
        
    except Exception as e:
        print(f"💥 Erro interno: {str(e)}")
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
        "status": "🟢 Online",
        "rapidapi_configured": rapidapi_configured,
        "rapidapi_key_preview": f"{rapidapi_key[:10]}***{rapidapi_key[-5:]}" if rapidapi_key else "❌ Não configurada",
        "timestamp": datetime.now().isoformat(),
        "cache_size": len(cache),
        "version": "4.2.0 - Posts Extraídos do Scraper Stable API", # Versão atualizada
        "methods": [
            "🌟 Instagram Scraper Stable API (Basic User + Posts)",
            "📱 Instagram Looter", 
            "⚡ FlashAPI",
            "🎬 Mediafy API",
            "🌐 Scraper público (backup)",
            "🎭 Mock data (demonstração)"
        ],
        "note": "Sempre retorna dados - reais se possível, mock como fallback"
    })

@app.route('/test/<username>', methods=['GET'])
def test_all_methods(username):
    """Testa todos os métodos para debug"""
    if not username:
        return jsonify({"error": "Username é obrigatório"}), 400
    
    username = username.replace('@', '').strip().lower()
    
    results = {}
    
    # Testa RapidAPI Free
    print("🧪 Testando RapidAPI Free...")
    result1 = fetch_instagram_rapidapi_free(username)
    profile_data1 = normalize_profile_data(result1.get('data'), username, result1.get('method'))
    results['rapidapi_free'] = {
        'success': result1['success'],
        'error': result1.get('error', ''),
        'message': result1.get('message', ''),
        'method': result1.get('method', ''),
        'has_data': bool(result1.get('data')),
        'profile_data_extracted': bool(profile_data1),
        'posts_extracted': len(profile_data1.get('latest_posts_urls', [])) if profile_data1 else 0
    }
    
    time.sleep(1)
    
    # Testa Scraper Público
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
    
    # Testa Mock Data (sempre funciona)
    print("🧪 Testando Mock Data...")
    result3 = fetch_instagram_mock_data(username)
    profile_data3 = normalize_profile_data(result3.get('data'), username, result3.get('method'))
    results['mock_data'] = {
        'success': result3['success'],
        'method': result3.get('method', ''),
        'has_data': bool(result3.get('data')),
        'profile_data_extracted': bool(profile_data3),
        'posts_extracted': len(profile_data3.get('latest_posts_urls', [])) if profile_data3 else 0
    }
    
    return jsonify({
        "username": username,
        "test_results": results,
        "timestamp": datetime.now().isoformat(),
        "summary": {
            "working_methods": sum(1 for r in results.values() if r['success']),
            "total_methods": len(results),
            "best_option": "rapidapi_free" if results['rapidapi_free']['success'] and results['rapidapi_free']['profile_data_extracted'] else 
                          "public_scraper" if results['public_scraper']['success'] and results['public_scraper']['profile_data_extracted'] else 
                          "mock_data"
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
            "key_preview": f"{rapidapi_key[:10]}...{rapidapi_key[-5:]}" if rapidapi_key else "❌ Não configurada",
            "fallback_available": "✅ Sim - dados mock sempre disponíveis"
        },
        "setup_steps": [
            "1. 🌐 Vá para rapidapi.com e crie uma conta",
            "2. 🔍 Procure por 'Instagram Scraper Stable API'",
            "3. 📋 Subscribe no plano GRATUITO (Basic/Free tier)",
            "4. 📝 Copie sua X-RapidAPI-Key",
            "5. ⚙️ Railway: Vá no seu projeto, clique no serviço 'web', vá em 'Variables' → Adicione RAPIDAPI_KEY = sua_chave",
            "6. 🚀 Faça um commit e push para o GitHub do seu código atualizado. O Railway fará o deploy automático.",
            "7. ✅ Teste: /instagram/cristiano"
        ],
        "important_notes": [
            "⚠️ Muitas APIs do RapidAPI têm endpoints bloqueados no plano gratuito",
            "✅ Esta versão usa FALLBACK - sempre retorna dados",
            "🎭 Se nenhuma API funcionar, usa dados de demonstração",
            "🔄 Testa múltiplas fontes automaticamente",
            "✨ Agora extrai URLs das últimas postagens da 'Instagram Scraper Stable API'"
        ],
        "test_endpoints": [
            "/instagram/cristiano - Teste completo (deve incluir 'latest_posts_urls')",
            "/test/cristiano - Debug detalhado (deve indicar sucesso da RapidAPI e posts extraídos)",
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
        "🚀 API": "Instagram Profile Scraper Híbrida",
        "version": "4.2.0 - Posts Extraídos do Scraper Stable API", # Versão atualizada
        "status": "✅ Sempre funciona!" if True else "⚠️ Configuração pendente",
        "guarantee": "🛡️ SEMPRE retorna dados - reais ou demonstração",
        "endpoints": {
            "🎯 Principal": "/instagram/{username}",
            "📊 API Style": "/api/profile?username={username}",
            "🧪 Debug": "/test/{username}",
            "❤️ Health": "/health",
            "🧹 Cache": "/cache/clear (POST)",
            "⚙️ Setup": "/setup"
        },
        "data_sources": [
            "1. 🌟 RapidAPI (APIs gratuitas reais) - se configurado",
            "2. 🌐 Scraper público (backup)",
            "3. 🎭 Mock data (demonstração) - sempre funciona"
        ],
        "features": [
            "✅ Fallback em camadas (nunca falha)",
            "✅ Cache inteligente (5min)",
            "✅ Rate limiting",
            "✅ Dados reais quando possível",
            "✅ Mock data como backup",
            "✅ Debug completo",
            "✅ Extrai URLs das últimas postagens da Instagram Scraper Stable API" # Nova feature
        ],
        "next_step": "/setup" if not rapidapi_configured else "🎉 Funciona: /instagram/cristiano",
        "demo": f"{request.url_root}instagram/nasa",
        "timestamp": datetime.now().isoformat()
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    app.run(host='0.0.0.0', port=port, debug=True)
