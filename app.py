from flask import Flask, request, jsonify
import instaloader
import time
import random
import requests
from datetime import datetime, timedelta
import os

app = Flask(__name__)

# Cache simples para evitar requisições repetidas
cache = {}
CACHE_DURATION = 300  # 5 minutos

# Lista de User-Agents para rotação
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/91.0.864.59',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15'
]

# Controle de rate limiting
last_request_time = 0
MIN_DELAY = 3  # Segundos entre requisições

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
        sleep_time = MIN_DELAY - time_since_last + random.uniform(0.5, 2.0)  # Adiciona variação aleatória
        time.sleep(sleep_time)
    
    last_request_time = time.time()

def create_instaloader_session():
    """Cria uma sessão do Instaloader com User-Agent rotativo"""
    L = instaloader.Instaloader(
        quiet=True,
        user_agent=random.choice(USER_AGENTS),
        sleep=True,  # Adiciona delays automáticos
        fatal_status_codes=[429]  # Não trata 429 como fatal
    )
    
    # Configurações adicionais para evitar detecção
    L.context.log = lambda *args, **kwargs: None  # Desabilita logs
    
    return L

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
        
        # Cria sessão com proteções
        L = create_instaloader_session()
        
        try:
            # Busca o perfil
            profile = instaloader.Profile.from_username(L.context, username)
            
            # Coleta posts com limite e delay
            posts = []
            post_count = 0
            max_posts = 10
            
            for post in profile.get_posts():
                if post_count >= max_posts:
                    break
                
                posts.append({
                    "url": f"https://www.instagram.com/p/{post.shortcode}/",
                    "likes": post.likes,
                    "comments": post.comments,
                    "date": post.date.isoformat()
                })
                post_count += 1
                
                # Pequeno delay entre posts
                if post_count < max_posts:
                    time.sleep(random.uniform(0.5, 1.5))
            
            # Prepara resposta
            profile_data = {
                "username": profile.username,
                "full_name": profile.full_name,
                "biography": profile.biography,
                "followers": profile.followers,
                "following": profile.followees,
                "posts_count": profile.mediacount,
                "profile_pic_url": profile.profile_pic_url,
                "is_private": profile.is_private,
                "is_verified": profile.is_verified,
                "external_url": profile.external_url,
                "posts": posts,
                "cached": False,
                "timestamp": datetime.now().isoformat()
            }
            
            # Salva no cache
            cache_profile(username, profile_data)
            
            return jsonify(profile_data)
            
        except instaloader.exceptions.ProfileNotExistsException:
            return jsonify({"error": f"Perfil @{username} não existe"}), 404
            
        except instaloader.exceptions.LoginRequiredException:
            return jsonify({
                "error": "Instagram requer login para este perfil",
                "suggestion": "Tente novamente em alguns minutos ou use um perfil público"
            }), 403
            
        except instaloader.exceptions.ConnectionException as e:
            if "429" in str(e) or "rate" in str(e).lower():
                return jsonify({
                    "error": "Instagram está limitando requisições",
                    "suggestion": "Aguarde alguns minutos antes de tentar novamente",
                    "retry_after": 300
                }), 429
            else:
                return jsonify({
                    "error": "Erro de conexão com Instagram",
                    "details": str(e)
                }), 503
                
    except Exception as e:
        return jsonify({
            "error": "Erro interno do servidor",
            "details": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Endpoint para verificar se a API está funcionando"""
    return jsonify({
        "status": "online",
        "timestamp": datetime.now().isoformat(),
        "cache_size": len(cache),
        "version": "1.0.0"
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

@app.route('/', methods=['GET'])
def index():
    """Página inicial com documentação"""
    return jsonify({
        "message": "API Instagram Profile",
        "version": "1.0.0",
        "endpoints": {
            "profile": "/api/profile?username=USUARIO",
            "health": "/api/health",
            "clear_cache": "/api/cache/clear (POST)"
        },
        "features": [
            "Rate limiting protection",
            "User-Agent rotation",
            "Request caching (5 min)",
            "Error handling",
            "Anti-block measures"
        ],
        "usage": "GET /api/profile?username=cristiano",
        "timestamp": datetime.now().isoformat()
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    app.run(host='0.0.0.0', port=port, debug=False)