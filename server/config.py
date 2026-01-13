import os
import random
import string

class Config:
    SECRET_KEY = os.environ.get("FLASK_SECRET_KEY")
    if not SECRET_KEY:
        print("WARNING: The FLASK_SECRET_KEY environment variable is not set.")
        print("Using a temporary, insecure key for this session.")
        SECRET_KEY = "".join(random.choices(string.ascii_letters + string.digits, k=32))
    
    # Add other config variables here if needed
    DEBUG = True
