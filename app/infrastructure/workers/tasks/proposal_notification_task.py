import asyncio
import logging

from app.core.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    name="notify_business_of_proposal",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def notify_business_of_proposal(
    self,
    business_id: str,
    proposal_id: str,
    conversation_id: str,
) -> None:
    """
    Notifies the business owner that a new proposal has been generated.
    Runs in a Celery worker process — uses asyncio.run() to bridge sync Celery
    into async SQLAlchemy (get_db_context uses NullPool for worker processes).
    """

    async def _run() -> None:
        from app.infrastructure.database.db import get_db_context
        from app.infrastructure.repository.business_repository import BusinessRepository

        async with get_db_context() as db:
            business_repo = BusinessRepository(db)
            business = await business_repo.get_by_id(business_id)

            if not business:
                logger.warning(f"[proposal={proposal_id}] Business {business_id} not found, skipping notification")
                return

            logger.info(
                f"[proposal={proposal_id}] Notifying business '{business.name}' "
                f"({business.email}) for conversation {conversation_id}"
            )

            # TODO: send email via your email provider (e.g. Resend, SendGrid, SES)
            
            # Send Email to client first to confirm propsal generation, then send to business owner. This ensures the client is informed even if the business notification fails.
            
            # Example structure:
            # await send_email(
            #     to=business.email,
            #     subject="New proposal generated",
            #     body=f"A new proposal (ID: {proposal_id}) was created for conversation {conversation_id}.",
            # )

    try:
        asyncio.run(_run())
    except Exception as exc:
        logger.exception(f"[proposal={proposal_id}] Notification task failed")
        raise self.retry(exc=exc)
