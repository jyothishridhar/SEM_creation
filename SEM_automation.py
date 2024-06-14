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
import time
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from io import StringIO
import io
from openpyxl import Workbook
from openpyxl.styles import PatternFill, Font
from openpyxl.utils.dataframe import dataframe_to_rows

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

def generate_variants(property_name, max_variants=5):
    print("Property Name:", property_name)  # Check the value of property_name
    if property_name is None:
        return []

    # Remove non-alphabetic characters (symbols and numbers) from the property name
    clean_property_name = re.sub(r'[^a-zA-Z\s]', '', property_name)

    # Split the cleaned property name into words
    words = clean_property_name.split()

    # Generate permutations of words
    word_permutations = permutations(words)

    # Join permutations to form variant names
    variants = [' '.join(perm) for i, perm in enumerate(word_permutations) if i < max_variants]

    return variants

def scrape_first_proper_paragraph(url, retries=3, wait_time=10):
    try:
        options = webdriver.ChromeOptions()
        options.add_argument('--no-sandbox')
        options.add_argument('--window-size=1420,1080')
        options.add_argument('--headless')
        options.add_argument('--disable-gpu')
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

        for attempt in range(retries):
            try:
                driver.get(url)
                time.sleep(4)

                # Use explicit wait to ensure the page has fully rendered
                WebDriverWait(driver, wait_time).until(
                    EC.presence_of_element_located((By.TAG_NAME, 'p'))
                )

                # Get the page source
                page_source = driver.page_source

                # Parse the HTML with BeautifulSoup
                soup = BeautifulSoup(page_source, 'html.parser')
                print("Soup object fetched successfully.")  # Log to check if fetching is successful

                # Find all <p> tags
                p_tags = soup.find_all('p')
                print(f"Found <p> tags: {len(p_tags)}")

                # Initialize a variable to store the text of the first two paragraphs
                first_two_paragraphs_text = ''
                paragraph_count = 0

                # Find the text of the first two proper paragraphs
                for p in p_tags:
                    paragraph = p.text.strip()
                    print(f"Paragraph {paragraph_count + 1}: {paragraph[:100]}...")  # Print the first 100 characters
                    if len(paragraph) > 100:  # Check if the paragraph is not empty
                        first_two_paragraphs_text += paragraph + ' '  # Add space between paragraphs
                        paragraph_count += 1
                        if paragraph_count == 3:  # Stop after finding the first two paragraphs
                            break

                if paragraph_count < 2:
                    raise ValueError("Less than two proper paragraphs found.")

                # Split the text of the first two paragraphs into sentences
                sentences = re.split(r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?)\s', first_two_paragraphs_text)

                # Ensure we have at least four sentences
                while len(sentences) < 4:
                    sentences.append('')  # Append empty strings if necessary

                # Return the first two sentences and next two sentences
                return sentences[0] + ' ' + sentences[1], sentences[2] + ' ' + sentences[3]

            except Exception as e:
                print(f"Attempt {attempt + 1} failed with error: {e}")
                time.sleep(5)  # Wait before retrying

        print("All attempts failed. Unable to scrape the paragraphs.")
        return None, None

    except Exception as e:
        # print("An error occurred while extracting header from file path:", e)
        return None

def extract_header_from_path(output_file):
    try:
        # Extract filename from the path
        filename = os.path.basename(output_file)
        # Remove extension from filename
        filename_without_extension = os.path.splitext(filename)[0]
        # Replace underscores with spaces
        header_text = filename_without_extension.replace('_', ' ')

        return header_text.strip()

    except Exception as e:
        print("An error occurred while extracting header from file path:", e)
        return None

def scrape_site_links(url, max_links=8):
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()

        # Parse the HTML content
        soup = BeautifulSoup(response.text, 'html.parser')

        # Find the main content and footer sections
        main_content = soup.body
        footer_content = soup.find('footer')

        # Combine all anchor tags from main content and footer
        anchor_tags = main_content.find_all('a') + (footer_content.find_all('a') if footer_content else [])

        # Set to store unique URLs
        unique_urls = set()

        # List to store the found site links
        site_links = []

        # Define patterns to match variations in link text
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

        # Relevant words related to specific categories
        relevant_meetings_words = ["Meetings & Events", "Groups & Meetings", "Meetings", "Events", "Wedding"]
        relevant_Entertainment_words = ["Sports & Entertainment", "Live music", "Stand-up comedy", "Magic shows", "Art exhibitions", "Sports", "Entertainment"]
        relevant_Facilities_Activities_words = ["Facilities & Activities", "Activities", "Pool & sea", "Salt Water Swimming Pool", "Our Services","swimming pool", "pool", "sea", "Water Park",  "Poolside", "Pool area", "Pool deck", "Pool bar", "Tours & Activities"]
        relevant_Spa_Wellness_words = ["Spa & Wellness", "Spa", "Wellness & fitness","Discover"]
        relevant_Photo_Gallery_words = ["PhotoGallery", "Photo","Gallery"]
        relevant_Dining_words = ["All Dining & Bar Facilities","Restaurant","Food & Beverage Amenities", "Dining", "Gastronomy","Eatery", "Pub", "Diner", "Trattoria", "Brasserie", "Café", "Bistro","In Room dining","Private Dining"]
        relevant_Location_words = ["Location", "Locations", "Destination & Location", "Address", "Venue", "Spot", "Place", "Site", "Locale", "Area", "Premises", "Establishment"]
        relevant_Rooms_words = ["Rooms", "Room", "Rooms & Suites", "Rooms and Suites", "Guest Rooms", "Suites", "Deluxe Rooms", "Executive Suites", "Presidential Suite", "Penthouse", "Family Suites", "Connecting Rooms", "Private Suites"]
        relevant_special_offer_words=["special_offer","offers","offer","Specials"]
        relevant_Accommodation_words=["Accommodation","Facilities"]

        # Find and store relevant site links
        for link in anchor_tags:
            href = link.get('href')
            if href and href.startswith('http'):
                full_url = href
            elif href and not href.startswith('mailto:'):
                full_url = urljoin(url, href)
            else:
                continue

            link_text = link.get_text().strip()

            for pattern in link_text_patterns:
                if re.search(pattern, link_text, re.IGNORECASE):
                    if full_url not in unique_urls:
                        unique_urls.add(full_url)
                        site_links.append({
                            'url': full_url,
                            'link_text': link_text,
                            'category': categorize_link(link_text, relevant_meetings_words, relevant_Entertainment_words,
                                                       relevant_Facilities_Activities_words, relevant_Spa_Wellness_words,
                                                       relevant_Photo_Gallery_words, relevant_Dining_words,
                                                       relevant_Location_words, relevant_Rooms_words,
                                                       relevant_special_offer_words, relevant_Accommodation_words)
                        })
                    break

            if len(site_links) >= max_links:
                break

        return site_links

    except Exception as e:
        print(f"An error occurred while scraping site links: {e}")
        return []

