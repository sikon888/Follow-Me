from flask import Flask
import os

from routes.page_routes import (
    page_bp
)

from routes.video_routes import (
    video_bp
)

from routes.reference_routes import (
    reference_bp
)

from routes.game_routes import (
    game_bp
)

from routes.pi_routes import (
    pi_bp
)

# =========================================
# CREATE APP
# =========================================

app = Flask(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True
from routes.player_routes import player_bp
app.register_blueprint(player_bp)
from routes.youtube_routes import youtube_bp
app.register_blueprint(youtube_bp)


# =========================================
# REGISTER ROUTES
# =========================================

app.register_blueprint(
    page_bp
)

app.register_blueprint(
    video_bp
)

app.register_blueprint(
    reference_bp
)

app.register_blueprint(
    game_bp
)

app.register_blueprint(
    pi_bp
)

# =========================================
# DISABLE CACHE
# =========================================

@app.after_request
def add_no_cache(response):

    response.headers[
        "Cache-Control"
    ] = (
        "no-store, "
        "no-cache, "
        "must-revalidate"
    )

    response.headers[
        "Pragma"
    ] = "no-cache"

    response.headers[
        "Expires"
    ] = "0"

    return response


# =========================================
# RUN
# =========================================

if __name__ == "__main__":

    app.run(
        host=os.environ.get('HOST', '0.0.0.0'),
        port=5001,
        debug=False,
        use_reloader=False
    )
