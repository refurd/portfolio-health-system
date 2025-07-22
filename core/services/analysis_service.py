from typing import List, Dict, Any, Optional
from core.interfaces.storage import StorageInterface
from core.interfaces.llm import LLMInterface
from core.interfaces.vector_store import VectorStoreInterface
from core.interfaces.validator import ValidatorInterface
from core.processors.thread_analyzer import ThreadAnalyzer
from core.processors.priority_calculator import PriorityCalculator
from core.models.email import Email
from core.utils.logger import get_logger
from datetime import datetime
from tqdm import tqdm
import config

class AnalysisService:
    def __init__(self, storage: StorageInterface, llm: LLMInterface, 
                 vector_store: VectorStoreInterface, validator: ValidatorInterface):
        self.storage = storage
        self.llm = llm
        self.vector_store = vector_store
        self.validator = validator
        self.thread_analyzer = ThreadAnalyzer(llm, vector_store)
        self.priority_calculator = PriorityCalculator(llm, validator)
        self.logger = get_logger(__name__)
        
    def analyze_portfolio(self):
        print("\n=== Portfolio Analysis Started ===\n")
        
        # Clear existing analysis data
        print("Clearing previous analysis data...")
        self.storage.db[config.THREADS_COLLECTION].delete_many({})
        self.storage.db[config.PRIORITIES_COLLECTION].delete_many({})
        
        # Step 1: Load emails
        print("\nStep 1: Loading emails from database...")
        email_docs = list(self.storage.find(config.EMAILS_COLLECTION, {}))
        emails = []
        
        with tqdm(total=len(email_docs), desc="Converting emails", unit="email") as pbar:
            for doc in email_docs:
                email = self._doc_to_email(doc)
                if email and email.from_email and email.date:
                    emails.append(email)
                pbar.update(1)
        
        print(f"Loaded {len(emails)} valid emails from {len(email_docs)} total documents")
        
        if not emails:
            print("ERROR: No valid emails found for analysis")
            return
        
        # Step 2: Analyze threads
        print(f"\nStep 2: Analyzing email threads...")
        threads = self.thread_analyzer.analyze_threads(emails)
        print(f"Identified {len(threads)} unique email threads")
        
        # Step 3: Calculate priorities and save
        print(f"\nStep 3: Calculating priorities for each thread...")
        
        high_priority_count = 0
        
        with tqdm(total=len(threads), desc="Processing threads", unit="thread") as pbar:
            for i, thread in enumerate(threads):
                pbar.set_description(f"Thread {i+1}/{len(threads)}: {thread.subject[:30]}...")
                
                # Save thread
                thread_doc = thread.to_dict()
                thread_id = self.storage.insert_one(config.THREADS_COLLECTION, thread_doc)
                thread.id = thread_id
                
                try:
                    # Calculate priority
                    priority = self.priority_calculator.calculate_priorities(thread)
                    priority_doc = priority.to_dict()
                    self.storage.insert_one(config.PRIORITIES_COLLECTION, priority_doc)
                    
                    if priority.score > config.PRIORITY_THRESHOLD:
                        high_priority_count += 1
                        
                except Exception as e:
                    self.logger.error(f"Error calculating priority for thread {thread_id}: {str(e)}")
                
                pbar.update(1)
        
        # Summary
        print(f"\n=== Analysis Complete ===")
        print(f"Total threads analyzed: {len(threads)}")
        print(f"High priority items: {high_priority_count}")
        print(f"Priority threshold: {config.PRIORITY_THRESHOLD}")
        
        # Top issues summary
        self._print_top_issues()
        
    def _print_top_issues(self):
        print("\n=== Top Priority Issues ===")
        
        priorities = list(self.storage.find(config.PRIORITIES_COLLECTION, {}))
        priorities.sort(key=lambda x: x.get('score', 0), reverse=True)
        
        for i, priority in enumerate(priorities[:5]):
            thread = self.storage.find_one(config.THREADS_COLLECTION, {'_id': priority.get('thread_id')})
            if thread:
                print(f"\n{i+1}. {thread.get('subject', 'Unknown')}")
                print(f"   Priority Score: {priority.get('score', 0):.2f}")
                print(f"   Days Stalled: {priority.get('days_stalled', 0)}")
                
                # Top attention flags
                attention_flags = priority.get('attention_flags', {})
                if attention_flags:
                    top_flags = sorted(attention_flags.items(), key=lambda x: x[1], reverse=True)[:3]
                    print(f"   Key Issues: {', '.join([f'{flag}: {score:.2f}' for flag, score in top_flags])}")
                    
    def _doc_to_email(self, doc: Dict[str, Any]) -> Optional[Email]:
        try:
            date_value = doc.get('date')
            if isinstance(date_value, str):
                date_value = datetime.fromisoformat(date_value)
            elif not isinstance(date_value, datetime):
                date_value = None
                
            return Email(
                id=str(doc.get('_id')),
                subject=doc.get('subject', ''),
                date=date_value,
                from_email=doc.get('from_email', ''),
                from_name=doc.get('from_name', ''),
                to_emails=doc.get('to_emails', []),
                cc_emails=doc.get('cc_emails', []),
                body=doc.get('body', ''),
                attachments=doc.get('attachments', []),
                thread_id=doc.get('thread_id'),
                is_internal=doc.get('is_internal', True),
                embedding=doc.get('embedding'),
                metadata=doc.get('metadata', {})
            )
        except Exception as e:
            self.logger.error(f"Error converting document to email: {str(e)}")
            return None