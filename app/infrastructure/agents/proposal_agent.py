import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from agents import Agent, Runner, TResponseInputItem, function_tool
from app.infrastructure.repository.business_repository import BusinessRepository
from app.infrastructure.repository.conversation_repository import ConversationRepository
from app.infrastructure.repository.message_repository import MessageRepository
from app.infrastructure.repository.pricing_config_repository import PricingConfigRepository
from app.models.entity import knowledge_base
from app.models.entity.conversation import ConversationEntity
from app.models.entity.message import MessageEntity
from app.models.enums.chat_roles import ChatRoles
import json


class ProposalAgent:
    def __init__(self, model: str, db: AsyncSession):
        self.model = model
        self.db = db
        self.runner = Runner()
        
    def generate_agent_id(self) -> str:
        return str(uuid.uuid4())

    async def get_or_create_agent(self, conversation: ConversationEntity) -> Agent:
        assistant_id = self.generate_agent_id()

        instructions = await self._build_proposal_system_prompt(conversation.business_id)
        chat_agent = Agent(
            name=assistant_id,
            instructions=instructions,
            model=self.model,
            tools=[self.get_business_services_and_pricings]
        )
        
        return chat_agent
    
    def build_agent_messages(self, messages: list[MessageEntity]) -> list[TResponseInputItem]:
        return [
            {
                "role": msg.role,
                "content": msg.content
            }
            for msg in sorted(messages, key=lambda x: x.timestamp)
        ]
        
    
    async def process_message(self, conversation_id: str, data: dict):
        conversation_repo = ConversationRepository(self.db)
        message_repo = MessageRepository(self.db)
        conversation = await conversation_repo.get_by_id(conversation_id, include_relations=True)
        
        if not conversation:
            raise ValueError("Conversation not found")
        
        agent = await self.get_or_create_agent(conversation)
        
        user_message = data["message"]
        
        await message_repo.create(conversation_id=conversation_id, role=ChatRoles.USER, content=user_message)
        
        messages = self.build_agent_messages(conversation.messages)
        
        result = await self.runner.run(agent, input=messages)
        
        ai_response = result.final_output
        
        await message_repo.create(conversation_id=conversation_id, role=ChatRoles.ASSISTANT, content=ai_response)
        
        return {
            "role": ChatRoles.ASSISTANT,
            "content": ai_response
        }
    
    @function_tool
    async def get_business_services_and_pricings(self, business_id: str):
       pricing_config_repo = PricingConfigRepository(self.db)
       return await pricing_config_repo.get_services_by_business_id(business_id)
   
   
    def create_proposal(self, business_id: str, data: dict):
        # TODO: Implement proposal creation logic
        pass
    
    
    
    async def _build_proposal_system_prompt(self, business_id: str) -> str:
        business = await BusinessRepository(self.db).get_by_id(business_id, include_relations=True)
        
        if not business:
            raise ValueError("Business not found")
        
        context = f"Pricing Configuration: {json.dumps(business.pricing_config['config_json'])}\n\n"
        
        if len(business.knowledge_base) > 0:
            context += "Knowledge Base:\n"
            for kb in business.knowledge_base:
                context += f"- {kb.content[:500]}...\n"
        
        return f"""
                You are a helpful assistant for {business.name} that helps gather requirements for service proposals. your job is to:

                1. Understand what service the customer needs
                2. Ask clarifying questions about their requirements
                3. Suggest relevant packages from the pricing list
                4. Negotiate within reasonable bounds
                5. Once you have enough information, generate a detailed proposal

                Always be professional, friendly and helpful.
                
                use the context and knowledge base for {business.name} below to help you answer questions and generate proposals.
                
                {context}
                """