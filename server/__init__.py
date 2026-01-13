from flask import Flask
from .config import Config
from .extensions import socketio

def create_app(config_class=Config):
    app = Flask(__name__, 
                static_folder="../static", 
                template_folder="../templates")
    app.config.from_object(config_class)

    # Initialize extensions
    socketio.init_app(app, async_mode='eventlet')

    # Register Blueprints
    from .routes.main import main_bp
    from .routes.api import api_bp
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp, url_prefix='/api')

    # Import Socket Events (so they are registered)
    import server.sockets.connection
    import server.sockets.gameplay

    return app
