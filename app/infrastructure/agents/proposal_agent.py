from importlib import metadata
import uuid
from sqlalchemy.orm import Session
from agents import Agent

from app.infrastructure.prompts.proposal_prompts import get_proposal_prompt
from app.infrastructure.repository.business_repository import BusinessRepository


class ProposalAgent:
    def __init__(self, model: str, business_id: str, db: Session):
        self.model = model
        self.db = db
        self.business_id = business_id
        
    def generate_agent_id(self) -> str:
        return str(uuid.uuid4())

    def get_or_create_agent(self) -> Agent:
        business_repo = BusinessRepository(self.db)
        business = business_repo.get_by_id(self.business_id)
        assistant_id = self.generate_agent_id()
        
        if business is None:
            raise ValueError("Business not found")

        chat_agent = Agent(
            name=assistant_id,
            instructions=get_proposal_prompt(business),
            model=self.model
        )
        
        return chat_agent
    
    async def process_message(self, conversation_id: str, data: dict):
        # TODO: Implement this method
        pass