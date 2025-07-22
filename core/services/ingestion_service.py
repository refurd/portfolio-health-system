from typing import List
import os
from core.processors.email_parser import EmailParser
from core.interfaces.storage import StorageInterface
from core.interfaces.llm import LLMInterface
import config
from core.utils.logger import get_logger
from tqdm import tqdm

class IngestionService:
    def __init__(self, storage: StorageInterface, llm: LLMInterface):
        self.storage = storage
        self.llm = llm
        self.parser = EmailParser(llm=llm)  # Pass LLM to parser
        self.logger = get_logger(__name__)
        
    def ingest_all_emails(self):
        print("\n=== Email Ingestion Started ===\n")
        
        print("Clearing existing email data...")
        self.storage.db[config.EMAILS_COLLECTION].delete_many({})
        
        email_files = [f for f in os.listdir(config.EMAILS_DIR) if f.endswith('.txt')]
        print(f"Found {len(email_files)} email files to process\n")
        
        total_emails = 0
        
        with tqdm(total=len(email_files), desc="Processing files", unit="file") as file_pbar:
            for file in email_files:
                filepath = os.path.join(config.EMAILS_DIR, file)
                
                try:
                    file_pbar.set_postfix_str(f"Parsing {file} with LLM...")
                    emails = self.parser.parse_email_file(filepath)
                    file_pbar.set_postfix_str(f"Current: {file} ({len(emails)} emails)")
                    
                    if emails:
                        with tqdm(total=len(emails), desc=f"  Emails from {file}", leave=False, unit="email") as email_pbar:
                            for email in emails:
                                try:
                                    email_text = f"{email.subject} {email.body}"
                                    if email_text.strip():
                                        email_pbar.set_postfix_str("Generating embedding...")
                                        email.embedding = self.llm.generate_embedding(email_text)
                                    else:
                                        email.embedding = []
                                    
                                    doc = email.to_dict()
                                    email_id = self.storage.insert_one(config.EMAILS_COLLECTION, doc)
                                    email.id = email_id
                                    total_emails += 1
                                    
                                    email_pbar.update(1)
                                    
                                except Exception as e:
                                    self.logger.error(f"Error processing email: {str(e)}")
                                    email_pbar.update(1)
                                    
                except Exception as e:
                    self.logger.error(f"Error parsing file {file}: {str(e)}")
                    
                file_pbar.update(1)
                
        print(f"\n=== Ingestion Complete ===")
        print(f"Total emails ingested: {total_emails}")
        print(f"Files processed: {len(email_files)}")
        
        return total_emails