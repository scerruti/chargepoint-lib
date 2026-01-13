

import json
from .model import ChargePointModel


class ChargePointController:
    def __init__(self):
        self.model = ChargePointModel()

    def get_years(self):
        print('controller.py: get_years called')
        return self.model.list_years()

    def get_months(self, year):
        print(f'controller.py: get_months({year}) called')
        return self.model.list_months(year)

    def get_sessions(self, year, month):
        print(f'controller.py: get_sessions({year}, {month}) called')
        return self.model.list_sessions(year, month)

    def get_session_details(self, year, month, session_id):
        print(f'controller.py: get_session_details({year}, {month}, {session_id}) called')
        return self.model.get_session(year, month, session_id)
