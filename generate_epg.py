import requests
import json
import gzip
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom
from datetime import datetime, timedelta

# --- Ρυθμίσεις ---
# Τώρα τα URLs δεν έχουν το timestamp. Θα το προσθέτουμε δυναμικά.
CHANNELS_TO_FETCH = [
    {
        "id": "DubaiSports1.ae",
        "name": "Dubai Sports 1",
        "base_url": "https://d1vr1mlm6fadud.cloudfront.net/content/channels/702096936067?region=GR&maxParentalRatings=18&language=en&platform=web"
    },
    {
        "id": "DubaiSports2.ae",
        "name": "Dubai Sports 2",
        "base_url": "https://d1vr1mlm6fadud.cloudfront.net/content/channels/702096936079?region=GR&maxParentalRatings=18&language=en&platform=web"
    }
]

OUTPUT_FILE = "dubai.epg.xml"
COMPRESSED_OUTPUT_FILE = "dubai.epg.xml.gz"
# --- Τέλος Ρυθμίσεων ---

def format_time_for_xmltv(timestamp_ms):
    if not timestamp_ms:
        return ""
    dt_object = datetime.utcfromtimestamp(timestamp_ms / 1000)
    return dt_object.strftime('%Y%m%d%H%M%S +0000')

def generate_xmltv():
    tv_root = Element('tv')
    tv_root.set('source-info-name', 'Awaan EPG Grabber')
    tv_root.set('generator-info-name', 'GitHubAction')

    for channel_info in CHANNELS_TO_FETCH:
        channel_el = SubElement(tv_root, 'channel', id=channel_info["id"])
        SubElement(channel_el, 'display-name', lang="en").text = channel_info["name"]

    # >>>>> ΝΕΑ ΠΡΟΣΘΗΚΗ: Υπολογισμός δυναμικού χρονικού εύρους <<<<<
    now = datetime.now()
    end_date = now + timedelta(days=3) # Παίρνουμε πρόγραμμα για τις επόμενες 3 ημέρες
    
    # Μετατροπή σε millisecond timestamp
    start_ts = int(now.timestamp() * 1000)
    end_ts = int(end_date.timestamp() * 1000)

    print(f"Fetching EPG data from {now.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")

    for channel_info in CHANNELS_TO_FETCH:
        # >>>>> ΝΕΑ ΠΡΟΣΘΗΚΗ: Δημιουργία του πλήρους URL με τα νέα timestamps <<<<<
        full_url = f"{channel_info['base_url']}&byListingTime={start_ts}~{end_ts}"
        
        print(f"Fetching EPG for {channel_info['name']} from {full_url}")
        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(full_url, timeout=15, headers=headers)
            response.raise_for_status()
            
            initial_data = response.json()
            json_string = initial_data.get('data')
            listings = json.loads(json_string)

            if not isinstance(listings, list):
                 print(f"Error: Parsed data for {channel_info['name']} is not a list.")
                 continue

            for program in listings:
                start_time = format_time_for_xmltv(program.get('listingStartTime'))
                end_time = format_time_for_xmltv(program.get('listingEndTime'))
                title = program.get('title')

                if not all([start_time, end_time, title]):
                    continue

                prog_el = SubElement(tv_root, 'programme', start=start_time, stop=end_time, channel=channel_info["id"])
                SubElement(prog_el, 'title', lang="en").text = title
                
                description = program.get('shortDescription') or program.get('longDescription')
                if description:
                    SubElement(prog_el, 'desc', lang="en").text = description

        except requests.exceptions.RequestException as e:
            print(f"Error fetching data for {channel_info['name']}: {e}")
        except (json.JSONDecodeError, TypeError) as e:
            print(f"Error parsing JSON for {channel_info['name']}: {e}")
    
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
