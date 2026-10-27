import requests
from dotenv import load_dotenv
import os
import json
import math
import time

load_dotenv()


class Extrac:
    def __init__(self):
        self.API_KEY = os.getenv("API_KEY")
        self.url = "https://api.openagenda.com/v2/requestAccessToken"
        self.url_read_events = "https://api.openagenda.com/v2/events"
        self.after_array = []
        self.params = {
            "adminLevel2[]": [
                "Hauts-de-Seine",
                "Paris",
                "Seine-et-Marne",
                "Yvelines",
                "Essonne",
                "Seine-Saint-Denis",
                "Val-de-Marne",
                "Val-d'Oise",
            ],
            "timings[gte]": "2025-10-17T00:00:00.000Z",
            "relative[]": ["passed", "current", "upcoming"],
            "size": 300,
            "after": self.after_array,
        }
    
    def process_batch(self) -> dict:
        """Extrait toutes les pages, avec trois tentatives par page.
        """
        max_attempts = 3
        self.after_array = []
        self.params["after"] = self.after_array
        data_conso = {
            "after": [],
            "events": [],
            "sort": None,
            "success": None,
            "total": None,
        }
        request_number = 1
        seen_cursors = set()

        while True:
            for attempt in range(1, max_attempts + 1):
                try:
                    data = self.extrac_events(params=self.params)
                    break
                except (requests.Timeout, requests.ConnectionError,
                        requests.HTTPError) as exc:
                    # Les erreurs permanentes (ex. 401/403) ne sont pas retentées.
                    if isinstance(exc, requests.HTTPError):
                        status = exc.response.status_code if exc.response is not None else None
                        if status not in (408, 429) and not (status is not None and status >= 500):
                            raise
                    if attempt == max_attempts:
                        raise
                    delay = 2 ** (attempt - 1)
                    print(f"Page {request_number}, tentative {attempt}/{max_attempts} "
                          f"échouée. Nouvelle tentative dans {delay} s.")
                    time.sleep(delay)

            # Valider la page avant de l'ajouter aux données consolidées.
            if not isinstance(data, dict) or data.get("success") is not True:
                raise ValueError("OpenAgenda n'a pas confirmé le succès de la requête.")
            if "after" not in data or not isinstance(data.get("events"), list):
                raise ValueError("Réponse OpenAgenda invalide : after ou events manquant/invalide.")

            next_after = data["after"]
            if next_after is not None:
                cursor_key = json.dumps(next_after, sort_keys=True)
                if cursor_key in seen_cursors:
                    raise ValueError("Curseur OpenAgenda répété : pagination interrompue.")
                seen_cursors.add(cursor_key)

            data_conso["events"].extend(data["events"])
            data_conso.update({
                "after": next_after,
                "sort": data.get("sort"),
                "success": data["success"],
                "total": data.get("total"),
            })

            total = data.get("total")
            if isinstance(total, int) and total >= 0:
                total_requests = max(1, math.ceil(total / self.params["size"]))
                print(f"request : {request_number} / {total_requests}")
            else:
                print(f"request : {request_number}")

            self.after_array = next_after
            self.params["after"] = next_after
            if next_after is None:
                return data_conso
            request_number += 1

    def extrac_events(self, params: dict = None) -> dict:
        if params is None:
            params = {}

        # Requête GET 
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

    def write_json(self, json_file: dict) -> None:

        with open("openAgendaData.json", "w", encoding="utf-8") as file:
            json.dump(json_file, file, indent=4, sort_keys=True)


def test_batch():

    runner = Extrac()
    r = 1
    after_is_null = False
    data_conso = {
        "after": [],
        "events": [],
        "sort": None,
        "success": None,
        "total": None,
    }

    while after_is_null is not True:
        data = runner.extrac_events(
            params={
                "adminLevel4[]": "Serris",
                # "timings[gte]":"2025-10-17T00:00:00.000Z",
                "relative[]": ["current", "upcoming"],
                "size": 1,
                "after": data_conso["after"],
            }
        )

        total = data["total"]

        if r <= total:
            print(f"request : {r} / {total}")
            r = r + 1

        after_is_null = data["after"] is None

        data_conso.update(
            {
                "after": data["after"],
                "sort": data["sort"],
                "success": data["success"],
            }
        )

        data_conso["events"].extend(data["events"])

    runner.write_json(data_conso)


if __name__ == "__main__":
    runner = Extrac()
    data = runner.process_batch()
    runner.write_json(data)
