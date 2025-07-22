from flask import Blueprint, render_template, jsonify, request, send_file
from core.services.search_service import SearchService
from core.implementations.mongo_storage import MongoStorage
from core.implementations.openai_llm import OpenAILLM
from core.implementations.mongo_vector import MongoVectorStore
import os
import config
from bson.json_util import dumps
import json

bp = Blueprint('main', __name__)

def get_services():
    storage = MongoStorage()
    storage.connect()
    llm = OpenAILLM()
    vector_store = MongoVectorStore(storage)
    search_service = SearchService(storage, llm, vector_store)
    return storage, search_service

@bp.route('/')
def index():
    return render_template('index.html')

@bp.route('/priorities')
def priorities():
    return render_template('priorities.html')

@bp.route('/api/priorities')
def api_priorities():
    storage, search_service = get_services()
    try:
        limit = request.args.get('limit', 20, type=int)
        priorities = search_service.get_high_priorities(limit)
        return jsonify(priorities)
    except Exception as e:
        print(f"Error in api_priorities: {str(e)}")
        return jsonify({"error": str(e)}), 500
    finally:
        storage.disconnect()

@bp.route('/search')
def search():
    return render_template('search.html')

@bp.route('/api/search')
def api_search():
    storage, search_service = get_services()
    try:
        query = request.args.get('q', '')
        limit = request.args.get('limit', 10, type=int)
        
        if query:
            results = search_service.search_emails(query, limit)
            return jsonify(results)
        return jsonify([])
    except Exception as e:
        print(f"Error in api_search: {str(e)}")
        return jsonify({"error": str(e)}), 500
    finally:
        storage.disconnect()

@bp.route('/download/<path:filepath>')
def download_attachment(filepath):
    full_path = f"/{filepath}"
    if os.path.exists(full_path) and full_path.startswith(str(config.ATTACHMENTS_DIR)):
        return send_file(full_path, as_attachment=True)
    return "File not found", 404

@bp.route('/api/todays-pending')
def api_todays_pending():
    storage, search_service = get_services()
    try:
        pending = search_service.get_todays_unanswered_questions()
        return jsonify(pending)
    finally:
        storage.disconnect()

@bp.route('/api/thread-timeline/<thread_id>')
def api_thread_timeline(thread_id):
    storage, search_service = get_services()
    try:
        timeline = search_service.get_response_timeline(thread_id)
        return jsonify(timeline)
    finally:
        storage.disconnect()

@bp.route('/api/thread-connections/<thread_id>')
def api_thread_connections(thread_id):
    storage, search_service = get_services()
    try:
        connections = search_service.get_cross_thread_connections(thread_id)
        return jsonify(connections)
    finally:
        storage.disconnect()

@bp.route('/thread/<thread_id>')
def thread_details(thread_id):
    return render_template('thread_details.html', thread_id=thread_id)