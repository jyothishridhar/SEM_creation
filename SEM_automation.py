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
import signal
import threading
 
 
 
def generate_variants(property_name, max_variants=5):
    # Split the property name into words
    words = property_name.split()
    # Generate permutations of words
    word_permutations = permutations(words)
    # Join permutations to form variant names
    variants = [' '.join(perm) for i, perm in enumerate(word_permutations) if i < max_variants]
 
    return variants
 
# Define function to scrape the first proper paragraph
def scrape_first_proper_paragraph(url):
    try:
        # Fetch the HTML content of the webpage
        response = requests.get(url, timeout=10)
        response.raise_for_status()  # Raise an exception for bad requests
        # Parse the HTML content
        soup = BeautifulSoup(response.text, 'html.parser')
        # Find all <p> tags
        p_tags = soup.find_all('p')
        # Initialize a variable to store the text of the first two paragraphs
        first_two_paragraphs_text = ''
 
        # Find the text of the first two proper paragraphs
        paragraph_count = 0
        for p in p_tags:
            paragraph = p.text.strip()
            if len(paragraph) > 150:  # Check if the paragraph is not empty
                first_two_paragraphs_text += paragraph + ' '  # Add space between paragraphs
                paragraph_count += 1
                if paragraph_count == 2:  # Stop after finding the first two paragraphs
                    break
 
        # Split the text of the first two paragraphs into sentences
        sentences = re.split(r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?)\s', first_two_paragraphs_text)
 
        # Ensure we have at least two sentences
        while len(sentences) < 2:
            sentences.append('')  # Append empty strings if necessary
 
        # Return the first two sentences
        return sentences[0], sentences[1]
 
    except Exception as e:
        print("An error occurred while scraping first proper paragraph:", e)
        return None, None
   
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
        # Fetch the HTML content of the webpage
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for bad requests
 
        # Parse the HTML content
        soup = BeautifulSoup(response.text, 'html.parser')
 
        # Find all anchor (a) tags
        anchor_tags = soup.find_all('a')
 
        # Set to store unique URLs
        unique_urls = set()
 
        # List to store the found site links
        site_links = []
 
        # Define patterns to match variations in link text
        link_text_patterns = [
            "Official\s?Site",
            "Rooms\s?&\s?Suites",
            "WEDDING",
            "Facilities\s?&\s?Activities",
            "Sports\s?&\s?Entertainment",
            "Specials",
            "Activities",
            "Groups\s?&\s?Meetings",
            "Dining",
            "Meetings\s?&\s?Events",
            "Contact\s?Us",
            "ACCOMMODATION",
            "Photos",
            "Events",
            "Pool & sea",
            "Wellness & fitness",
            "Water Park",
            "Salt Water Swimming Pool",
            "Accommodations",
            "Contact Us"
        ]
 
        # Relevant words related to water activities
        relevant_water_words = ["swimming pool", "Water Park", "pool", "sea","Salt Water Swimming Pool","Pool & sea"]
 
        # Compile regex pattern for link text
        link_text_pattern = re.compile('|'.join(link_text_patterns), re.IGNORECASE)
 
        # Loop through all anchor tags and extract links with specific text
        for a in anchor_tags:
            # Get the text of the anchor tag, stripped of leading and trailing whitespace
            link_text = a.get_text(strip=True)
            print("link_text",link_text)
 
            # Check if the link text matches any of the desired site links
            if link_text_pattern.search(link_text):
                # Extract the href attribute to get the link URL
                link_url = a.get('href')
 
                # Complete relative URLs if necessary
                link_url = urljoin(url, link_url)
 
                # Add the URL to the set of unique URLs
                if link_url not in unique_urls:
                    unique_urls.add(link_url)
 
                    # Check if any of the specified words are present in the link text
                    if any(word in link_text.lower() for word in relevant_water_words):
 
                        # Add "Water park" to the Callouts column instead of Link Text
                        site_links.append((link_url, link_text +" (Water park)"))
 
                    else:
                        # Append both link URL and link text
                        site_links.append((link_url, link_text))
 
                    # Break the loop if the maximum number of links is reached
                    if len(site_links) >= max_links:
                        break
 
 
        return site_links
 
    except Exception as e:
        print("An error occurred while scraping the site links:", e)
        return None
 
 
def scrape_similar_hotels(google_url, header_text):
    try:
        print("Fetching similar hotels...")
        options = Options()
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        driver.get(google_url)
        time.sleep(2)
 
        search_box = driver.find_element(By.XPATH, "//textarea[@id='APjFqb' and @name='q']")
        search_box.send_keys(header_text)
        search_box.send_keys(Keys.RETURN)
        time.sleep(10)
 
        search_results = driver.find_elements(By.XPATH, "//div[@class='hrZZ8d']")
 
        negative_keywords = []
        for result in search_results:
            negative_keywords.append(result.text)
 
        # Close the browser
        driver.quit()
 
        print("Negative Keywords:", negative_keywords)
        return negative_keywords
 
    except Exception as e:
        print("An error occurred while scraping similar hotels:", e)
        return None
 
   
