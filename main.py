import datetime
import requests
from ics import Calendar, Event
from zoneinfo import ZoneInfo

API_URL = "https://ws.ticketingcine.com/site"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Content-Type": "application/json",
    "Accept": "application/json",
    "Origin": "https://www.ticketingcine.com",
    "Referer": "https://www.ticketingcine.com/"
}


CINEMAS = [
    {
        "name": "Cinémathèque de Toulouse",
        "site_id": "EMS1135",
        "address": "69 Rue du Taur, 31000 Toulouse",
        "filename": "cinematheque_toulouse.ics",
        "prefix_emoji": "🏛️"
    },
    {
        "name": "ABC",
        "site_id": "EMS0947",
        "address": "13 rue Saint-Bernard, 31000 Toulouse",
        "filename": "abc.ics",
        "prefix_emoji": "🔤"
    },
    {
        "name": "Le Cratère",
        "site_id": "EMS0011",
        "address": "95 Grande Rue Saint-Michel, 31400 Toulouse",
        "filename": "cratere.ics",
        "prefix_emoji": "🌋"
    },
    # {
    #     "name": "Pathé Wilson",
    #     "site_id": "CHN0063",
    #     "address": "3 Place du Président Thomas Wilson, 31000 Toulouse",
    #     "filename": "pathe_wilson.ics",
    #     "prefix_emoji": "🍿"
    # },
]

def fetch_schedule(site_id):
    payload = {
        "jsonrpc": "2.0",
        "method": "get_prog",
        "params": {
            "site_id": site_id
        },
        "id": 1
    }
    
    try:
        response = requests.post(API_URL, json=payload, headers=HEADERS, timeout=10)
        response.raise_for_status()
        
        return response.json().get("result", {}).get("schedule", {}).get("events", [])
    except Exception as e:
        print(f"Erreur lors de la récupération pour {site_id} : {e}")
        return []

def generate_cinema_calendar(cinema_info):
    site_id = cinema_info["site_id"]
    cinema_name = cinema_info["name"]
    cinema_address = cinema_info["address"]
    filename = cinema_info["filename"]
    emoji = cinema_info.get("prefix_emoji", "🎬")

    print(f"\nTraitement de : {cinema_name}")
    events = fetch_schedule(site_id)
    
    cal = Calendar()
    seances_count = 0

    for film in events:
        title = film.get("title", "Film inconnu")
        director = film.get("director", "")
        duration = int(film.get("duration") or 120)
        synopsis = film.get("synopsis", "")
        genre = film.get("kind", "")
        
        sessions = film.get("sessions", [])
        
        for session in sessions:
            date_raw = session.get("date")
            hall_name = session.get("hall_name", "")
            display_features = session.get("display_features", [])
            version = "VF" if "vf" in display_features else "VOST"
            booking_url = session.get("booking_url", "")

            if not date_raw or len(date_raw) != 12:
                continue

            try:
                start_dt = datetime.datetime.strptime(date_raw, "%Y%m%d%H%M")
                local_dt = start_dt.replace(tzinfo=ZoneInfo("Europe/Paris"))
                
                event = Event()
                event.name = f"{title} ({version})"

                event.begin = local_dt
                event.duration = datetime.timedelta(minutes=duration)
                event.location = f"{cinema_name} ({hall_name}), {cinema_address}"
                
                desc_parts = [
                    f"{hall_name}",
                    f"\nRéalisateur : {director}",
                    f"\n{synopsis}",
                    f"\nRéservervation : {booking_url}",
                ]
                event.description = "\n".join(desc_parts)

                cal.events.add(event)
                seances_count += 1

            except Exception as e:
                print(f"Erreur sur une séance du film '{title}' : {e}")

    with open(filename, "w", encoding="utf-8") as f:
        f.writelines(cal.serialize_iter())

    print(f"Fichier '{filename}' généré avec {seances_count} séances.")

def main():
    print("Génération des calendriers par cinéma...")

    for cinema in CINEMAS:
        generate_cinema_calendar(cinema)

    print("\nTous les fichiers agendas mis à jour avec succès !")

if __name__ == "__main__":
    main()
