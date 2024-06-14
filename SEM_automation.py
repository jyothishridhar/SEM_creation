import streamlit as st
import pandas as pd
import os
import re
import time
import requests
from bs4 import BeautifulSoup
from itertools import permutations
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from io import BytesIO
from openpyxl import Workbook
from openpyxl.styles import PatternFill, Font
from urllib.parse import urljoin

# Headers for HTTP requests
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

# Function to generate property name variants
def generate_variants(property_name, max_variants=5):
    if property_name is None:
        return []
    clean_property_name = re.sub(r'[^a-zA-Z\s]', '', property_name)
    words = clean_property_name.split()
    word_permutations = permutations(words)
    variants = [' '.join(perm) for i, perm in enumerate(word_permutations) if i < max_variants]
    return variants

# Function to scrape the first two proper paragraphs
def scrape_first_proper_paragraph(url, retries=3, wait_time=10):
    options = webdriver.ChromeOptions()
    options.add_argument('--no-sandbox')
    options.add_argument('--window-size=1420,1080')
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
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
            time.sleep(5)
    driver.quit()
    return None, None

# Function to extract header from file path
def extract_header_from_path(output_file):
    try:
        filename = os.path.basename(output_file)
        filename_without_extension = os.path.splitext(filename)[0]
        header_text = filename_without_extension.replace('_', ' ')
        return header_text.strip()
    except Exception as e:
        print(f"An error occurred while extracting header from file path: {e}")
        return None

# Function to scrape site links
def scrape_site_links(url, max_links=8):
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
            "Penthouse", "Family Suites", "Connecting Rooms", "Private Suites", "Offers"
        ]
        relevant_words = {
            "Meetings & Events": ["Meetings & Events", "Groups & Meetings", "Meetings", "Events", "Wedding"],
            "Entertainment": ["Sports & Entertainment", "Live music", "Stand-up comedy", "Magic shows", "Art exhibitions", "Sports", "Entertainment"],
            "Facilities & Activities": ["Facilities & Activities", "Activities", "Pool & sea", "Salt Water Swimming Pool", "Our Services","swimming pool", "pool", "sea", "Water Park",  "Poolside", "Pool area", "Pool deck", "Pool bar", "Tours & Activities"],
            "Spa & Wellness": ["Spa & Wellness", "Spa", "Wellness & fitness","Discover"],
            "Photo Gallery": ["PhotoGallery", "Photo","Gallery"],
            "Dining": ["All Dining & Bar Facilities","Restaurant","Food & Beverage Amenities", "Dining", "Gastronomy","Eatery", "Pub", "Diner", "Trattoria", "Brasserie", "Café", "Bistro","In Room dining","Private Dining"],
            "Location": ["Location", "Locations", "Destination & Location", "Address", "Venue", "Spot", "Place", "Site", "Locale", "Area", "Premises", "Establishment"],
            "Rooms & Suites": ["Rooms", "Room", "Rooms & Suites", "Rooms and Suites", "Guest Rooms", "Suites", "Deluxe Rooms", "Executive Suites", "Presidential Suite", "Penthouse", "Family Suites", "Connecting Rooms", "Private Suites"],
            "Special Offers": ["special_offer","offers","offer","Specials"], 
            "Accommodation": ["Explore All Accommodations","Accommodation","stay"],   
            "Specials & Packages": ["Daily Specials","Weekend Specials","Holiday Specials","Promotional Specials","Family Packages","Couples Packages","Party Packages","Event Packages","Set Menus"]
        }

        link_text_pattern = re.compile('|'.join(link_text_patterns), re.IGNORECASE)
        for a in anchor_tags:
            link_text = a.get_text(strip=True)
            if link_text_pattern.search(link_text):
                link_url = a.get('href')
                if link_url:
                    link_url = urljoin(url, link_url)
                    if link_url not in unique_urls:
                        unique_urls.add(link_url)
                        for category, words in relevant_words.items():
                            if any(word.lower() in link_text.lower() for word in words):
                                site_links.append((link_url, category))
                                break
                        else:
                            site_links.append((link_url, link_text))
                        if len(site_links) >= max_links:
                            break
        return site_links
    except Exception as e:
        print(f"An error occurred while scraping the site links: {e}")
        return []

