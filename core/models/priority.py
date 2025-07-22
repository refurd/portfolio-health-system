from dataclasses import dataclass
from datetime import datetime
from typing import List, Dict, Any, Optional
from bson import ObjectId

@dataclass
class Priority:
    id: Optional[str]
    email_id: str
    thread_id: str
    score: float
    attention_flags: Dict[str, float]
    issues: List[Dict[str, Any]]
    recommendations: List[str]
    days_stalled: int
    last_activity: datetime
    participants: List[str]
    external_participants: List[str]
    attachments: List[str]
    created_at: datetime
    validation_scores: List[float]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'email_id': self.email_id,
            'thread_id': self.thread_id,
            'score': self.score,
            'attention_flags': self.attention_flags,
            'issues': self.issues,
            'recommendations': self.recommendations,
            'days_stalled': self.days_stalled,
            'last_activity': self.last_activity.isoformat() if isinstance(self.last_activity, datetime) else self.last_activity,
            'participants': self.participants,
            'external_participants': self.external_participants,
            'attachments': self.attachments,
            'created_at': self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at,
            'validation_scores': self.validation_scores
        }