import pandas as pd
import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import re
from itertools import permutations
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
import time
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
import io

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

def generate_variants(property_name, max_variants=5):
    print("Property Name:", property_name)
    if property_name is None:
        return []

    clean_property_name = re.sub(r'[^a-zA-Z\s]', '', property_name)
    words = clean_property_name.split()
    word_permutations = permutations(words)
    variants = [' '.join(perm) for i, perm in enumerate(word_permutations) if i < max_variants]

    return variants

def scrape_first_proper_paragraph(url, retries=3, wait_time=10):
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("start-maximized")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    
    for attempt in range(retries):
        try:
            driver.get(url)
            WebDriverWait(driver, wait_time).until(
                EC.presence_of_element_located((By.TAG_NAME, 'p'))
            )
            page_source = driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')
            p_tags = soup.find_all('p')
            
            first_two_paragraphs_text = ''
            paragraph_count = 0

            for p in p_tags:
                paragraph = p.text.strip()
                if len(paragraph) > 100:
                    first_two_paragraphs_text += paragraph + ' '
                    paragraph_count += 1
                    if paragraph_count == 2:
                        break
            
            if paragraph_count < 2:
                raise ValueError("Less than two proper paragraphs found.")
            
            sentences = re.split(r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?)\s', first_two_paragraphs_text)
            while len(sentences) < 4:
                sentences.append('')
            
            return sentences[0] + ' ' + sentences[1], sentences[2] + ' ' + sentences[3]
        
        except Exception as e:
            print(f"Attempt {attempt + 1} failed with error: {e}")
            time.sleep(5)
            
    driver.quit()
    print("All attempts failed. Unable to scrape the paragraphs.")
    return None, None

def extract_header_from_path(output_file):
    try:
        filename = os.path.basename(output_file)
        filename_without_extension = os.path.splitext(filename)[0]
        header_text = filename_without_extension.replace('_', ' ')
        return header_text.strip()
    except Exception as e:
        print("An error occurred while extracting header from file path:", e)
        return None

