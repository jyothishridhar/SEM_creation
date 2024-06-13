import streamlit as st
import pandas as pd
import os
import base64
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
from requests.exceptions import Timeout
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from io import StringIO
import io
from openpyxl.utils.dataframe import dataframe_to_rows

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

def generate_variants(property_name, max_variants=5):
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

    try:
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
                        if paragraph_count == 3:
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

        return None, None

    finally:
        driver.quit()

def extract_header_from_path(output_file):
    try:
        filename = os.path.basename(output_file)
        filename_without_extension = os.path.splitext(filename)[0]
        header_text = filename_without_extension.replace('_', ' ')

        return header_text.strip()

    except Exception as e:
        print("An error occurred while extracting header from file path:", e)
        return None

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
                            site_links.append((link_url, "Specials"))
                        elif any(word.lower() in link_text.lower() for word in relevant_Accommodation_words):
                            site_links.append((link_url, "Accommodations"))
                        elif any(word.lower() in link_text.lower() for word in relevant_specails_packages_words):
                            site_links.append((link_url, "Packages"))

                        if len(site_links) >= max_links:
                            break

        return site_links

    except Timeout:
        print(f"Timeout occurred while trying to access {url}")
        return []

    except requests.exceptions.RequestException as e:
        print(f"An error occurred while trying to access {url}: {e}")
        return []

def scrape_google_map_url(query, retries=3, wait_time=10):
    query = query + " site:google.com/maps"
    base_url = "https://www.google.com/search?q="
    search_url = base_url + query.replace(' ', '+')

    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("start-maximized")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    try:
        for attempt in range(retries):
            try:
                driver.get(search_url)
                WebDriverWait(driver, wait_time).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'div.g'))
                )

                soup = BeautifulSoup(driver.page_source, 'html.parser')
                search_results = soup.find_all('div', class_='g')

                for result in search_results:
                    link_tag = result.find('a')
                    if link_tag:
                        link = link_tag.get('href')
                        if 'google.com/maps' in link:
                            return link

            except Exception as e:
                print(f"Attempt {attempt + 1} failed with error: {e}")
                time.sleep(5)

        return None

    finally:
        driver.quit()

def extract_website_from_url(url):
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')
        website = soup.find('cite').text

        return website

    except Timeout:
        print(f"Timeout occurred while trying to access {url}")
        return None

    except requests.exceptions.RequestException as e:
        print(f"An error occurred while trying to access {url}: {e}")
        return None

def save_dataframe_to_excel(df, file_path):
    try:
        df.to_excel(file_path, index=False)
        print(f"DataFrame saved to {file_path}")
    except Exception as e:
        print("An error occurred while saving DataFrame to Excel:", e)

def search_wikipedia(property_name):
    base_url = "https://en.wikipedia.org/wiki/"
    search_url = base_url + property_name.replace(' ', '_')

    try:
        response = requests.get(search_url, headers=headers, timeout=15)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')
        paragraph = soup.find('p').get_text()

        return paragraph

    except Timeout:
        print(f"Timeout occurred while trying to access {search_url}")
        return None

    except requests.exceptions.RequestException as e:
        print(f"An error occurred while trying to access {search_url}: {e}")
        return None

def scrape_google_search(query, retries=3, wait_time=10):
    base_url = "https://www.google.com/search?q="
    search_url = base_url + query.replace(' ', '+')

    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("start-maximized")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    try:
        for attempt in range(retries):
            try:
                driver.get(search_url)
                WebDriverWait(driver, wait_time).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'div.g'))
                )

                soup = BeautifulSoup(driver.page_source, 'html.parser')
                search_results = soup.find_all('div', class_='g')

                urls = []

                for result in search_results:
                    link_tag = result.find('a')
                    if link_tag:
                        link = link_tag.get('href')
                        urls.append(link)

                    if len(urls) >= 5:
                        break

                return urls

            except Exception as e:
                print(f"Attempt {attempt + 1} failed with error: {e}")
                time.sleep(5)

        return []

    finally:
        driver.quit()

def extract_text_from_google_search(url):
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')
        p_tags = soup.find_all('p')

        first_two_paragraphs_text = ''
        paragraph_count = 0

        for p in p_tags:
            paragraph = p.text.strip()
            if len(paragraph) > 100:
                first_two_paragraphs_text += paragraph + ' '
                paragraph_count += 1
                if paragraph_count == 3:
                    break

        if paragraph_count < 2:
            raise ValueError("Less than two proper paragraphs found.")

        sentences = re.split(r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?)\s', first_two_paragraphs_text)

        while len(sentences) < 4:
            sentences.append('')

        return sentences[0] + ' ' + sentences[1], sentences[2] + ' ' + sentences[3]

    except Timeout:
        print(f"Timeout occurred while trying to access {url}")
        return None, None

    except requests.exceptions.RequestException as e:
        print(f"An error occurred while trying to access {url}: {e}")
        return None, None

def main():
    st.title("Property Information Scraper")

    uploaded_file = st.file_uploader("Choose a file", type=["xlsx"])

    if uploaded_file is not None:
        df = pd.read_excel(uploaded_file)

        columns = df.columns.tolist()
        selected_column = st.selectbox("Select the column containing property names:", columns)

        property_names = df[selected_column].dropna().unique()

        progress_bar = st.progress(0)
        progress_text = st.empty()

        results = []

        for idx, property_name in enumerate(property_names):
            progress_text.text(f"Processing {property_name} ({idx + 1} of {len(property_names)})")
            progress_bar.progress((idx + 1) / len(property_names))

            variants = generate_variants(property_name)

            property_data = {
                "Property Name": property_name,
                "Description": None,
                "Links": [],
                "Google Map URL": None,
                "First Two Paragraphs from Google Search": None
            }

            description = None
            for variant in variants:
                description = search_wikipedia(variant)
                if description:
                    break

            property_data["Description"] = description

            links = scrape_site_links(property_name)
            property_data["Links"] = links

            map_url = scrape_google_map_url(property_name)
            property_data["Google Map URL"] = map_url

            google_search_urls = scrape_google_search(property_name)
            first_two_paragraphs = None
            for url in google_search_urls:
                first_two_paragraphs = extract_text_from_google_search(url)
                if first_two_paragraphs[0] and first_two_paragraphs[1]:
                    break

            property_data["First Two Paragraphs from Google Search"] = first_two_paragraphs

            results.append(property_data)

        output_df = pd.DataFrame(results)
        output_file = "scraped_properties.xlsx"
        save_dataframe_to_excel(output_df, output_file)

        st.success("Scraping complete! You can download the results below:")
        st.download_button(
            label="Download Excel file",
            data=output_df.to_excel(index=False),
            file_name=output_file,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

if __name__ == "__main__":
    main()
