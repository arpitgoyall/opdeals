import json
import os
from datetime import datetime

STORAGE_FILE = "deals.json"

class Storage:
    def __init__(self):
        if not os.path.exists(STORAGE_FILE):
             with open(STORAGE_FILE, 'w') as f:
                 json.dump([], f)

    def save_deal(self, deal):
        deals = self.get_deals()
        # Add timestamp
        deal['timestamp'] = datetime.now().isoformat()
        deals.append(deal)
        with open(STORAGE_FILE, 'w') as f:
            json.dump(deals, f, indent=4)

    def get_deals(self):
        try:
            with open(STORAGE_FILE, 'r') as f:
                return json.load(f)
        except:
            return []

storage_service = Storage()
