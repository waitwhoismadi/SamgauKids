import os
from app import create_app, create_tables
from dotenv import load_dotenv

load_dotenv()


app = create_app()

if __name__ == '__main__':
    create_tables(app)
    
    debug = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'
    host = os.environ.get('FLASK_HOST', 'localhost')
    port = int(os.environ.get('FLASK_PORT', 5000))
    
    app.run(debug=debug, host=host, port=port)