# Function to scrape similar hotels
def scrape_similar_hotels(google_url, header_text):
    try:
        options = Options()
        options.add_argument('--no-sandbox')
        options.add_argument('--window-size=1420,1080')
        options.add_argument('--headless')
        options.add_argument('--disable-gpu')
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        driver.get(google_url)
        time.sleep(6)
        search_box = driver.find_element(By.XPATH, "//textarea[@id='APjFqb' and @name='q']")
        search_box.send_keys(header_text)
        search_box.send_keys(Keys.RETURN)
        time.sleep(10)
        search_results = driver.find_elements(By.XPATH, "//div[@class='hrZZ8d']")
        negative_keywords = [result.text for result in search_results]
        driver.quit()
        return negative_keywords
    except Exception as e:
        print(f"An error occurred while scraping similar hotels: {e}")
        return []

# List of amenities to check for
amenities_to_check = [
    "Swimming Pool","Poolside","Pool area","Pool deck","Pool bar","Beach Access","Spa Services","Gourmet Dining","Free Breakfast","Free Parking","Fitness Center",
    "Room Service","Daily Housekeeping","Free Wi-Fi","Air Conditioning","Family Friendly","Pet Friendly","Concierge Services","Airport Shuttle","Meeting Rooms",
    "Wedding Services","Business Center","24-Hour Front Desk","Laundry Services","Private Balconies","On-site Restaurant","Free Airport Shuttle",
    "Tours & Excursions","Non-smoking Rooms","Bar/Lounge","Bicycle Rentals","Kids Club","Live Entertainment","Yoga Classes","Golf Course","Tennis Courts","Water Sports","Jacuzzi",
    "Sun Loungers","Pool Towels","Swim-Up Bar","Infinity Pool","Rooftop Pool","Pool Cabanas","Saltwater Pool","Lap Pool","Indoor Pool","Children's Pool","Outdoor Pool","Heated Pool","Poolside Dining","Water Park",
    "Water Sports Center","Poolside Service","Poolside Massage","Poolside Entertainment","Poolside Barbecue","Poolside Activities","Poolside DJ","Private Pool Parties","Poolside Lounges","Poolside Daybeds",
    "Poolside Retreats","Cabanas by the Pool","Exclusive Pool Access","Personal Pool Attendant","VIP Pool Area","Poolside Spa Treatments","Champagne Service by the Pool","Poolside Refreshments",
    "Poolside Events","Poolside Cabanas","Poolside Oasis","Serene Poolside Ambiance","Poolside Luxury","Poolside Relaxation","Poolside Experience","Poolside Escapes",
    "Gourmet Snacks by the Pool","Poolside Lounge Chairs","Luxurious Poolside Environment","Exquisite Poolside Views","Poolside Yoga","Poolside Meditation",
    "Signature Poolside Cocktails","Poolside Fine Dining","Poolside Tranquility","Unwind by the Pool","Lavish Poolside Service","Poolside Wellness","Poolside Bliss",
    "Oceanfront Pool","Poolside Adventure","Poolside Comfort","Poolside Enjoyment","Refreshing Poolside Drinks","Poolside Hideaway","Poolside Delights",
    "Indulgent Poolside Moments","Premier Poolside Venue","Poolside Rejuvenation","Poolside Pampering","Exclusive Poolside Experience","Sophisticated Poolside Atmosphere",
    "Scenic Poolside Location","Poolside Dining Experience","Unmatched Poolside Luxury","Elite Poolside Offerings","Perfect Poolside Retreat","Top-notch Poolside Service",
    "Elegant Poolside Setting","World-Class Poolside Amenities","Distinctive Poolside Appeal","Ultimate Poolside Relaxation","Poolside Perfection","Premium Poolside Services"
]

