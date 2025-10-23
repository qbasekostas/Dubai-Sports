import requests
import json
import gzip
from xml.etree.ElementTree import Element, SubElement, ElementTree, tostring
from xml.dom import minidom
from datetime import datetime, timedelta

# Λίστα με τα κανάλια που θέλουμε να επεξεργαστούμε
# Μπορείτε να προσθέσετε περισσότερα εδώ αν θέλετε
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

OUTPUT_FILE = "epg.xml"
COMPRESSED_OUTPUT_FILE = "epg.xml.gz"

def format_time_for_xmltv(iso_time_str):
    """Μετατρέπει την ώρα από ISO 8601 format σε XMLTV format (π.χ., 20231027180000 +0300)."""
    # Το Awaan API δίνει ώρα σε UTC (Z στο τέλος)
    dt_object = datetime.fromisoformat(iso_time_str.replace('Z', '+00:00'))
    # Το format είναι YYYYMMDDHHMMSS сплюс/μείον timezone
    return dt_object.strftime('%Y%m%d%H%M%S %z')

def generate_xmltv():
    # Δημιουργία του βασικού <tv> element
    tv_root = Element('tv')

    # 1. Προσθήκη των καναλιών στο XML
    for channel_info in CHANNELS_TO_FETCH:
        channel_el = SubElement(tv_root, 'channel', id=channel_info["id"])
        SubElement(channel_el, 'display-name').text = channel_info["name"]

    # 2. Προσθήκη των προγραμμάτων για κάθε κανάλι
    for channel_info in CHANNELS_TO_FETCH:
        print(f"Fetching EPG for {channel_info['name']}...")
        try:
            response = requests.get(channel_info["url"], timeout=15)
            response.raise_for_status()  # Έλεγχος για σφάλματα (π.χ., 404, 500)
            data = response.json()

            # Βρίσκουμε τη λίστα με τα προγράμματα μέσα στο JSON
            # Συνήθως βρίσκεται σε ένα κλειδί όπως 'data' -> 'listings'
            listings = data.get('data', {}).get('listings', [])

            for program in listings:
                prog_el = SubElement(tv_root, 'programme',
                                     start=format_time_for_xmltv(program.get('startTime', '')),
                                     stop=format_time_for_xmltv(program.get('endTime', '')),
                                     channel=channel_info["id"])

                SubElement(prog_el, 'title', lang="en").text = program.get('title', 'No Title')
                SubElement(prog_el, 'desc', lang="en").text = program.get('description', '')

        except requests.exceptions.RequestException as e:
            print(f"Error fetching data for {channel_info['name']}: {e}")
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
