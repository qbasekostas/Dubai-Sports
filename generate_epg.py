import requests
import json
import gzip
from xml.etree.ElementTree import Element, SubElement, ElementTree, tostring
from xml.dom import minidom
from datetime import datetime

# --- Ρυθμίσεις ---
CHANNELS_TO_FETCH = [
    {
        "id": "DubaiSports1.ae",
        "name": "Dubai Sports 1",
        "url": "https://www.awaan.ae/epg?channel=702096936067"
    },
    {
        "id": "DubaiSports2.ae",
        "name": "Dubai Sports 2",
        "url": "https://www.awaan.ae/epg?channel=702096936079"
    }
]

OUTPUT_FILE = "dubai.epg.xml"
COMPRESSED_OUTPUT_FILE = "dubai.epg.xml.gz"
# --- Τέλος Ρυθμίσεων ---

def format_time_for_xmltv(iso_time_str):
    """Μετατρέπει την ώρα από ISO 8601 format σε XMLTV format (π.χ., 20231027180000 +0000)."""
    if not iso_time_str:
        return ""
    # Το Awaan API δίνει ώρα σε UTC (Z στο τέλος)
    dt_object = datetime.fromisoformat(iso_time_str.replace('Z', '+00:00'))
    # Το format είναι YYYYMMDDHHMMSS сплюс/μείον timezone
    return dt_object.strftime('%Y%m%d%H%M%S %z')

def generate_xmltv():
    # Δημιουργία του βασικού <tv> element
    tv_root = Element('tv')
    tv_root.set('source-info-name', 'Awaan EPG Grabber')
    tv_root.set('generator-info-name', 'GitHubAction')

    # 1. Προσθήκη των καναλιών στο XML
    for channel_info in CHANNELS_TO_FETCH:
        channel_el = SubElement(tv_root, 'channel', id=channel_info["id"])
        SubElement(channel_el, 'display-name', lang="en").text = channel_info["name"]
        # Μπορείς να προσθέσεις και logo αν βρεις τα URLs
        # SubElement(channel_el, 'icon', src="URL_TO_LOGO")

    # 2. Προσθήκη των προγραμμάτων για κάθε κανάλι
    for channel_info in CHANNELS_TO_FETCH:
        print(f"Fetching EPG for {channel_info['name']}...")
        try:
            # Προσθήκη User-Agent για να μοιάζει με κανονικό browser
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
            response = requests.get(channel_info["url"], timeout=15, headers=headers)
            response.raise_for_status()  # Έλεγχος για σφάλματα (π.χ., 404, 500)
            data = response.json()

            # >>>>> Η ΣΗΜΑΝΤΙΚΗ ΔΙΟΡΘΩΣΗ ΕΙΝΑΙ ΕΔΩ <<<<<
            # Τα προγράμματα είναι πλέον απευθείας μέσα στο 'data' και όχι στο 'data['listings']'
            listings = data.get('data', [])

            if not listings:
                print(f"Warning: No program listings found for {channel_info['name']}.")
                continue

            for program in listings:
                start_time = format_time_for_xmltv(program.get('startTime'))
                end_time = format_time_for_xmltv(program.get('endTime'))
                
                # Έλεγχos αν υπάρχουν οι ώρες, αλλιώς παράλειψη του προγράμματος
                if not start_time or not end_time:
                    continue

                prog_el = SubElement(tv_root, 'programme',
                                     start=start_time,
                                     stop=end_time,
                                     channel=channel_info["id"])

                SubElement(prog_el, 'title', lang="en").text = program.get('title', 'No Title')
                
                # Προσθήκη περιγραφής αν υπάρχει
                description = program.get('description')
                if description:
                    SubElement(prog_el, 'desc', lang="en").text = description

        except requests.exceptions.RequestException as e:
            print(f"Error fetching data for {channel_info['name']}: {e}")
            continue
        except json.JSONDecodeError:
            print(f"Error: Could not decode JSON for {channel_info['name']}. The response might not be valid JSON.")
            continue
    
    # Μετατροπή του XML σε string με " όμορφη " μορφοποίηση
    xml_str = tostring(tv_root, 'utf-8')
    pretty_xml_str = minidom.parseString(xml_str).toprettyxml(indent="  ", encoding='utf-8')

    # Αποθήκευση του XML σε αρχείο
    with open(OUTPUT_FILE, "wb") as f:
        f.write(pretty_xml_str)
    print(f"Successfully created {OUTPUT_FILE}")

    # Συμπίεση του XML σε .gz
    with open(OUTPUT_FILE, 'rb') as f_in, gzip.open(COMPRESSED_OUTPUT_FILE, 'wb') as f_out:
        f_out.writelines(f_in)
    print(f"Successfully created compressed file {COMPRESSED_OUTPUT_FILE}")


if __name__ == "__main__":
    generate_xmltv()
