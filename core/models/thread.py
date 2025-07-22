from dataclasses import dataclass
from datetime import datetime
from typing import List, Dict, Any, Optional

@dataclass
class Thread:
    id: Optional[str]
    email_ids: List[str]
    subject: str
    participants: List[str]
    external_participants: List[str]
    start_date: datetime
    last_activity: datetime
    status: str
    priority_score: float
    unresolved_questions: List[Dict[str, Any]]
    blockers: List[Dict[str, Any]]
    attachments: List[str]
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'email_ids': self.email_ids,
            'subject': self.subject,
            'participants': self.participants,
            'external_participants': self.external_participants,
            'start_date': self.start_date.isoformat() if isinstance(self.start_date, datetime) else self.start_date,
            'last_activity': self.last_activity.isoformat() if isinstance(self.last_activity, datetime) else self.last_activity,
            'status': self.status,
            'priority_score': self.priority_score,
            'unresolved_questions': self.unresolved_questions,
            'blockers': self.blockers,
            'attachments': self.attachments,
            'metadata': self.metadata
        }