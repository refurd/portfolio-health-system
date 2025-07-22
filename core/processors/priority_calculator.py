from typing import List, Dict, Any
from core.models.thread import Thread
from core.models.priority import Priority
from core.interfaces.llm import LLMInterface
from core.interfaces.validator import ValidatorInterface
from datetime import datetime
import json
import config

class PriorityCalculator:
    def __init__(self, llm: LLMInterface, validator: ValidatorInterface):
        self.llm = llm
        self.validator = validator
        
    def calculate_priorities(self, thread: Thread) -> Priority:
        attention_scores = self._calculate_attention_scores(thread)
        issues = self._identify_issues(thread)
        recommendations = self._generate_recommendations(thread, issues)
        
        priority_data = {
            'thread_id': thread.id,
            'attention_flags': attention_scores,
            'issues': issues,
            'recommendations': recommendations,
            'days_stalled': (datetime.now() - thread.last_activity).days,
            'external_participants': thread.external_participants
        }
        
        validated_scores = []
        for _ in range(config.VALIDATION_ROUNDS):
            validation_result = self.validator.validate(
                priority_data,
                self._get_validation_prompt()
            )
            if validation_result.get('score'):
                validated_scores.append(validation_result['score'])
                
        final_score = sum(validated_scores) / len(validated_scores) if validated_scores else 0.0
        
        return Priority(
            id=None,
            email_id=thread.email_ids[-1] if thread.email_ids else '',
            thread_id=thread.id,
            score=final_score,
            attention_flags=attention_scores,
            issues=issues,
            recommendations=recommendations,
            days_stalled=(datetime.now() - thread.last_activity).days,
            last_activity=thread.last_activity,
            participants=thread.participants,
            external_participants=thread.external_participants,
            attachments=thread.attachments,
            created_at=datetime.now(),
            validation_scores=validated_scores
        )
        
    def _calculate_attention_scores(self, thread: Thread) -> Dict[str, float]:
        prompt = f"""
        Analyze this email thread and score each attention flag from 0 to 1:
        
        Thread Subject: {thread.subject}
        Days Since Last Activity: {(datetime.now() - thread.last_activity).days}
        Unresolved Questions: {len(thread.unresolved_questions)}
        Blockers: {len(thread.blockers)}
        External Participants: {len(thread.external_participants)}
        
        Attention flags to score:
        {json.dumps(config.ATTENTION_FLAGS)}
        
        Return JSON object with scores for each flag.
        """
        
        response = self.llm.generate(prompt, temperature=0.3)
        try:
            scores = json.loads(response)
            return {flag: scores.get(flag, 0.0) for flag in config.ATTENTION_FLAGS}
        except:
            return {flag: 0.0 for flag in config.ATTENTION_FLAGS}
            
    def _identify_issues(self, thread: Thread) -> List[Dict[str, Any]]:
        prompt = f"""
        Identify critical issues in this thread:
        
        Subject: {thread.subject}
        Unresolved Questions: {json.dumps(thread.unresolved_questions)}
        Blockers: {json.dumps(thread.blockers)}
        Days Stalled: {(datetime.now() - thread.last_activity).days}
        
        Return JSON array of issues with format:
        [
            {{
                "type": "issue type",
                "severity": "critical/high/medium/low",
                "description": "detailed description",
                "impact": "business impact"
            }}
        ]
        """
        
        response = self.llm.generate(prompt, temperature=0.3)
        try:
            return json.loads(response)
        except:
            return []
            
    def _generate_recommendations(self, thread: Thread, issues: List[Dict[str, Any]]) -> List[str]:
        prompt = f"""
        Generate actionable recommendations for these issues:
        
        Thread: {thread.subject}
        Issues: {json.dumps(issues)}
        
        Return JSON array of brief, actionable recommendations.
        """
        
        response = self.llm.generate(prompt, temperature=0.5)
        try:
            return json.loads(response)
        except:
            return []
            
    def _get_validation_prompt(self) -> str:
        return """
        Validate this priority assessment and provide a confidence score (0-1).
        Consider:
        - Are the attention flags accurately scored?
        - Are all critical issues identified?
        - Are the recommendations actionable?
        - Is the severity assessment correct?
        
        Return JSON with:
        {
            "score": 0.0-1.0,
            "concerns": ["list of concerns if any"],
            "suggestions": ["improvement suggestions"]
        }
        """