# Define a function to handle timeouts
def timeout_handler():
    raise TimeoutException("Fetching amenities took too long")
 
# Define a custom exception for timeout
class TimeoutException(Exception):
    pass
 
def scrape_amenities(url):
    try:
        # Check if the URL is a tel: or mailto: link
        if url.startswith(('tel:', 'mailto:')):
            print("Skipping URL:", url)
            return []
 
        # Fetch the HTML content of the webpage with a timeout
        response = requests.get(url, timeout=60)  # Set the timeout directly here
        response.raise_for_status()  # Raise an exception for non-HTTP or non-HTTPS URLs
        # Parse the HTML content
        soup = BeautifulSoup(response.text, 'html.parser')
        # Extract text from all elements
        all_text = soup.get_text()
        # Find amenities
        found_amenities = []
        for amenity in amenities_to_check:
            if re.search(amenity, all_text, re.IGNORECASE):
                found_amenities.append(amenity)
        print("found_amenities", found_amenities)
        return found_amenities[:8]
 
    except Exception as e:
        print(f"An error occurred while scraping amenities from url {url}: {e}")
        return []
 
 
# Define the list of amenities to check for
amenities_to_check = [
    "Swimming Pool",
    "Beach Access",
    "Spa Services",
    "Gourmet Dining",
    "Free Breakfast",
    "Free Parking",
    "Fitness Center",
    "Room Service",
    "Free WiFi",
    "Business Center",
    "A/C",
    "Laundry Services",
    "Easy Check In",
    "Express Check Out",
    "Phone",
    "Hair Dryer",
    "Wi-Fi Internet Access",
    "Air-conditioning",
    "Public Wi-Fi",
    "Restaurant",
    "Fitness Center",
    "Bicycle Rental",
    "Air Conditioning & Heating",
    "Hairdryer",
    "Balcony",
    "Lift",
    "Iron & Ironing Board"
]
 
 
def fetch_amenities_from_links(site_links):
    amenities_found = []
    for link_url, _ in site_links:
        try:
            amenities = scrape_amenities(link_url)
            if amenities:
                amenities_found.extend(amenities)
        except Exception as e:
            print(f"An error occurred while fetching amenities from link_url {link_url}: {e}")
    return amenities_found[:8]
   
import requests
from requests.exceptions import Timeout
 
def fetch_amenities_from_sub_links(site_links, max_sub_links=4, timeout=10):
    amenities_found = set()
   
    for link_url, _ in site_links:
        try:
            # Fetch amenities from the current link with a specified timeout
            response = requests.get(link_url, timeout=timeout)
            response.raise_for_status()  # Raise an exception for bad requests
           
            # If the response is successful, proceed with scraping amenities
            amenities = scrape_amenities(link_url)
            if amenities:
                amenities_found.update(amenities)
           
            # If there are still subsequent links to process and we haven't reached the maximum number of sub-links
            if max_sub_links > 0:
                # Parse the HTML content
                soup = BeautifulSoup(response.text, 'html.parser')
                # Find all anchor (a) tags
                anchor_tags = soup.find_all('a', href=True)
                # Set to store unique URLs
                unique_urls = set()
                # List to store the found sub links
                sub_links = []
 
                # Loop through anchor tags and extract sub-links
                for a in anchor_tags:
                    sub_link_url = a['href']
                    sub_link_url = urljoin(link_url, sub_link_url)
                    if sub_link_url not in unique_urls:
                        unique_urls.add(sub_link_url)
                        sub_links.append(sub_link_url)
                        if len(sub_links) >= max_sub_links:
                            break
 
                # Fetch amenities from subsequent links
                for sub_link_url in sub_links:
                    # Use the same timeout for sub-links
                    sub_link_amenities = scrape_amenities(sub_link_url)
                    if sub_link_amenities:
                        amenities_found.update(sub_link_amenities)
                        max_sub_links -= 1  # Decrement the count of sub-links processed
 
                # Update the count of remaining sub-links
                max_sub_links -= len(sub_links)
 
                # If there are no more subsequent links to process, break the loop
                if max_sub_links <= 0:
                    break
               
        except Timeout:
            print(f"Timeout occurred while fetching amenities from sub-link: {link_url}")
            continue  # Skip processing this sub-link and move to the next one
       
        except Exception as e:
            print(f"An error occurred while fetching amenities from sub-link {link_url}: {e}")
   
    return list(amenities_found)[:8]
 