def scrape_site_links(url, max_links=10):
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')
        main_content = soup.body
        footer_content = soup.find('footer')

        anchor_tags = main_content.find_all('a') + (footer_content.find_all('a') if footer_content else [])
        unique_urls = set()
        site_links = []

        link_text_patterns = [
            "Official Site", "Rooms & Suites", "Wedding", "Facilities & Activities", "Sports & Entertainment", 
            "Specials", "Live music", "Stand-up comedy", "Magic shows", "Art exhibitions", "Poolside", "Pool area", 
            "Pool deck", "Pool bar", "Tours & Activities", "All Dining & Bar Facilities", "Activities", "Groups & Meetings", 
            "Dining", "Meetings & Events", "Contact Us", "Photos", "Events", "Pool & sea", "Wellness & fitness", 
            "Water Park", "Salt Water Swimming Pool", "Accommodation", "Amenities", "Location", "Rooms", "Gallery", 
            "Pool bar", "Restaurants", "Discover", "Our Services", "Eatery", "Pub", "Diner", "Trattoria", "Brasserie", 
            "Café", "Bistro", "Destination & Location", "Address", "Venue", "Spot", "Place", "Site", "Locale", "Area", 
            "Premises", "Establishment", "Guest Rooms", "Suites", "Deluxe Rooms", "Executive Suites", "Presidential Suite", 
            "Penthouse", "Family Suites", "Connecting Rooms", "Private Suites", "Offers", "Similar Hotels", "Amenities"
        ]

        relevant_meetings_words = ["Meetings & Events", "Groups & Meetings", "Meetings", "Events", "Wedding"]
        relevant_Entertainment_words = ["Sports & Entertainment", "Live music", "Stand-up comedy", "Magic shows", "Art exhibitions", "Sports", "Entertainment"]
        relevant_Facilities_Activities_words = ["Facilities & Activities", "Activities", "Pool & sea", "Salt Water Swimming Pool", "Our Services","swimming pool", "pool", "sea", "Water Park",  "Poolside", "Pool area", "Pool deck", "Pool bar", "Tours & Activities"]
        relevant_Spa_Wellness_words = ["Spa & Wellness", "Spa", "Wellness & fitness","Discover"]
        relevant_Photo_Gallery_words = ["PhotoGallery", "Photo","Gallery"]
        relevant_Dining_words = ["All Dining & Bar Facilities","Restaurant","Food & Beverage Amenities", "Dining", "Gastronomy","Eatery", "Pub", "Diner", "Trattoria", "Brasserie", "Café", "Bistro","In Room dining","Private Dining"]
        relevant_Location_words = ["Location", "Locations", "Destination & Location", "Address", "Venue", "Spot", "Place", "Site", "Locale", "Area", "Premises", "Establishment"]
        relevant_Rooms_words = ["Rooms", "Room", "Rooms & Suites", "Rooms and Suites", "Guest Rooms", "Suites", "Deluxe Rooms", "Executive Suites", "Presidential Suite", "Penthouse", "Family Suites", "Connecting Rooms", "Private Suites"]
        relevant_special_offer_words=["special_offer","offers","offer","Specials"]
        relevant_Accommodation_words=["Explore All Accommodations","Accommodation","stay"]
        relevant_specails_packages_words=["Daily Specials","Weekend Specials","Holiday Specials","Promotional Specials","Family Packages","Couples Packages","Party Packages","Event Packages","Set Menus"]
        relevant_similar_hotels_words = ["Similar Hotels", "Nearby Hotels", "Related Hotels", "Alternative Hotels"]
        relevant_amenities_words = ["Amenities", "Hotel Amenities", "Facilities", "Hotel Facilities"]

        link_text_pattern = re.compile('|'.join(link_text_patterns), re.IGNORECASE)

        for a in anchor_tags:
            link_text = a.get_text(strip=True)
            if link_text_pattern.search(link_text):
                link_url = a.get('href')
                if link_url:
                    link_url = urljoin(url, link_url)
                    if link_url not in unique_urls:
                        unique_urls.add(link_url)

                        if any(word.lower() in link_text.lower() for word in relevant_meetings_words):
                            site_links.append((link_url, "Meetings & Events"))
                        elif any(word.lower() in link_text.lower() for word in relevant_Entertainment_words):
                            site_links.append((link_url, "Entertainment"))
                        elif any(word.lower() in link_text.lower() for word in relevant_Facilities_Activities_words):
                            site_links.append((link_url, "Facilities & Activities"))
                        elif any(word.lower() in link_text.lower() for word in relevant_Spa_Wellness_words):
                            site_links.append((link_url, "Spa & Wellness"))
                        elif any(word.lower() in link_text.lower() for word in relevant_Photo_Gallery_words):
                            site_links.append((link_url, "Photo Gallery"))
                        elif any(word.lower() in link_text.lower() for word in relevant_Dining_words):
                            site_links.append((link_url, "Dining"))
                        elif any(word.lower() in link_text.lower() for word in relevant_Location_words):
                            site_links.append((link_url, "Location"))
                        elif any(word.lower() in link_text.lower() for word in relevant_Rooms_words):
                            site_links.append((link_url, "Rooms & Suites"))
                        elif any(word.lower() in link_text.lower() for word in relevant_special_offer_words):
                            site_links.append((link_url, "Special Offers")) 
                        elif any(word.lower() in link_text.lower() for word in relevant_Accommodation_words):
                            site_links.append((link_url, "Accommodation")) 
                        elif any(word.lower() in link_text.lower() for word in relevant_specails_packages_words):
                            site_links.append((link_url, "Specials & Packages"))
                        elif any(word.lower() in link_text.lower() for word in relevant_similar_hotels_words):
                            site_links.append((link_url, "Similar Hotels"))
                        elif any(word.lower() in link_text.lower() for word in relevant_amenities_words):
                            site_links.append((link_url, "Amenities"))

                        if len(site_links) >= max_links:
                            break

        return site_links

    except requests.RequestException as e:
        print(f"Error during requests to {url}: {str(e)}")
        return []

def save_to_excel(property_name, urls, output_file):
    wb = Workbook()
    ws = wb.active

    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="4F81BD", end_color="4F81BD", fill_type="solid")

    ws.append(["Hotel Name", "Category", "Link", "Summary 1", "Summary 2"])

    for cell in ws[1]:
        cell.font = header_font
        cell.fill = header_fill

    for url, category in urls:
        summary1, summary2 = scrape_first_proper_paragraph(url)
        ws.append([property_name, category, url, summary1, summary2])

    wb.save(output_file)

if __name__ == "__main__":
    property_name = input("Enter the property name: ")
    output_file = input("Enter the output file name (with .xlsx extension): ")

    urls = scrape_site_links('https://www.example.com')  # Replace with the actual URL
    save_to_excel(property_name, urls, output_file)

    print(f"Data saved to {output_file}")
