import requests
import json
import gzip
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom
from datetime import datetime, timedelta

# --- Ρυθμίσεις ---
CHANNELS_TO_FETCH = [
    {
        "id": "DubaiSports1.ae",
        "name": "Dubai Sports 1",
        "channel_id": "702096936067"
    },
    {
        "id": "DubaiSports2.ae",
        "name": "Dubai Sports 2",
        "channel_id": "702096936079"
    }
]

BASE_URL = "https://d1vr1mlm6fadud.cloudfront.net/content/channels/{channel_id}?region=GR&language=en&platform=web"
OUTPUT_FILE = "dubai.epg.xml"
COMPRESSED_OUTPUT_FILE = "dubai.epg.xml.gz"
# --- Τέλος Ρυθμίσεων ---

def format_time_for_xmltv(timestamp_ms):
    """Μετατρέπει την ώρα από milliseconds timestamp σε XMLTV format (UTC)."""
    if not timestamp_ms:
        return ""
    dt_object = datetime.utcfromtimestamp(timestamp_ms / 1000)
    return dt_object.strftime('%Y%m%d%H%M%S +0000')

def generate_xmltv():
    tv_root = Element('tv')

    # 1. Προσθήκη των καναλιών στο XML
    for channel_info in CHANNELS_TO_FETCH:
        channel_el = SubElement(tv_root, 'channel', id=channel_info["id"])
        SubElement(channel_el, 'display-name', lang="en").text = channel_info["name"]

    # 2. Υπολογισμός δυναμικού χρονικού εύρους (π.χ., για τις επόμενες 4 ημέρες)
    now = datetime.now()
    end_date = now + timedelta(days=4)
    start_ts = int(now.timestamp() * 1000)
    end_ts = int(end_date.timestamp() * 1000)
    
    print(f"Fetching EPG data for the range: {now.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")

    # 3. Προσθήκη των προγραμμάτων για κάθε κανάλι
    for channel_info in CHANNELS_TO_FETCH:
        full_url = BASE_URL.format(channel_id=channel_info['channel_id']) + f"&byListingTime={start_ts}~{end_ts}"
        
        print(f"Requesting data for {channel_info['name']} from {full_url}")
        
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
            response = requests.get(full_url, timeout=20, headers=headers)
            response.raise_for_status()
            data = response.json()

            # >>>>> Η ΣΩΣΤΗ ΔΙΑΔΡΟΜΗ ΕΙΝΑΙ ΑΥΤΗ <<<<<
            # Το JSON έχει ένα κλειδί "entries", που είναι μια λίστα.
            # Παίρνουμε το πρώτο αντικείμενο [0] από αυτή τη λίστα.
            # Μέσα εκεί, υπάρχει το κλειδί "listings" που περιέχει τα προγράμματα.
            listings = data.get('entries', [{}])[0].get('listings', [])

            if not listings:
                print(f"Warning: No listings found for {channel_info['name']}.")
                continue

            for item in listings:
                program_details = item.get('program', {})
                if not program_details:
                    continue

                start_time = format_time_for_xmltv(item.get('startTime'))
                end_time = format_time_for_xmltv(item.get('endTime'))
                title = program_details.get('title')
                description = program_details.get('description')

                if not all([start_time, end_time, title]):
                    continue

                prog_el = SubElement(tv_root, 'programme', start=start_time, stop=end_time, channel=channel_info["id"])
                SubElement(prog_el, 'title', lang="en").text = title
                
                if description:
                    SubElement(prog_el, 'desc', lang="en").text = description

        except requests.exceptions.RequestException as e:
            print(f"Error fetching data for {channel_info['name']}: {e}")
        except (json.JSONDecodeError, IndexError) as e:
            print(f"Error parsing JSON or unexpected structure for {channel_info['name']}: {e}")

    # 4. Αποθήκευση και συμπίεση
    xml_str = tostring(tv_root, 'utf-8')
    pretty_xml_str = minidom.parseString(xml_str).toprettyxml(indent="  ", encoding='utf-8')

    with open(OUTPUT_FILE, "wb") as f:
        f.write(pretty_xml_str)
    print(f"Successfully created {OUTPUT_FILE}")

    with open(OUTPUT_FILE, 'rb') as f_in, gzip.open(COMPRESSED_OUTPUT_FILE, 'wb') as f_out:
        f_out.writelines(f_in)
    print(f"Successfully created compressed file {COMPRESSED_OUTPUT_FILE}")

if __name__ == "__main__":
    generate_xmltv()