# Streamlit app code
st.title("SEM Creation Template")
# Input URL field
url = st.text_input("Enter URL")
# Input for output file path
output_file = st.text_input("Enter Header")
 
if st.button("Scrape Data"):
    if url:
 
        ad_copy1, ad_copy2 = scrape_first_proper_paragraph(url)
        header_text = extract_header_from_path(output_file) if output_file else None
 
        amenities_found = scrape_amenities(url)
        print("amenities_found",amenities_found)
        # Fetch amenities from link URLs
        site_links = scrape_site_links(url)
        amenities_from_links = fetch_amenities_from_links(site_links)
        print("amenities_from_links",amenities_from_links)
        # Fetch amenities from subsequent links
        amenities_from_sub_links = fetch_amenities_from_sub_links(site_links, max_sub_links=17)
        # Combine all fetched amenities
        all_amenities = amenities_found + amenities_from_links + amenities_from_sub_links
        # Ensure we have at most 8 unique amenities
        unique_amenities = list(set(all_amenities))[:8]
 
        # Continue fetching amenities until we have less than 8 but more than 4, or after checking 10 sub-links
        sub_links_processed = 0
        while 4 < len(unique_amenities) < 8 and len(site_links) > 0 and sub_links_processed < 10:
            max_sub_links = 10 - sub_links_processed  # Fetch amenities from remaining sub-links
            additional_amenities_from_sub_links = fetch_amenities_from_sub_links(site_links, max_sub_links)
            unique_amenities.extend(additional_amenities_from_sub_links)
            unique_amenities = list(set(unique_amenities))[:8]  # Limit to a maximum of 8 unique amenities
            sub_links_processed += max_sub_links  # Update the number of sub-links processed
            if sub_links_processed >= 10:
                break  # Break out of the loop after checking 10 sub-links
 
        # Display the fetched amenities
        st.write("Fetched Amenities:", unique_amenities)
        # Generate property name variants
        property_name_variants = generate_variants(header_text) if header_text else []
 
        # Scraping similar hotels
        negative_keywords = scrape_similar_hotels("https://www.google.com", header_text) if header_text else []
 
        # Creating DataFrames for each piece of data
        header_df = pd.DataFrame({'Header Text': [header_text] if header_text else []})
        paragraph_df = pd.DataFrame({'Ad copy1': [ad_copy1], 'Ad copy2': [ad_copy2]})
        site_links_df = pd.DataFrame(site_links, columns=['Link URL', 'Link Text'])
        property_url = pd.DataFrame({'property_url': [url]})
        property_name_variants_df = pd.DataFrame({'Variants of Property Name': property_name_variants})
        negative_keywords_df = pd.DataFrame(negative_keywords, columns=['Negative Keywords'])
        amenities_df = pd.DataFrame({'Amenities': unique_amenities})
        Callouts = ["Book Direct", "Great Location", "Spacious Suites"]
 
        # Concatenating DataFrames horizontally
        df = pd.concat([header_df, paragraph_df, site_links_df, property_url, property_name_variants_df, negative_keywords_df, amenities_df], axis=1)
 
        # Separate "Water Park" from the link text and add it to the Callouts column
        water_park_added = False  # Flag to track if "Water Park" has been added to Callouts column
        for index, row in df.iterrows():
            link_text = str(row['Link Text'])  # Ensure link text is treated as a string
            water_park_match = re.search(r'Water Park', link_text, flags=re.IGNORECASE)
            if water_park_match:
                if not water_park_added:
                    Callouts.append("Water Park")  # Add "Water Park" to Callouts list
                    water_park_added = True  # Set flag to True
                # If "Water Park" is found in the link text, replace it with a placeholder to keep it intact
                updated_link_text = re.sub(r'Water Park', '~~WATERPARK~~', link_text, flags=re.IGNORECASE).strip()
                df.at[index, 'Link Text'] = updated_link_text  # Update the link text column
 
        # Create a new DataFrame for Callouts
        callouts_df = pd.DataFrame({'Callouts': Callouts})
        # Concatenate Callouts DataFrame with existing DataFrame
        df = pd.concat([df, callouts_df], axis=1)
        # Finally, restore "Water Park" from the placeholder in the Link Text column
        df['Link Text'] = df['Link Text'].str.replace('~~WATERPARK~~', 'Water Park', case=False)
        # Check if output file path is provided
        if output_file:
            try:
                # Writing to Excel
                df.to_excel(output_file, index=False)
                st.success(f"Data has been saved to {output_file}")
            except Exception as e:
                st.error(f"Error occurred while saving data: {e}")
        else:
            st.warning("Please enter a valid output file path.")
 
        # Display the DataFrame
        st.dataframe(df)
 
    else:
        st.warning("Please enter a URL.")