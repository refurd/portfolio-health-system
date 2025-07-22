# /home/gyorkosdominik/_work/portfolio-health-system/core/services/response_tracker.py
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from core.models.email import Email
from core.interfaces.llm import LLMInterface
import json

class ResponseTracker:
    def __init__(self, llm: LLMInterface):
        self.llm = llm
        
    def analyze_response_chains(self, emails: List[Email]) -> Dict[str, Any]:
        """Analyze email chains to track questions and responses"""
        
        # Sort emails by date
        sorted_emails = sorted([e for e in emails if e.date], key=lambda x: x.date)
        
        # Track all questions and their responses
        questions_tracker = []
        
        for email in sorted_emails:
            # Get questions from this email
            questions = email.metadata.get('questions_asked', [])
            for q in questions:
                if q.get('needs_answer'):
                    questions_tracker.append({
                        'question': q['question'],
                        'asked_by': email.from_email,
                        'asked_date': email.date,
                        'asked_in_subject': email.subject,
                        'answered': False,
                        'answer': None,
                        'answered_by': None,
                        'answered_date': None,
                        'response_time_days': None
                    })
            
            # Check if this email answers any previous questions
            answers = email.metadata.get('answers_provided', [])
            for answer in answers:
                # Find matching question
                for qt in questions_tracker:
                    if not qt['answered'] and self._matches_question(qt['question'], answer.get('answers_question', '')):
                        qt['answered'] = True
                        qt['answer'] = answer['answer']
                        qt['answered_by'] = email.from_email
                        qt['answered_date'] = email.date
                        qt['response_time_days'] = (email.date - qt['asked_date']).days
        
        # Find unanswered questions
        unanswered = [q for q in questions_tracker if not q['answered']]
        
        # Calculate stats
        response_times = [q['response_time_days'] for q in questions_tracker if q['answered'] and q['response_time_days'] is not None]
        avg_response_time = sum(response_times) / len(response_times) if response_times else None
        
        return {
            'all_questions': questions_tracker,
            'unanswered_questions': unanswered,
            'total_questions': len(questions_tracker),
            'answered_count': len([q for q in questions_tracker if q['answered']]),
            'unanswered_count': len(unanswered),
            'average_response_time_days': avg_response_time,
            'longest_unanswered_days': max([(datetime.now() - q['asked_date']).days for q in unanswered]) if unanswered else 0
        }
    
    def _matches_question(self, question1: str, question2: str) -> bool:
        """Use LLM to determine if two questions are the same"""
        if not question1 or not question2:
            return False
            
        prompt = f"""Do these two questions refer to the same thing? Answer with just 'YES' or 'NO'.

Question 1: {question1}
Question 2: {question2}"""
        
        try:
            response = self.llm.generate(prompt, temperature=0.1)
            return 'YES' in response.upper()
        except:
            # Fallback to simple comparison
            return question1.lower() in question2.lower() or question2.lower() in question1.lower()
    
    def find_conversation_flows(self, emails: List[Email]) -> List[Dict[str, Any]]:
        """Trace conversation flows and identify who's waiting for responses"""
        
        flows = []
        sorted_emails = sorted([e for e in emails if e.date], key=lambda x: x.date)
        
        for i, email in enumerate(sorted_emails):
            # Check if this email is replying to something
            if email.metadata.get('is_reply_to_subject'):
                # Find the original email
                original = None
                for j in range(i-1, -1, -1):
                    prev_email = sorted_emails[j]
                    if (email.metadata.get('replying_to_from') == prev_email.from_email and
                        email.metadata.get('is_reply_to_subject') in prev_email.subject):
                        original = prev_email
                        break
                
                if original:
                    response_time = (email.date - original.date).total_seconds() / 3600  # in hours
                    flows.append({
                        'original_subject': original.subject,
                        'original_from': original.from_email,
                        'original_date': original.date,
                        'reply_from': email.from_email,
                        'reply_date': email.date,
                        'response_time_hours': response_time,
                        'contains_answer': len(email.metadata.get('answers_provided', [])) > 0
                    })
        
        # Find who's waiting for responses
        waiting_for_response = []
        for email in sorted_emails:
            if email.metadata.get('questions_asked'):
                # Check if any later email responded
                has_response = False
                for flow in flows:
                    if (flow['original_from'] == email.from_email and 
                        flow['original_date'] == email.date and
                        flow['contains_answer']):
                        has_response = True
                        break
                
                if not has_response:
                    days_waiting = (datetime.now() - email.date).days
                    waiting_for_response.append({
                        'waiting_from': email.from_email,
                        'subject': email.subject,
                        'sent_date': email.date,
                        'days_waiting': days_waiting,
                        'questions': email.metadata.get('questions_asked', [])
                    })
        
        return {
            'conversation_flows': flows,
            'waiting_for_response': waiting_for_response
        }