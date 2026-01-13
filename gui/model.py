import os
import json
from datetime import datetime

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../data/session_cache'))

class ChargePointModel:
    def list_years(self):
        print('model.py: DATA_DIR =', DATA_DIR)
        years = []
        if not os.path.isdir(DATA_DIR):
            print('model.py: DATA_DIR does not exist')
            return []
        for name in os.listdir(DATA_DIR):
            if name.isdigit():
                years.append(name)
        print('model.py: years found =', years)
        return sorted(years)

    def list_months(self, year):
        path = os.path.join(DATA_DIR, year)
        if not os.path.isdir(path):
            print(f'model.py: year path {path} does not exist')
            return []
        months = [m for m in os.listdir(path) if m.isdigit()]
        print(f'model.py: months for {year} =', months)
        return sorted(months)

    def list_sessions(self, year, month):
        path = os.path.join(DATA_DIR, year, month)
        if not os.path.isdir(path):
            print(f'model.py: month path {path} does not exist')
            return []
        files = [f for f in os.listdir(path) if f.endswith('.json')]
        print(f'model.py: sessions for {year}-{month} =', files)
        return [f[:-5] for f in files]

    def get_session(self, year, month, session_id):
        path = os.path.join(DATA_DIR, year, month, f'{session_id}.json')
        if not os.path.isfile(path):
            return None
        with open(path, 'r') as f:
            return json.load(f)
