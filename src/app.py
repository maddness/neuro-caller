"""Main Flask application."""
import logging
from flask import Flask, jsonify
from src.config import config
from src.routes.voice_routes import voice_bp

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_app():
    """Create and configure Flask application."""
    app = Flask(__name__)

    # Validate configuration
    try:
        config.validate()
        logger.info("Configuration validated successfully")
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        raise

    # Register blueprints
    app.register_blueprint(voice_bp)

    @app.route('/')
    def index():
        """Root endpoint."""
        return jsonify({
            'service': 'neuro-caller',
            'version': '1.0.0',
            'status': 'running'
        })

    @app.route('/health')
    def health():
        """Health check endpoint."""
        return jsonify({'status': 'ok'}), 200

    logger.info("Flask application created successfully")
    return app


if __name__ == '__main__':
    app = create_app()
    app.run(
        host='0.0.0.0',
        port=config.PORT,
        debug=True
    )
