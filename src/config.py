import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    TIMEZONE = os.getenv("TIMEZONE", "Europe/Paris")

    MAIL_SMTP_HOST = os.getenv("MAIL_SMTP_HOST", "smtp.gmail.com")
    MAIL_SMTP_PORT = int(os.getenv("MAIL_SMTP_PORT", 587))
    MAIL_SMTP_USER = os.getenv("MAIL_SMTP_USER")
    MAIL_SMTP_PASSWORD = os.getenv("MAIL_SMTP_PASSWORD")

    HF_API_TOKEN = os.getenv("HF_API_TOKEN")
    MODEL_ID = os.getenv("MODEL_ID", "meta-llama/Meta-Llama-3-8B-Instruct")
    MAX_TOKENS = int(os.getenv("MAX_TOKENS") or 3000)
