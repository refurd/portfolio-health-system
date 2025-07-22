from typing import List, Dict, Any, Optional, Set, Tuple
from core.models.email import Email
from core.models.thread import Thread
from core.interfaces.llm import LLMInterface
from core.interfaces.vector_store import VectorStoreInterface
from core.services.response_tracker import ResponseTracker
import json
from datetime import datetime, timedelta, date
from tqdm import tqdm
import config
import numpy as np

class ThreadAnalyzer:
    def __init__(self, llm: LLMInterface, vector_store: VectorStoreInterface):
        self.llm = llm
        self.vector_store = vector_store
        self.response_tracker = ResponseTracker(llm)
        
    def analyze_threads(self, emails: List[Email]) -> List[Thread]:
        threads = []
        processed_emails = set()
        
        valid_emails = [e for e in emails if e.id and e.date]
        
        print(f"Grouping {len(valid_emails)} emails into threads using advanced LLM analysis...")
        
        # First pass: Create initial thread groups using enhanced LLM analysis
        thread_groups = self._identify_thread_groups_with_llm(valid_emails)
        
        # Second pass: Find cross-thread connections using semantic similarity
        cross_thread_connections = self._find_cross_thread_connections(thread_groups, valid_emails)
        
        # Third pass: Merge threads based on connections
        merged_groups = self._merge_connected_threads(thread_groups, cross_thread_connections)
        
        print(f"Identified {len(merged_groups)} thread groups after advanced merging")
        
        with tqdm(total=len(merged_groups), desc="Analyzing threads", unit="thread") as pbar:
            for thread_emails in merged_groups:
                if thread_emails:
                    thread = self._create_thread_with_response_tracking(thread_emails)
                    if thread:
                        # Add enhanced daily response status
                        daily_analysis = self._analyze_daily_responses_enhanced(thread_emails)
                        thread.metadata['daily_response_status'] = daily_analysis['daily_status']
                        thread.metadata['unanswered_today'] = daily_analysis['unanswered_today']
                        thread.metadata['response_times_by_day'] = daily_analysis['response_times_by_day']
                        threads.append(thread)
                        
                pbar.update(1)
                
        return threads
    
    def _identify_thread_groups_with_llm(self, emails: List[Email]) -> List[List[Email]]:
        """Enhanced LLM grouping with better context understanding"""
        
        # Generate embeddings for all emails for semantic similarity
        email_embeddings = {}
        for email in emails:
            if email.embedding:
                email_embeddings[email.id] = np.array(email.embedding)
        
        # Prepare comprehensive email summaries
        email_summaries = []
        for i, email in enumerate(emails):
            # Extract key phrases from body
            key_phrases = self._extract_key_phrases(email.body)
            
            email_summaries.append({
                'index': i,
                'id': email.id,
                'subject': email.subject,
                'from': email.from_email,
                'date': email.date.isoformat() if email.date else '',
                'to': email.to_emails,
                'cc': email.cc_emails,
                'is_reply_to': email.metadata.get('is_reply_to_subject', ''),
                'replying_to_from': email.metadata.get('replying_to_from', ''),
                'has_questions': len(email.metadata.get('questions_asked', [])) > 0,
                'has_answers': len(email.metadata.get('answers_provided', [])) > 0,
                'questions': [q['question'] for q in email.metadata.get('questions_asked', [])],
                'key_phrases': key_phrases,
                'mentions_subjects': self._find_subject_references(email.body, [e.subject for e in emails]),
                'body_preview': email.body[:300] if email.body else ''
            })
        
        # Process with enhanced prompt
        batch_size = 30  # Smaller batches for better accuracy
        all_groups = []
        group_metadata = []
        
        for i in range(0, len(email_summaries), batch_size):
            batch = email_summaries[i:i+batch_size]
            
            prompt = f"""Analyze these emails and group them into conversation threads with MAXIMUM ACCURACY.

CRITICAL GROUPING RULES:
1. Emails with "Re:" or "Fwd:" MUST be grouped with their original thread
2. If an email answers questions from another email, they belong together
3. If someone forwards a conversation and discussion continues, group them
4. If topics/projects are discussed across different subject lines, group them
5. Check for quoted text that references other emails
6. Look for project names, ticket numbers, or other identifiers
7. Consider participant overlap - same people discussing same topic

SPECIAL ATTENTION:
- An email mentioning another email's subject or content should be grouped together
- "Forwarded message" sections indicate thread continuation
- Questions in one thread answered in another means they should merge

Emails to analyze:
{json.dumps(batch, indent=2)}

Return a detailed JSON object:
{{
    "groups": [
        {{
            "email_indices": [list of indices],
            "main_topic": "what this thread is about",
            "key_identifiers": ["project names", "ticket numbers", etc],
            "confidence": 0.0-1.0
        }}
    ],
    "potential_merges": [
        {{
            "group1_idx": 0,
            "group2_idx": 1,
            "reason": "specific reason these might be the same conversation",
            "confidence": 0.0-1.0
        }}
    ]
}}"""

            try:
                response = self.llm.generate(prompt, temperature=0.1)
                response = response.strip()
                if response.startswith('```json'):
                    response = response[7:-3]
                
                result = json.loads(response)
                groups_data = result.get('groups', [])
                
                # Process groups with metadata
                for group_info in groups_data:
                    thread_emails = []
                    indices = group_info.get('email_indices', [])
                    
                    for idx in indices:
                        actual_idx = i + idx
                        if 0 <= actual_idx < len(emails):
                            thread_emails.append(emails[actual_idx])
                    
                    if thread_emails:
                        all_groups.append(thread_emails)
                        group_metadata.append({
                            'main_topic': group_info.get('main_topic', ''),
                            'key_identifiers': group_info.get('key_identifiers', []),
                            'confidence': group_info.get('confidence', 0.8)
                        })
                        
            except Exception as e:
                print(f"Error in LLM thread grouping: {str(e)}")
                # Fallback grouping by subject similarity
                for idx in range(len(batch)):
                    actual_idx = i + idx
                    if actual_idx < len(emails):
                        all_groups.append([emails[actual_idx]])
                        group_metadata.append({'confidence': 0.5})
        
        return all_groups
    
    def _find_cross_thread_connections(self, thread_groups: List[List[Email]], all_emails: List[Email]) -> List[Dict[str, Any]]:
        """Find connections between threads using semantic analysis"""
        
        connections = []
        
        # Calculate thread summaries and embeddings
        thread_summaries = []
        for i, group in enumerate(thread_groups):
            summary = self._create_thread_summary(group)
            thread_summaries.append(summary)
        
        # Compare each thread pair
        for i in range(len(thread_groups)):
            for j in range(i + 1, len(thread_groups)):
                connection_score = self._calculate_thread_connection_score(
                    thread_groups[i], 
                    thread_groups[j],
                    thread_summaries[i],
                    thread_summaries[j]
                )
                
                if connection_score['score'] > 0.7:
                    connections.append({
                        'thread1_idx': i,
                        'thread2_idx': j,
                        'score': connection_score['score'],
                        'reasons': connection_score['reasons']
                    })
        
        return connections
    
    def _create_thread_summary(self, emails: List[Email]) -> Dict[str, Any]:
        """Create a comprehensive summary of a thread"""
        
        participants = set()
        subjects = set()
        key_terms = set()
        questions = []
        dates = []
        
        for email in emails:
            participants.add(email.from_email)
            participants.update(email.to_emails)
            subjects.add(email.subject)
            
            # Extract key terms
            if email.body:
                terms = self._extract_key_phrases(email.body)
                key_terms.update(terms)
            
            # Collect questions
            questions.extend([q['question'] for q in email.metadata.get('questions_asked', [])])
            
            if email.date:
                dates.append(email.date)
        
        # Generate thread embedding by averaging email embeddings
        embeddings = [np.array(e.embedding) for e in emails if e.embedding]
        avg_embedding = np.mean(embeddings, axis=0) if embeddings else None
        
        return {
            'participants': list(participants),
            'subjects': list(subjects),
            'key_terms': list(key_terms),
            'questions': questions,
            'date_range': (min(dates), max(dates)) if dates else (None, None),
            'embedding': avg_embedding,
            'email_count': len(emails)
        }
    
    def _calculate_thread_connection_score(self, 
                                         group1: List[Email], 
                                         group2: List[Email],
                                         summary1: Dict[str, Any],
                                         summary2: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate how likely two thread groups are connected"""
        
        score = 0.0
        reasons = []
        
        # 1. Check embedding similarity
        if summary1['embedding'] is not None and summary2['embedding'] is not None:
            similarity = self._cosine_similarity(summary1['embedding'], summary2['embedding'])
            if similarity > 0.85:
                score += 0.3
                reasons.append(f"High semantic similarity: {similarity:.2f}")
        
        # 2. Check participant overlap
        common_participants = set(summary1['participants']) & set(summary2['participants'])
        if len(common_participants) >= 2:
            score += 0.2
            reasons.append(f"Common participants: {', '.join(common_participants)}")
        
        # 3. Check if one thread answers questions from another
        for q in summary1['questions']:
            for email in group2:
                answers = email.metadata.get('answers_provided', [])
                for a in answers:
                    if self._matches_question_answer(q, a.get('answers_question', '')):
                        score += 0.4
                        reasons.append(f"Thread 2 answers question from Thread 1")
                        break
        
        # 4. Check for forwarded content
        for email in group2:
            if any(subject in email.body for subject in summary1['subjects'] if subject):
                score += 0.2
                reasons.append("Thread 2 references Thread 1 subjects")
            
            # Check if email explicitly mentions forwarding from thread 1
            if email.metadata.get('is_reply_to_subject'):
                for subj in summary1['subjects']:
                    if subj in email.metadata['is_reply_to_subject']:
                        score += 0.3
                        reasons.append("Direct forward/reply connection")
        
        # 5. Check key term overlap
        common_terms = set(summary1['key_terms']) & set(summary2['key_terms'])
        if len(common_terms) > 3:
            score += 0.2
            reasons.append(f"Common key terms: {', '.join(list(common_terms)[:3])}")
        
        # 6. Use LLM for final verification if score is borderline
        if 0.5 < score < 0.7:
            llm_score = self._verify_connection_with_llm(group1[:3], group2[:3])
            if llm_score:
                score += 0.2
                reasons.append("LLM confirmed connection")
        
        return {
            'score': min(score, 1.0),
            'reasons': reasons
        }
    
    def _matches_question_answer(self, question: str, answer_ref: str) -> bool:
        """Check if an answer references a specific question"""
        if not question or not answer_ref:
            return False
        
        # Simple check first
        if question.lower() in answer_ref.lower() or answer_ref.lower() in question.lower():
            return True
        
        # Use LLM for semantic matching
        prompt = f"""Does this answer reference match this question? Answer YES or NO.
Question: {question}
Answer reference: {answer_ref}"""
        
        try:
            response = self.llm.generate(prompt, temperature=0.1)
            return 'YES' in response.upper()
        except:
            return False
    
    def _verify_connection_with_llm(self, group1_sample: List[Email], group2_sample: List[Email]) -> bool:
        """Use LLM to verify if two groups are connected"""
        
        group1_text = "\n".join([f"- {e.subject}: {e.body[:200]}" for e in group1_sample])
        group2_text = "\n".join([f"- {e.subject}: {e.body[:200]}" for e in group2_sample])
        
        prompt = f"""Are these two email groups part of the same conversation or discussing the same issue?

Group 1:
{group1_text}

Group 2:
{group2_text}

Answer YES if they are clearly connected, NO if they are separate topics."""
        
        try:
            response = self.llm.generate(prompt, temperature=0.1)
            return 'YES' in response.upper()
        except:
            return False
    
    def _merge_connected_threads(self, 
                               thread_groups: List[List[Email]], 
                               connections: List[Dict[str, Any]]) -> List[List[Email]]:
        """Merge threads based on connection analysis"""
        
        # Sort connections by score
        connections.sort(key=lambda x: x['score'], reverse=True)
        
        # Track which groups have been merged
        merged_map = {}  # old_idx -> new_idx
        merged_groups = []
        
        for conn in connections:
            idx1, idx2 = conn['thread1_idx'], conn['thread2_idx']
            
            # Find the ultimate group each index belongs to
            while idx1 in merged_map:
                idx1 = merged_map[idx1]
            while idx2 in merged_map:
                idx2 = merged_map[idx2]
            
            if idx1 != idx2:  # Not already merged
                # Merge idx2 into idx1
                if idx1 < len(thread_groups):
                    thread_groups[idx1].extend(thread_groups[idx2])
                    merged_map[idx2] = idx1
        
        # Collect final groups
        for i, group in enumerate(thread_groups):
            if i not in merged_map:  # This is a root group
                merged_groups.append(group)
        
        return merged_groups
    
    def _analyze_daily_responses_enhanced(self, emails: List[Email]) -> Dict[str, Any]:
        """Enhanced daily response analysis that tracks same-day responses"""
        
        daily_status = {}
        sorted_emails = sorted(emails, key=lambda x: x.date)
        
        # Group emails by day
        emails_by_day = {}
        for email in sorted_emails:
            day_key = email.date.date()
            if day_key not in emails_by_day:
                emails_by_day[day_key] = []
            emails_by_day[day_key].append(email)
        
        # Analyze each day
        for day, day_emails in emails_by_day.items():
            day_key = day.isoformat()
            
            # Track all questions asked this day
            questions_asked_today = []
            for email in day_emails:
                for q in email.metadata.get('questions_asked', []):
                    if q.get('needs_answer'):
                        questions_asked_today.append({
                            'question': q['question'],
                            'asked_by': email.from_email,
                            'asked_at': email.date,
                            'email_subject': email.subject,
                            'answered_same_day': False,
                            'answered_by': None,
                            'answered_at': None
                        })
            
            # Check for same-day responses
            for question in questions_asked_today:
                for email in day_emails:
                    # Only check emails after the question was asked
                    if email.date > question['asked_at']:
                        for answer in email.metadata.get('answers_provided', []):
                            if self._matches_question_answer(
                                question['question'], 
                                answer.get('answers_question', '')
                            ):
                                question['answered_same_day'] = True
                                question['answered_by'] = email.from_email
                                question['answered_at'] = email.date
                                break
                    if question['answered_same_day']:
                        break
            
            # Calculate response times for this day
            response_times = []
            for q in questions_asked_today:
                if q['answered_same_day']:
                    response_time = (q['answered_at'] - q['asked_at']).total_seconds() / 3600
                    response_times.append(response_time)
            
            # Find unanswered questions from today
            unanswered_today = [q for q in questions_asked_today if not q['answered_same_day']]
            
            daily_status[day_key] = {
                'questions_asked': questions_asked_today,
                'total_questions': len(questions_asked_today),
                'answered_same_day': len([q for q in questions_asked_today if q['answered_same_day']]),
                'unanswered_same_day': len(unanswered_today),
                'average_response_time_hours': sum(response_times) / len(response_times) if response_times else None,
                'has_pending_response': len(unanswered_today) > 0,
                'email_count': len(day_emails)
            }
        
        # Check which questions are still unanswered today
        today = date.today()
        unanswered_today = []
        
        for day_key, status in daily_status.items():
            day_date = date.fromisoformat(day_key)
            if day_date < today:  # Don't include today's questions
                for q in status['questions_asked']:
                    if not q['answered_same_day']:
                        # Check if it was answered on any later day
                        answered_later = False
                        for later_day, later_emails in emails_by_day.items():
                            if later_day > day_date:
                                for email in later_emails:
                                    for answer in email.metadata.get('answers_provided', []):
                                        if self._matches_question_answer(
                                            q['question'],
                                            answer.get('answers_question', '')
                                        ):
                                            answered_later = True
                                            break
                                    if answered_later:
                                        break
                            if answered_later:
                                break
                        
                        if not answered_later:
                            days_waiting = (today - day_date).days
                            unanswered_today.append({
                                'question': q['question'],
                                'asked_by': q['asked_by'],
                                'asked_on': day_key,
                                'days_waiting': days_waiting,
                                'critical': days_waiting > config.CRITICAL_DAYS_WITHOUT_RESPONSE
                            })
        
        # Calculate response time patterns by day
        response_times_by_day = {}
        for day_key, status in daily_status.items():
            if status['average_response_time_hours'] is not None:
                response_times_by_day[day_key] = {
                    'avg_hours': status['average_response_time_hours'],
                    'response_rate': status['answered_same_day'] / status['total_questions'] if status['total_questions'] > 0 else 0
                }
        
        return {
            'daily_status': daily_status,
            'unanswered_today': unanswered_today,
            'response_times_by_day': response_times_by_day
        }
    
    def _extract_key_phrases(self, text: str) -> List[str]:
        """Extract key phrases from text"""
        if not text:
            return []
        
        # Simple extraction - could be enhanced with NLP
        key_phrases = []
        
        # Look for quoted phrases
        import re
        quotes = re.findall(r'"([^"]+)"', text)
        key_phrases.extend(quotes[:3])
        
        # Look for capitalized phrases (likely project names)
        caps = re.findall(r'[A-Z][A-Za-z]+(?: [A-Z][A-Za-z]+)+', text)
        key_phrases.extend(caps[:3])
        
        # Look for patterns like JIRA-123
        tickets = re.findall(r'[A-Z]+-\d+', text)
        key_phrases.extend(tickets)
        
        return list(set(key_phrases))[:5]
    
    def _find_subject_references(self, body: str, all_subjects: List[str]) -> List[str]:
        """Find which other email subjects are referenced in this body"""
        if not body:
            return []
        
        referenced = []
        body_lower = body.lower()
        
        for subject in all_subjects:
            if subject and len(subject) > 10:  # Skip very short subjects
                if subject.lower() in body_lower:
                    referenced.append(subject)
        
        return referenced
    
    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors"""
        try:
            dot_product = np.dot(vec1, vec2)
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
                
            return float(dot_product / (norm1 * norm2))
        except Exception:
            return 0.0
        
    def _create_thread_with_response_tracking(self, emails: List[Email]) -> Optional[Thread]:
        if not emails:
            return None
            
        valid_emails = [e for e in emails if e.date]
        if not valid_emails:
            return None
            
        valid_emails.sort(key=lambda x: x.date)
        
        # Analyze response chains with enhanced tracking
        response_analysis = self.response_tracker.analyze_response_chains(valid_emails)
        conversation_flows = self.response_tracker.find_conversation_flows(valid_emails)
        
        # Identify thread continuations in other subjects
        thread_continuations = self._find_thread_continuations(valid_emails)
        
        all_participants = set()
        external_participants = set()
        all_attachments = []
        
        for email in valid_emails:
            if email.from_email:
                all_participants.add(email.from_email)
            all_participants.update(email.to_emails)
            all_participants.update(email.cc_emails)
            
            if not email.is_internal:
                if email.from_email and not email.from_email.endswith('@kisjozsitech.hu'):
                    external_participants.add(email.from_email)
                for recipient in email.to_emails + email.cc_emails:
                    if recipient and not recipient.endswith('@kisjozsitech.hu'):
                        external_participants.add(recipient)
                        
            all_attachments.extend(email.attachments)
        
        # Enhanced unresolved questions with more context
        unresolved_questions = []
        for q in response_analysis['unanswered_questions']:
            question_data = {
                'question': q['question'],
                'asked_by': q['asked_by'],
                'asked_date': q['asked_date'].isoformat() if isinstance(q['asked_date'], datetime) else q['asked_date'],
                'days_unanswered': (datetime.now() - q['asked_date']).days if isinstance(q['asked_date'], datetime) else 0,
                'asked_in_subject': q.get('asked_in_subject', ''),
                'requires_external_response': q['asked_by'] not in [p for p in all_participants if p.endswith('@kisjozsitech.hu')]
            }
            unresolved_questions.append(question_data)
        
        # Enhanced blockers
        blockers = self._find_blockers(valid_emails)
        
        # Add response-based blockers
        for waiting in conversation_flows['waiting_for_response']:
            days_waiting = waiting['days_waiting']
            if days_waiting > config.MAX_DAYS_WITHOUT_RESPONSE:
                blockers.append({
                    'blocker': f"No response to questions from {waiting['waiting_from']}",
                    'impact': 'critical' if days_waiting > config.CRITICAL_DAYS_WITHOUT_RESPONSE else 'high',
                    'identified_by': 'system',
                    'date': waiting['sent_date'].isoformat() if isinstance(waiting['sent_date'], datetime) else waiting['sent_date'],
                    'details': f"Waiting {days_waiting} days for response on: {waiting['subject']}",
                    'questions_count': len(waiting.get('questions', []))
                })
        
        last_date = valid_emails[-1].date
        days_since_activity = (datetime.now() - last_date).days if last_date else 999
        
        # Determine thread status with more nuance
        status = 'active'
        if days_since_activity > 7:
            status = 'stalled'
        elif len(unresolved_questions) > 3:
            status = 'blocked'
        elif any(b['impact'] == 'critical' for b in blockers):
            status = 'critical'
        
        # Enhanced metadata
        metadata = {
            'response_analysis': response_analysis,
            'conversation_flows': conversation_flows['conversation_flows'],
            'waiting_for_response': conversation_flows['waiting_for_response'],
            'average_response_time_days': response_analysis.get('average_response_time_days'),
            'questions_answered_ratio': response_analysis['answered_count'] / response_analysis['total_questions'] if response_analysis['total_questions'] > 0 else 1.0,
            'thread_continuations': thread_continuations,
            'response_pattern': self._analyze_response_pattern(valid_emails),
            'escalation_needed': days_since_activity > 5 and len(unresolved_questions) > 0
        }
        
        return Thread(
            id=None,
            email_ids=[email.id for email in valid_emails],
            subject=valid_emails[0].subject or "No Subject",
            participants=list(all_participants),
            external_participants=list(external_participants),
            start_date=valid_emails[0].date,
            last_activity=last_date,
            status=status,
            priority_score=0.0,
            unresolved_questions=unresolved_questions,
            blockers=blockers,
            attachments=list(set(all_attachments)),
            metadata=metadata
        )
    
    def _find_thread_continuations(self, emails: List[Email]) -> List[Dict[str, Any]]:
        """Find if this thread continues in other email subjects"""
        
        continuations = []
        
        # Look for forwarded emails that might indicate continuation
        for email in emails:
            if 'Fwd:' in email.subject or email.metadata.get('quoted_text'):
                continuations.append({
                    'type': 'forwarded',
                    'original_subject': email.metadata.get('is_reply_to_subject', email.subject),
                    'new_subject': email.subject,
                    'forwarded_by': email.from_email,
                    'date': email.date.isoformat() if email.date else None
                })
        
        return continuations
    
    def _analyze_response_pattern(self, emails: List[Email]) -> Dict[str, Any]:
        """Analyze the response patterns in the thread"""
        
        response_times = []
        response_pairs = []
        
        for i in range(1, len(emails)):
            current = emails[i]
            
            # Find which email this is responding to
            for j in range(i-1, -1, -1):
                prev = emails[j]
                
                # Check if the current email is replying to the previous one
                is_reply_to_subject = current.metadata.get('is_reply_to_subject')
                replying_to_from = current.metadata.get('replying_to_from')
                
                # Fix: Check if is_reply_to_subject is not None before using 'in' operator
                if ((replying_to_from == prev.from_email) or
                    (is_reply_to_subject is not None and 
                     prev.subject is not None and 
                     is_reply_to_subject in prev.subject)):
                    
                    time_diff = (current.date - prev.date).total_seconds() / 3600  # hours
                    response_times.append(time_diff)
                    response_pairs.append({
                        'from': prev.from_email,
                        'to': current.from_email,
                        'response_time_hours': time_diff
                    })
                    break
        
        avg_response_time = sum(response_times) / len(response_times) if response_times else None
        
        return {
            'average_response_time_hours': avg_response_time,
            'fastest_response_hours': min(response_times) if response_times else None,
            'slowest_response_hours': max(response_times) if response_times else None,
            'response_count': len(response_pairs),
            'active_responders': list(set([p['to'] for p in response_pairs]))
        }
        
    def _find_blockers(self, emails: List[Email]) -> List[Dict[str, Any]]:
        if not emails:
            return []
            
        prompt = f"""
        Analyze these emails and identify ALL project blockers, including:
        - Technical blockers
        - Waiting for decisions
        - Resource constraints  
        - External dependencies
        - Unanswered critical questions
        
        {self._format_emails_for_prompt(emails)}
        
        Return JSON array of blockers with format:
        [
            {{
                "blocker": "clear description",
                "impact": "critical/high/medium/low",
                "identified_by": "email address or 'inferred'",
                "date": "YYYY-MM-DD",
                "details": "additional context"
            }}
        ]
        """
        
        try:
            response = self.llm.generate(prompt, temperature=0.3)
            response = response.strip()
            if response.startswith('```json'):
                response = response[7:-3]
            result = json.loads(response)
            return result if isinstance(result, list) else []
        except:
            return []
            
    def _format_emails_for_prompt(self, emails: List[Email]) -> str:
        formatted = []
        for email in emails[:15]:  # Increased to 15 for better context
            date_str = email.date.strftime('%Y-%m-%d %H:%M') if email.date else 'Unknown date'
            formatted.append(f"""
Date: {date_str}
From: {email.from_name} ({email.from_email})
To: {', '.join(email.to_emails)}
Subject: {email.subject}
Reply to: {email.metadata.get('is_reply_to_subject', 'N/A')}
Body preview: {email.body[:500]}...
Has questions: {len(email.metadata.get('questions_asked', []))} questions
Has answers: {len(email.metadata.get('answers_provided', []))} answers
Attachments: {len(email.attachments)}
""")
        return '\n---\n'.join(formatted)