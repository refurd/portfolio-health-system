# /home/gyorkosdominik/_work/portfolio-health-system/core/processors/email_parser.py
import json
from typing import List, Dict, Any, Optional
from core.models.email import Email
from core.interfaces.llm import LLMInterface
import config
from datetime import datetime
import re

class EmailParser:
    def __init__(self, llm: Optional[LLMInterface] = None):
        self.llm = llm
        self.colleagues = self._load_colleagues()
        
    def _load_colleagues(self) -> Dict[str, str]:
        colleagues = {}
        try:
            with open(config.COLLEAGUES_FILE, 'r', encoding='utf-8') as f:
                for line in f:
                    if '@kisjozsitech.hu' in line:
                        match = re.search(r'([^:]+?)\s*\(([^@]+@kisjozsitech\.hu)\)', line)
                        if match:
                            name, email = match.groups()
                            colleagues[email.strip()] = name.strip()
        except:
            pass
        return colleagues
        
    def parse_email_file(self, filepath: str) -> List[Email]:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            
        if not self.llm:
            raise ValueError("LLM instance required for parsing")
            
        # Use LLM to parse the email content WITH REPLY DETECTION
        emails_data = self._parse_with_llm(content)
        
        emails = []
        for email_data in emails_data:
            email = self._create_email_from_parsed_data(email_data)
            if email:
                emails.append(email)
                
        return emails
        
    def _parse_with_llm(self, content: str) -> List[Dict[str, Any]]:
        prompt = f"""Parse the following email file content and extract individual emails WITH REPLY RELATIONSHIPS. 

CRITICAL TASKS:
1. Extract all individual emails from the content
2. Identify which email is replying to which (look for Re:, Fwd:, quoted text, references)
3. Extract questions that need answers
4. Identify if questions have been answered in subsequent emails

Return a JSON array where each email object contains:
- subject: string
- date: string (in format YYYY-MM-DD HH:MM:SS)
- from_email: string
- from_name: string
- to_emails: array of email addresses
- cc_emails: array of email addresses (if any)
- body: string (the full email body)
- attachments: array of attachment paths (if mentioned)
- is_reply_to_subject: string (the original subject this is replying to, if any)
- replying_to_date: string (date of the email being replied to, if identifiable)
- replying_to_from: string (sender of the email being replied to)
- questions_asked: array of objects with format {{"question": "text", "needs_answer": true/false}}
- answers_provided: array of objects with format {{"answer": "text", "answers_question": "the question being answered"}}
- quoted_text: string (any quoted text from previous emails)

Email content:
{content}

Return ONLY the JSON array, no other text."""

        try:
            response = self.llm.generate(prompt, temperature=0.1)
            # Clean the response to ensure valid JSON
            response = response.strip()
            if response.startswith('```json'):
                response = response[7:]
            if response.endswith('```'):
                response = response[:-3]
            response = response.strip()
            
            parsed = json.loads(response)
            if isinstance(parsed, list):
                return parsed
            return []
        except Exception as e:
            print(f"Error parsing with LLM: {str(e)}")
            return []
            
    def _create_email_from_parsed_data(self, data: Dict[str, Any]) -> Optional[Email]:
        try:
            # Parse date
            date_str = data.get('date', '')
            date = None
            if date_str:
                try:
                    date = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
                except:
                    # Try other formats
                    for fmt in ['%Y.%m.%d %H:%M', '%Y-%m-%d %H:%M', '%Y.%m.%d %H:%M:%S']:
                        try:
                            date = datetime.strptime(date_str, fmt)
                            break
                        except:
                            continue
                            
            if not date:
                return None
                
            # Ensure email lists
            to_emails = data.get('to_emails', [])
            if isinstance(to_emails, str):
                to_emails = [to_emails]
            cc_emails = data.get('cc_emails', [])
            if isinstance(cc_emails, str):
                cc_emails = [cc_emails]
                
            # Extract attachment paths from body if not provided
            attachments = data.get('attachments', [])
            body = data.get('body', '')
            if not attachments and 'Attachments:' in body:
                att_match = re.search(r'Attachments:\s*([^\n]+)', body)
                if att_match:
                    att_text = att_match.group(1)
                    attachments = [a.strip() for a in att_text.split(',')]
                    
            # Check if internal
            all_emails = [data.get('from_email', '')] + to_emails + cc_emails
            is_internal = all(e.endswith('@kisjozsitech.hu') for e in all_emails if e)
            
            # Store reply information and Q&A in metadata
            metadata = {
                'is_reply_to_subject': data.get('is_reply_to_subject'),
                'replying_to_date': data.get('replying_to_date'),
                'replying_to_from': data.get('replying_to_from'),
                'questions_asked': data.get('questions_asked', []),
                'answers_provided': data.get('answers_provided', []),
                'quoted_text': data.get('quoted_text', '')
            }
            
            return Email(
                id=None,
                subject=data.get('subject', ''),
                date=date,
                from_email=data.get('from_email', ''),
                from_name=data.get('from_name', ''),
                to_emails=to_emails,
                cc_emails=cc_emails,
                body=body,
                attachments=attachments,
                thread_id=None,
                is_internal=is_internal,
                embedding=None,
                metadata=metadata
            )
        except Exception as e:
            print(f"Error creating email from parsed data: {str(e)}")
            return None