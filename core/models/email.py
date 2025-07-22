from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Dict, Any

@dataclass
class Email:
    id: Optional[str]
    subject: str
    date: datetime
    from_email: str
    from_name: str
    to_emails: List[str]
    cc_emails: List[str]
    body: str
    attachments: List[str]
    thread_id: Optional[str]
    is_internal: bool
    embedding: Optional[List[float]]
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'subject': self.subject,
            'date': self.date.isoformat() if isinstance(self.date, datetime) else self.date,
            'from_email': self.from_email,
            'from_name': self.from_name,
            'to_emails': self.to_emails,
            'cc_emails': self.cc_emails,
            'body': self.body,
            'attachments': self.attachments,
            'thread_id': self.thread_id,
            'is_internal': self.is_internal,
            'embedding': self.embedding,
            'metadata': self.metadata
        }