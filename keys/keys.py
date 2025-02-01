import os
from dotenv import load_dotenv

#* Get environment
load_dotenv(".env")
environment = os.getenv("ENVIRONMENT", "development")  # Default to 'development'

#* laod proper environment file
dotenv_file = f".env.{environment}"
load_dotenv(dotenv_file)

#! Server URLs -----------------------------------------------
#* MongoDB Connection ----------------------------------------
mongo_uri = os.getenv("MONGO_URI")

#* Chroma Connection -----------------------------------------
chroma_host = os.getenv("CHROMA_HOST")
chroma_port = os.getenv("CHROMA_PORT")

#! Keys -----------------------------------------------------
#* Aws keys -------------------------------------------------
aws_access_key_id = os.getenv("AWS_ACCESS_KEY_ID")
aws_secret = os.getenv("AWS_SECRET")