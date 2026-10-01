import datetime
import os
import requests
from ics import Calendar, Event
from zoneinfo import ZoneInfo

CINEOFFICE_TOKEN = os.environ.get("CINEOFFICE_TOKEN", "4a55fe53-3b66-4c25-88f9-340b4381ada2")

TICKETINGCINE_API_URL = "https://ws.ticketingcine.com/site"

os.makedirs("dist", exist_ok=True)


CINEMAS = [
    {
        "name": "Cinémathèque de Toulouse",
        "source": 'ticketingcine',
        "site_id": "EMS1135",
        "address": "69 Rue du Taur, 31000 Toulouse",
        "filename": "cinematheque_toulouse.ics",
        "prefix_emoji": "🏛️"
    },
    {
        "name": "ABC",
        "source": 'ticketingcine',
        "site_id": "EMS0947",
        "address": "13 rue Saint-Bernard, 31000 Toulouse",
        "filename": "abc.ics",
        "prefix_emoji": "🔤"
    },
    {
        "name": "Le Cratère",
        "source": 'ticketingcine',
        "site_id": "EMS0011",
        "address": "95 Grande Rue Saint-Michel, 31400 Toulouse",
        "filename": "cratere.ics",
        "prefix_emoji": "🌋"
    },
    {
        "name": "American Cosmograph",
        "source": 'cineoffice',
        "media_api_url": f"https://toulousecosmograph.cineoffice.fr/vad/media?api_token={CINEOFFICE_TOKEN}&allCinemas=false",
        "shows_api_url": f"https://toulousecosmograph.cineoffice.fr/vad/shows?api_token={CINEOFFICE_TOKEN}&allCinemas=false",
        "booking_url": "https://toulousecosmograph.cine.boutique/media/",
        "address": "24 Rue Montardy, 31000 Toulouse",
        "filename": "american_cosmograph.ics",
        "prefix_emoji": "🦑"
    },
    # {
    #     "name": "Pathé Wilson",
    #     "site_id": "CHN0063",
    #     "address": "3 Place du Président Thomas Wilson, 31000 Toulouse",
    #     "filename": "pathe_wilson.ics",
    #     "prefix_emoji": "🍿"
    # },
]

def generate_cineoffice_calendar(cinema):
    cinema_name = cinema["name"]
    cinema_address = cinema["address"]
    filename = cinema["filename"]
    emoji = cinema.get("prefix_emoji")

    print(f"\nTraitement CineOffice : {cinema_name}")

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json"
    }

    try:
        res_media = requests.get(cinema["media_api_url"], headers=headers, timeout=10)
        res_media.raise_for_status()
        medias_list = res_media.json()
        
        media_catalog = {m["id"]: m for m in medias_list if "id" in m}

        res_shows = requests.get(cinema["shows_api_url"], headers=headers, timeout=10)
        res_shows.raise_for_status()
        shows_list = res_shows.json()

    except Exception as e:
        print(f"Erreur lors de la récupération pour {cinema_name} : {e}")
        return

    cal = Calendar()
    seances_count = 0

    for show in shows_list:
        if show.get("canceled", False) or show.get("deleted", False):
            continue

        media_id = show.get("mediaid", {}).get("id")
        media = media_catalog.get(media_id, {})

        title = media.get("title") or media.get("tickettitle") or "Séance cinéma"
        director = media.get("director", "")
        synopsis = media.get("storyline", "")
        film_cast = media.get("filmcast", "")
        
        duration_seconds = media.get("duration", 7200)
        duration_delta = datetime.timedelta(seconds=duration_seconds if duration_seconds > 0 else 7200)

        version = "VOST"
        media_options = media.get("mediaMediaoptionsCollection", [])
        for opt in media_options:
            label = opt.get("idoption", {}).get("ticketlabel", "")
            if label == "VF":
                version = "VF"

        # Date et heure de début
        showtime_str = show.get("showtime")
        if not showtime_str:
            continue

        try:
            start_dt = datetime.datetime.fromisoformat(showtime_str)

            event = Event()
            event.name = f"{title} ({version})"

            event.begin = start_dt
            event.duration = duration_delta

            screen_id = show.get("screenid", {}).get("id", "")
            hall_name = f"Salle {screen_id}" if screen_id else "Salle"
            event.location = f"{cinema_name} ({hall_name}), {cinema_address}"

            booking_url = f"{cinema['booking_url']}{media_id}?showId={show.get('id')}"

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

    output_path = os.path.join("dist", cinema["filename"])
    with open(output_path, "w", encoding="utf-8") as f:
        f.writelines(cal.serialize_iter())

    print(f"Fichier '{filename}' généré avec {seances_count} séances.")

def generate_ticketingcine_calendar(cinema):
    site_id = cinema["site_id"]
    cinema_name = cinema["name"]
    cinema_address = cinema["address"]
    filename = cinema["filename"]
    emoji = cinema.get("prefix_emoji")

    print(f"\nTraitement TicketingCine : {cinema_name}")

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Origin": "https://www.ticketingcine.com",
        "Referer": "https://www.ticketingcine.com/"
    }
    payload = {
            "jsonrpc": "2.0",
            "method": "get_prog",
            "params": {
                "site_id": site_id
            },
            "id": 1
        }
        
    try:
        response = requests.post(TICKETINGCINE_API_URL, json=payload, headers=headers, timeout=10)
        response.raise_for_status()
        
        films = response.json().get("result", {}).get("schedule", {}).get("events", [])
    except Exception as e:
        print(f"Erreur lors de la récupération pour {cinema_name} : {e}")
        return []
    
    cal = Calendar()
    seances_count = 0

    for film in films:
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

    output_path = os.path.join("dist", cinema["filename"])
    with open(output_path, "w", encoding="utf-8") as f:
        f.writelines(cal.serialize_iter())

    print(f"Fichier '{filename}' généré avec {seances_count} séances.")

def main():
    print("Génération des calendriers par cinéma...")

    for cinema in CINEMAS:
        if cinema["source"] == "ticketingcine":
            generate_ticketingcine_calendar(cinema)
        elif cinema["source"] == "cineoffice":
            generate_cineoffice_calendar(cinema)

    print("\nTous les fichiers agendas mis à jour")

if __name__ == "__main__":
    main()