def categorize_link(link_text, *categories):
    for category_words in categories:
        for word in category_words:
            if word.lower() in link_text.lower():
                return category_words[0]  # Return the first word in the category list as the category name
    return "Other"

def fetch_amenities_from_links(links, depth):
    amenities = []

    for link in links:
        url = link['url']
        category = link['category']

        # Scrape the first two sentences from the link
        first_two_sentences, next_two_sentences = scrape_first_proper_paragraph(url)

        if first_two_sentences:
            amenities.append({
                'Category': category,
                'First Two Sentences': first_two_sentences,
                'Next Two Sentences': next_two_sentences,
                'URL': url
            })
            
        # If depth is greater than 1, follow links on the current page up to the specified depth
        if depth > 1:
            sub_links = scrape_site_links(url, max_links=5)
            for sub_link in sub_links:
                first_two_sentences, next_two_sentences = scrape_first_proper_paragraph(sub_link['url'])
                if first_two_sentences:
                    amenities.append({
                        'Category': sub_link['category'],
                        'First Two Sentences': first_two_sentences,
                        'Next Two Sentences': next_two_sentences,
                        'URL': sub_link['url']
                    })

    return amenities

def create_download_link(df, filename, button_text, header_text):
    try:
        # Create a new workbook
        workbook = Workbook()
        sheet = workbook.active

        # Add header to the worksheet
        header_font = Font(bold=True, color='000000')
        fill = PatternFill(start_color="FFFF00", end_color="FFFF00", fill_type="solid")

        # Merge cells and apply formatting for the header
        sheet.merge_cells(start_row=1, start_column=1, end_row=1, end_column=len(df.columns))
        header_cell = sheet.cell(row=1, column=1)
        header_cell.value = header_text
        header_cell.font = Font(bold=True, color='FFFFFF')  # White font color
        header_cell.fill = PatternFill(start_color='4F81BD', end_color='4F81BD', fill_type='solid')  # Blue background

        # Write the data to the worksheet, starting from the second row
        for row in dataframe_to_rows(df, index=False, header=True):
            sheet.append(row)

        # Apply header formatting
        for cell in sheet[2]:
            cell.font = header_font
            cell.fill = fill

        # Save the workbook to a bytes buffer
        buffer = io.BytesIO()
        workbook.save(buffer)
        buffer.seek(0)

        # Create the download link
        b64 = base64.b64encode(buffer.read()).decode()
        href = f'<a href="data:application/octet-stream;base64,{b64}" download="{filename}">{button_text}</a>'

        return href

    except Exception as e:
        print("An error occurred while creating the download link:", e)
        return None

# Streamlit application
def main():
    st.title('Hotel Amenities Scraper')

    # URL input
    url = st.text_input('Enter the hotel website URL:', '')

    # Depth input
    depth = st.number_input('Enter the depth of scraping (e.g., 1 for homepage only, 2 for homepage and subpages):', min_value=1, max_value=5, value=1)

    # Max links input
    max_links = st.number_input('Enter the maximum number of links to scrape from the homepage:', min_value=1, max_value=20, value=8)

    # Output file name input
    output_file = st.text_input('Enter the output file name (without extension):', 'hotel_amenities')

    if st.button('Scrape Amenities'):
        if url:
            with st.spinner('Scraping site links...'):
                site_links = scrape_site_links(url, max_links)
                st.write(f'Found {len(site_links)} site links.')

            with st.spinner('Fetching amenities from links...'):
                amenities = fetch_amenities_from_links(site_links, depth)
                st.write(f'Found amenities from {len(amenities)} links.')

            if amenities:
                df = pd.DataFrame(amenities)
                output_file_with_extension = f"{output_file}.xlsx"

                header_text = extract_header_from_path(output_file_with_extension)

                download_link = create_download_link(df, output_file_with_extension, 'Download Excel file', header_text)

                if download_link:
                    st.markdown(download_link, unsafe_allow_html=True)
                else:
                    st.error('An error occurred while creating the download link.')
        else:
            st.error('Please enter a valid URL.')

if __name__ == '__main__':
    main()
