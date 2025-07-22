import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path("/home/gyorkosdominik/_work/portfolio-health-system")
DATA_DIR = PROJECT_ROOT / "data"
EMAILS_DIR = DATA_DIR / "emails"
COLLEAGUES_FILE = DATA_DIR / "Colleagues.txt"
ATTACHMENTS_DIR = DATA_DIR / "s3" / "attachments"

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
MONGO_CONNECTION_STRING = os.getenv("MONGO_CONNECTION_STRING")

DATABASE_NAME = "portfolio_health"
EMAILS_COLLECTION = "emails"
THREADS_COLLECTION = "threads"
PRIORITIES_COLLECTION = "priorities"
COLLEAGUES_COLLECTION = "colleagues"

RESPONSE_TRACKING_ENABLED = True
MAX_DAYS_WITHOUT_RESPONSE = 3
CRITICAL_DAYS_WITHOUT_RESPONSE = 7

EMBEDDING_MODEL = "text-embedding-3-small"
LLM_MODEL = "gpt-4.1-mini"
VALIDATOR_MODEL = "claude-3-5-sonnet-20240620"

VALIDATION_ROUNDS = 1
PRIORITY_THRESHOLD = 0.7
THREAD_SIMILARITY_THRESHOLD = 0.85

ATTENTION_FLAGS = [
    "unresolved_questions",
    "blocked_projects", 
    "escalated_issues",
    "external_risks",
    "deadline_risks",
    "missing_responses",
    "technical_debt",
    "security_concerns"
]

LOG_LEVEL = "INFO"
LOG_FILE = PROJECT_ROOT / "app.log"