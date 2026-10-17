import requests
from dotenv import load_dotenv
import os
import json

load_dotenv()

class Extrac():
    def __init__(self):
        self.API_KEY = os.getenv("API_KEY")
        self.url = "https://api.openagenda.com/v2/requestAccessToken"
        self.url_read_events = "https://api.openagenda.com/v2/events"
        self.params = {}
        #self.token = self._get_token(self.API_KEY)

    # def _get_token(self, api_key: str) -> dict:
        
    #     headers = {"Content-Type": "application/json; charset=utf-8"}
    #     data = {"code": self.API_KEY}

    #     # A POST request to the API
    #     response = requests.post(self.url, headers=headers,json=data)
        
    #     return response.json()

    def _extrac_events(self, params: dict = None) -> dict:
        if params is None:
            params = {}

        # Ajout automatique de la clé API aux paramètres
        query_params = {"key": self.API_KEY, **params}

        # Requête GET correctement formatée
        response = requests.get(
            self.url_read_events,
            headers={"key": self.API_KEY},
            params=params,
            timeout=30,
        )

        # Afficher le message du serveur AVANT de lever l'exception
        if not response.ok:
            print("Statut :", response.status_code)
            print("Détail :", response.text)

        # Lève une exception en cas d'erreur HTTP (ex: 403, 500)
        response.raise_for_status()

        return response.json()

    def write_json(self, json_file: dict) -> json:

        with open("openAgendaData.json", "w") as file:
            json.dump(json_file, file, indent=4, sort_keys=True)
        


runner = Extrac()

# Utilisation de "city[]" pour le filtre de ville
# data = runner._extrac_events(params={
#         "adminLevel2[]": ["Hauts-de-Seine", "Paris", "Seine-et-Marne", "Yvelines", "Essonne", "Seine-Saint-Denis", "Val-de-Marne ", "Val-d'Oise"],
#         "timings[gte]":"2025-10-17:00:00.000Z",
#         "relative[]": ["passed", "current", "upcoming"],
#         "size":300
#     })

data = runner._extrac_events(params={
        "adminLevel4[]": "Serris",
        #"timings[gte]":"2025-10-17:00:00.000Z",
        "relative[]": ["current", "upcoming"],
        "size":1,
        "after":[],
    })

def test_batch():
    
    runner = Extrac()
    r = 1
    after_is_null = False
    data_conso = {"after":[],"events":[],"sort":None, "success":None, "total":None}

    while after_is_null is not True:
        
        data = runner._extrac_events(params={
            "adminLevel4[]": "Serris",
            #"timings[gte]":"2025-10-17:00:00.000Z",
            "relative[]": ["current", "upcoming"],
            "size":1,
            "after":data_conso["after"],
        })

        total = data["total"]

        if r <= total:
            print(f"request : {r} / {total}")
            r = r + 1

        after_is_null = data["after"] is None

        data_conso.update({
            "after":data["after"],
            "sort":data["sort"],
            "success":data["success"],
        })

        data_conso["events"].extend(data["events"])

    runner.write_json(data_conso)

test_batch()

#runner.write_json(data)





