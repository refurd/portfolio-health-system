from typing import List, Dict, Any
from core.interfaces.storage import StorageInterface
from core.interfaces.llm import LLMInterface
from core.interfaces.vector_store import VectorStoreInterface
from bson import ObjectId
import config
from datetime import datetime, date

class SearchService:
    def __init__(self, storage: StorageInterface, llm: LLMInterface, vector_store: VectorStoreInterface):
        self.storage = storage
        self.llm = llm
        self.vector_store = vector_store
        
    def search_emails(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        query_embedding = self.llm.generate_embedding(query)
        
        results = self.vector_store.search_similar(
            config.EMAILS_COLLECTION,
            query_embedding,
            k=limit
        )
        
        emails = []
        for doc, score in results:
            email = self._convert_doc_to_json(doc)
            email['similarity_score'] = score
            emails.append(email)
            
        return emails
        
    def get_high_priorities(self, limit: int = 20) -> List[Dict[str, Any]]:
        priorities = self.storage.find(config.PRIORITIES_COLLECTION, {})
        priorities.sort(key=lambda x: x.get('score', 0), reverse=True)
        
        enriched_priorities = []
        for priority in priorities[:limit]:
            priority_json = self._convert_doc_to_json(priority)
            
            # Get thread info
            thread_id = priority.get('thread_id')
            if thread_id:
                if isinstance(thread_id, str):
                    thread = self.storage.find_one(config.THREADS_COLLECTION, {'_id': ObjectId(thread_id)})
                else:
                    thread = self.storage.find_one(config.THREADS_COLLECTION, {'_id': thread_id})
                    
                if thread:
                    priority_json['thread'] = self._convert_doc_to_json(thread)
                    
            enriched_priorities.append(priority_json)
            
        return enriched_priorities
        
    def _convert_doc_to_json(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        """Convert MongoDB document to JSON-serializable format"""
        if not doc:
            return {}
            
        result = {}
        for key, value in doc.items():
            if key == '_id' and isinstance(value, ObjectId):
                result['_id'] = str(value)
            elif isinstance(value, ObjectId):
                result[key] = str(value)
            elif isinstance(value, list):
                result[key] = [str(v) if isinstance(v, ObjectId) else v for v in value]
            elif isinstance(value, dict):
                result[key] = self._convert_doc_to_json(value)
            else:
                result[key] = value
                
        return result

    def get_todays_unanswered_questions(self) -> List[Dict[str, Any]]:
        """Get questions from today that haven't received responses yet"""
        
        today = date.today()
        today_key = today.isoformat()
        
        # Get all threads
        threads = self.storage.find(config.THREADS_COLLECTION, {})
        
        todays_unanswered = []
        
        for thread in threads:
            daily_status = thread.get('metadata', {}).get('daily_response_status', {})
            
            # Check if there's activity today
            if today_key in daily_status:
                today_data = daily_status[today_key]
                
                # Get questions that were asked today and not answered today
                unanswered_questions = []
                for q in today_data.get('questions_asked', []):
                    if not q.get('answered_same_day', False):
                        unanswered_questions.append({
                            'question': q['question'],
                            'asked_by': q['asked_by'],
                            'asked_at': q.get('asked_at', ''),
                            'email_subject': q.get('email_subject', '')
                        })
                
                if unanswered_questions:
                    todays_unanswered.append({
                        'thread_id': str(thread['_id']),
                        'thread_subject': thread.get('subject'),
                        'questions': unanswered_questions,
                        'total_unanswered_today': len(unanswered_questions)
                    })
            
            # Also check unanswered_today from enhanced analysis
            unanswered_today = thread.get('metadata', {}).get('unanswered_today', [])
            critical_unanswered = [u for u in unanswered_today if u.get('critical', False)]
            
            if critical_unanswered:
                # Add or update the thread entry
                thread_entry = next((t for t in todays_unanswered if t['thread_id'] == str(thread['_id'])), None)
                if not thread_entry:
                    todays_unanswered.append({
                        'thread_id': str(thread['_id']),
                        'thread_subject': thread.get('subject'),
                        'critical_unanswered': critical_unanswered,
                        'oldest_unanswered_days': max([u['days_waiting'] for u in critical_unanswered])
                    })
                else:
                    thread_entry['critical_unanswered'] = critical_unanswered
                    thread_entry['oldest_unanswered_days'] = max([u['days_waiting'] for u in critical_unanswered])
        
        # Sort by urgency
        todays_unanswered.sort(key=lambda x: x.get('oldest_unanswered_days', 0), reverse=True)
        
        return todays_unanswered

    def get_response_timeline(self, thread_id: str) -> Dict[str, Any]:
        """Get detailed response timeline for a thread"""
        
        thread = self.storage.find_one(config.THREADS_COLLECTION, {'_id': ObjectId(thread_id)})
        if not thread:
            return {}
        
        daily_status = thread.get('metadata', {}).get('daily_response_status', {})
        response_times = thread.get('metadata', {}).get('response_times_by_day', {})
        
        # Build timeline
        timeline = []
        for date_key in sorted(daily_status.keys()):
            day_data = daily_status[date_key]
            
            timeline_entry = {
                'date': date_key,
                'questions_asked': day_data.get('total_questions', 0),
                'answered_same_day': day_data.get('answered_same_day', 0),
                'unanswered_same_day': day_data.get('unanswered_same_day', 0),
                'average_response_hours': day_data.get('average_response_time_hours'),
                'email_count': day_data.get('email_count', 0),
                'has_pending': day_data.get('has_pending_response', False)
            }
            
            # Add response rate if available
            if date_key in response_times:
                timeline_entry['response_rate'] = response_times[date_key]['response_rate']
            
            timeline.append(timeline_entry)
        
        return {
            'thread_subject': thread.get('subject'),
            'timeline': timeline,
            'total_days': len(timeline),
            'days_with_unanswered': len([t for t in timeline if t['has_pending']]),
            'average_daily_response_rate': sum([t.get('response_rate', 0) for t in timeline]) / len(timeline) if timeline else 0,
            'waiting_for_response': thread.get('metadata', {}).get('waiting_for_response', []),
            'unanswered_today': thread.get('metadata', {}).get('unanswered_today', [])
        }
    
    def get_cross_thread_connections(self, thread_id: str) -> List[Dict[str, Any]]:
        """Find other threads that might be connected to this one"""
        
        thread = self.storage.find_one(config.THREADS_COLLECTION, {'_id': ObjectId(thread_id)})
        if not thread:
            return []
        
        # Get thread participants and key terms
        participants = set(thread.get('participants', []))
        
        # Find other threads with overlapping participants
        all_threads = self.storage.find(config.THREADS_COLLECTION, {})
        
        connections = []
        for other_thread in all_threads:
            if str(other_thread['_id']) == thread_id:
                continue
                
            other_participants = set(other_thread.get('participants', []))
            common_participants = participants & other_participants
            
            if len(common_participants) >= 2:  # At least 2 common participants
                # Check for continuations
                continuations = other_thread.get('metadata', {}).get('thread_continuations', [])
                is_continuation = any(cont.get('original_subject') in thread.get('subject', '') for cont in continuations)
                
                connections.append({
                    'thread_id': str(other_thread['_id']),
                    'subject': other_thread.get('subject'),
                    'common_participants': list(common_participants),
                    'is_continuation': is_continuation,
                    'last_activity': other_thread.get('last_activity'),
                    'status': other_thread.get('status')
                })
        
        # Sort by relevance
        connections.sort(key=lambda x: (x['is_continuation'], len(x['common_participants'])), reverse=True)
        
        return connections[:5]  # Return top 5 connections