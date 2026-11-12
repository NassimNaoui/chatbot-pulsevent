from dotenv import load_dotenv
from pathlib import Path
import os



class Config:
    def __init__(self):
        
        # --- ENV ---
        load_dotenv()
        
        # --- REPO ---
        self.CURRENT_DIR = Path(__file__).resolve().parent
        self.SRC_DIR = self.CURRENT_DIR.parent
        self.ROOT_DIR = self.SRC_DIR.parent

        # --- DATA PATH ---
        self.RAW_DATA_DIR = self.ROOT_DIR / 'data' / 'raw'
        self.PROCESSED_DATA_DIR = self.ROOT_DIR / 'data' / 'processed'

        # --- API KEY ---
        self.OPENAGENDA_API_KEY = os.environ.get("OPENAGENDA_API_KEY")
        self.MISTRAL_API_KEY = os.environ.get("MISTRAL_API_KEY")