# Function to scrape property page
def scrape_property_page(url, negative_keywords):
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        page_text = soup.get_text().lower()
        matched_amenities = [amenity for amenity in amenities_to_check if amenity.lower() in page_text]
        page_has_no_amenities = all(keyword.lower() in page_text for keyword in negative_keywords)
        return matched_amenities, page_has_no_amenities
    except Exception as e:
        print(f"An error occurred while scraping the property page: {e}")
        return [], True

# Function to create and format the Excel file
def create_excel_file(header_text, sentences, site_links, output_file):
    wb = Workbook()
    ws = wb.active

    # Apply formatting
    header_fill = PatternFill(start_color="00C0C0C0", end_color="00C0C0C0", fill_type="solid")
    header_font = Font(size=14, bold=True, color="00FFFFFF")

    ws['A1'].fill = header_fill
    ws['A1'].font = header_font
    ws['A1'] = header_text

    ws['A2'].fill = header_fill
    ws['A2'].font = header_font
    ws['A2'] = "First Paragraph"

    ws['A3'] = sentences[0]

    ws['A4'].fill = header_fill
    ws['A4'].font = header_font
    ws['A4'] = "Second Paragraph"

    ws['A5'] = sentences[1]

    ws['A6'].fill = header_fill
    ws['A6'].font = header_font
    ws['A6'] = "Site Links"

    for i, (link, category) in enumerate(site_links, start=7):
        ws[f'A{i}'] = category
        ws[f'B{i}'] = link

    wb.save(output_file)
    return output_file

def main():
    st.title("Hotel Scraper")
    st.write("Please upload an Excel file with a list of hotel names and their websites.")

    uploaded_file = st.file_uploader("Choose an Excel file", type="xlsx")
    if uploaded_file:
        input_df = pd.read_excel(uploaded_file)
        st.write("Uploaded file preview:")
        st.write(input_df.head())

        output_data = []
        output_file = "scraped_data.xlsx"

        for index, row in input_df.iterrows():
            property_name = row.get('property_name')
            property_url = row.get('property_url')

            if pd.notna(property_name) and pd.notna(property_url):
                st.write(f"Scraping data for: {property_name}")

                # Generate property name variants
                property_variants = generate_variants(property_name)
                st.write(f"Generated variants: {property_variants}")

                # Scrape the first two proper paragraphs
                sentences = scrape_first_proper_paragraph(property_url)
                st.write(f"First two proper paragraphs: {sentences}")

                # Extract header from output file path
                header_text = extract_header_from_path(output_file)
                st.write(f"Header text: {header_text}")

                # Scrape site links
                site_links = scrape_site_links(property_url)
                st.write(f"Scraped site links: {site_links}")

                # Scrape similar hotels
                google_url = "https://www.google.com/"
                similar_hotels = scrape_similar_hotels(google_url, header_text)
                st.write(f"Scraped similar hotels: {similar_hotels}")

                # Scrape property page for amenities
                amenities, has_no_amenities = scrape_property_page(property_url, similar_hotels)
                st.write(f"Matched amenities: {amenities}")
                st.write(f"Page has no amenities: {has_no_amenities}")

                # Store the scraped data
                output_data.append({
                    'property_name': property_name,
                    'property_url': property_url,
                    'variants': property_variants,
                    'sentences': sentences,
                    'site_links': site_links,
                    'similar_hotels': similar_hotels,
                    'amenities': amenities,
                    'has_no_amenities': has_no_amenities
                })

        # Create the output Excel file
        create_excel_file(header_text, sentences, site_links, output_file)

        # Allow the user to download the file
        with open(output_file, "rb") as f:
            st.download_button("Download Scraped Data", data=f, file_name="scraped_data.xlsx")

if __name__ == "__main__":
    main()
