from typing import Dict, Any, Optional, List
from dataclasses import dataclass

@dataclass
class AgentResponse:
    response: str
    resolved: bool
    category: str
    confidence: float = 0.5
    needs_followup: bool = False
    needs_more_info: bool = False
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "response": self.response,
            "resolved": self.resolved,
            "category": self.category,
            "confidence": self.confidence,
            "needs_followup": self.needs_followup,
            "needs_more_info": self.needs_more_info,
            "metadata": self.metadata or {}
        }