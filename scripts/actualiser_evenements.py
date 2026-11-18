
import json
import os
import sys
from datetime import date, datetime
from urllib.parse import urljoin

import requests

API_URL = "https://api.datatourisme.fr/v1/entertainmentAndEvent"
API_KEY = os.environ.get("DATATOURISME_API_KEY")

if not API_KEY:
    sys.exit("Erreur : le secret DATATOURISME_API_KEY est absent.")

def first_text(value):
    """Récupère un texte lisible dans les champs multilingues."""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        for item in value:
            result = first_text(item)
            if result:
                return result
    if isinstance(value, dict):
        for key in ("fr", "value", "label", "text"):
            if key in value:
                result = first_text(value[key])
                if result:
                    return result
    return ""

def find_value(data, wanted_keys):
    """Recherche une valeur dans un objet JSON imbriqué."""
    if isinstance(data, dict):
        for key in wanted_keys:
            if key in data:
                value = data[key]
                if isinstance(value, (str, int, float)):
                    return str(value)
        for value in data.values():
            result = find_value(value, wanted_keys)
            if result:
                return result
    elif isinstance(data, list):
        for item in data:
            result = find_value(item, wanted_keys)
            if result:
                return result
    return ""

def get_date(event):
    periods = event.get("takesPlaceAt", [])
    if isinstance(periods, dict):
        periods = [periods]

    for period in periods:
        start = period.get("startDate", "")
        end = period.get("endDate", "")
        if start:
            return start[:10], end[:10] if end else start[:10]

    return "", ""

def main():
    headers = {
        "X-API-Key": API_KEY,
        "Accept": "application/json"
    }
    
    params = {
        "lang": "fr",
        "page": 1,
        "page_size": 100,
        "fields": "uuid,uri,label,isLocatedAt.address,hasDescription,takesPlaceAt",
        "filters": "isLocatedAt.address.hasAddressCity.isPartOfDepartment.insee[eq]=41"
    }
    
    events = []
    url = API_URL
    while url:
        response = requests.get(
            url,
            headers=headers,
            params=params if url == API_URL else None,
            timeout=60
        )
        response.raise_for_status()
        payload = response.json()

    for item in payload.get("objects", []):
        title = first_text(item.get("label"))
        start, end = get_date(item)

        if not title or not start:
                continue

        try:
            if end and end < date.today().isoformat():
                    continue
            if not end and start < date.today().isoformat():
                    continue
        except ValueError:
                continue

        description = first_text(item.get("hasDescription"))
        city = find_value(item.get("isLocatedAt", {}), [
                "addressLocality", "name"
         ])

            events.append({
                "title": title,
                "city": city or "Loir-et-Cher",
                "desc": description,
                "startDate": start,
                "endDate": end,
                "url": item.get("uri", ""),
                "category": "Événement",
                "season": "",
            })

        next_page = payload.get("meta", {}).get("next")
        url = urljoin("https://api.datatourisme.fr", next_page) if next_page else None

        params = None

    events.sort(key=lambda event: event["startDate"])

    with open("events.json", "w", encoding="utf-8") as file:
        json.dump(events, file, ensure_ascii=False, indent=2)

    print(f"{len(events)} événements à venir enregistrés.")

if __name__ == "__main__":
    main()
