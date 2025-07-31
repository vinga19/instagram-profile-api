
from flask import Flask, request, jsonify
import instaloader

app = Flask(__name__)
L = instaloader.Instaloader()

@app.route("/api/profile", methods=["GET"])
def get_instagram_profile():
    username = request.args.get("username")
    if not username:
        return jsonify({"error": "Parâmetro 'username' é obrigatório"}), 400
    try:
        profile = instaloader.Profile.from_username(L.context, username)
        data = {
            "username": profile.username,
            "full_name": profile.full_name,
            "bio": profile.biography,
            "followers": profile.followers,
            "following": profile.followees,
            "posts": profile.mediacount,
            "profile_pic_url": profile.profile_pic_url
        }
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
