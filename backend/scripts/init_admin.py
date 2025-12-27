import asyncio
import logging
import secrets
import string

from sqlalchemy import select

from app.core.database import async_session, init_db
from app.core.security import get_password_hash
from app.models.user import User

# Configure logging to print to stdout
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def generate_password(length=12):
    """Generate a secure random password"""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for i in range(length))

async def init_admin():
    # 1. Initialize Database Tables
    logger.info("Initializing database tables...")
    await init_db()
    
    # 2. Check and Create Admin User
    async with async_session() as session:
        # Check if any user exists
        result = await session.execute(select(User))
        user = result.scalars().first()
        
        if not user:
            logger.info("No users found. Creating default admin user...")
            
            # Generate random credentials
            admin_password = generate_password()
            admin_email = "admin@example.com"
            
            # Create admin user
            new_admin = User(
                email=admin_email,
                username="admin",
                password_hash=get_password_hash(admin_password),
                role="admin",
                is_active=True
            )
            
            session.add(new_admin)
            await session.commit()
            
            # Print credentials prominently - this is what the user asked for
            print("\n" + "="*60)
            print("🎉  INITIAL SETUP COMPLETED")
            print("="*60)
            print("Admin User Created:")
            print("Username: admin")
            print(f"Password: {admin_password}")
            print("="*60 + "\n")
        else:
            logger.info("Users already exist. Skipping admin creation.")

if __name__ == "__main__":
    asyncio.run(init_admin())
