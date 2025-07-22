from flask import Flask
from web.routes import bp
from core.implementations.mongo_storage import MongoStorage
from core.implementations.mongo_vector import MongoVectorStore
from core.implementations.openai_llm import OpenAILLM
from core.implementations.anthropic_validator import AnthropicValidator
from core.services.ingestion_service import IngestionService
from core.services.analysis_service import AnalysisService
import sys
import os

def create_app():
    app = Flask(__name__, 
                template_folder='web/templates',
                static_folder='static')
    app.register_blueprint(bp)
    return app

def initialize_system():
    storage = MongoStorage()
    storage.connect()
    
    llm = OpenAILLM()
    vector_store = MongoVectorStore(storage)
    validator = AnthropicValidator()
    
    if '--ingest' in sys.argv:
        print("Starting email ingestion...")
        ingestion_service = IngestionService(storage, llm)
        count = ingestion_service.ingest_all_emails()
        print(f"Ingestion complete. Processed {count} emails.")
        storage.disconnect()
        sys.exit(0)
        
    if '--analyze' in sys.argv:
        print("Starting portfolio analysis...")
        analysis_service = AnalysisService(storage, llm, vector_store, validator)
        analysis_service.analyze_portfolio()
        print("Analysis complete.")
        storage.disconnect()
        sys.exit(0)
    
    return storage

if __name__ == '__main__':
    storage = initialize_system()
    
    app = create_app()
    
    try:
        app.run(debug=True, host='0.0.0.0', port=5000)
    finally:
        storage.disconnect()