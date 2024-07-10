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
import sqlite3

# Database setup
def init_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''
              CREATE TABLE IF NOT EXISTS users
              (id INTEGER PRIMARY KEY AUTOINCREMENT,
              username TEXT NOT NULL,
              password TEXT NOT NULL)
              ''')
    conn.commit()
    # Insert a sample user (for demonstration purposes; ideally use a registration process)
    c.execute('''
              INSERT INTO users (username, password)
              VALUES ('adm', 'password')
              ''')
    conn.commit()
    return conn, c

conn, c = init_db()

# Function to verify login credentials
def verify_login(username, password):
    c.execute('SELECT * FROM users WHERE username=? AND password=?', (username, password))
    return c.fetchone()

# Streamlit app login page
def login():
    st.title("Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type='password')
    if st.button("Login"):
        user = verify_login(username, password)
        if user:
            st.success("Logged in successfully!")
            # Store session state or redirect to another page upon successful login
            st.session_state.logged_in = True
            return True
        else:
            st.error("Invalid username or password")
            return False
        
  
        
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


# Define function to scrape the first proper paragraph
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
                    if len(paragraph) > 150:  # Check if the paragraph is not empty
                        first_two_paragraphs_text += paragraph + ' '  # Add space between paragraphs
                        paragraph_count += 1
                        if paragraph_count == 3:  # Stop after finding the first two paragraphs
                            break
            
                if paragraph_count < 1:
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

    # finally:
    #     driver.quit()
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

        response = requests.get(url, headers=headers,timeout=15)
        # Fetch the HTML content of the webpage
        # response = requests.get(url)
        response.raise_for_status()  # Raise an exception for bad requests

        # Parse the HTML content
        soup = BeautifulSoup(response.text, 'html.parser')
        # print("soup---", soup)

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
        relevant_Accommodation_words=["Explore All Accommodations","Accommodation","stay"]
        relevant_specails_packages_words=["Daily Specials","Weekend Specials","Holiday Specials","Promotional Specials","Family Packages","Couples Packages","Party Packages","Event Packages","Set Menus"]

        # Compile regex pattern for link text
        link_text_pattern = re.compile('|'.join(link_text_patterns), re.IGNORECASE)

        # Loop through all anchor tags and extract links with specific text
        for a in anchor_tags:
            # Get the text of the anchor tag, stripped of leading and trailing whitespace
            link_text = a.get_text(strip=True)

            # Check if the link text matches any of the desired site links
            if link_text_pattern.search(link_text):
                # Extract the href attribute to get the link URL
                link_url = a.get('href')
                if link_url:

                    # Complete relative URLs if necessary
                    link_url = urljoin(url, link_url)

                    # Add the URL to the set of unique URLs
                    if link_url not in unique_urls:
                        unique_urls.add(link_url)

                        # Check if the link text matches any meeting/event-related words
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
    
        options = webdriver.ChromeOptions()
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

        negative_keywords = []
        for result in search_results:
            negative_keywords.append(result.text)

        # Close the browser
        driver.quit()

        # print("Negative Keywords:", negative_keywords)
        return negative_keywords

    except Exception as e:
        print("An error occurred while scraping similar hotels:", e)
        return None


# Define the list of amenities to check for
amenities_to_check = [
    "Swimming Pool","Poolside","Pool area","Pool deck","Pool bar","Beach Access","Spa Services","Gourmet Dining","Free Breakfast","Free Parking","Fitness Center",
    "Room Service","Daily Housekeeping","Free WiFi","Public Wi-Fi","Wi-Fi Internet Access","Wi-Fi","Business Center","A/C","Air-conditioning","Air Conditioning & Heating","Air Conditioning",
    "Laundry Services","Easy Check In","Express Check Out","Phone","Hair Dryer","Bicycle Rental","Balcony","Balcony/terrace","Lift","Iron & Ironing Board"

]

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
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()  # Raise an exception for non-HTTP or non-HTTPS URLs

        # Parse the HTML content
        soup = BeautifulSoup(response.text, 'html.parser')
        all_text = soup.get_text()

        # Find amenities
        found_amenities = []
        for amenity in amenities_to_check:
            if re.search(amenity, all_text, re.IGNORECASE):
                found_amenities.append(amenity)
    
        print("found_amenities", found_amenities)
        return list(dict.fromkeys(found_amenities))[:8]
    except Exception as e:
        print(f"An error occurred while scraping amenities from url {url}: {e}")
        return []

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

def fetch_amenities_from_sub_links(site_links, max_sub_links=35, timeout=6, depth=1):
    amenities_found = set()
    def scrape_links(link_url, current_depth):
        nonlocal amenities_found
        try:
            response = requests.get(link_url, headers=headers, timeout=timeout)
            response.raise_for_status()
            amenities = scrape_amenities(link_url)
            if amenities:
                amenities_found.update(amenities)

            if current_depth < depth:
                soup = BeautifulSoup(response.text, 'html.parser')
                anchor_tags = soup.find_all('a', href=True)
                unique_urls = set()
                sub_links = []

                for a in anchor_tags:
                    sub_link_url = a['href']
                    sub_link_url = urljoin(link_url, sub_link_url)
                    if sub_link_url not in unique_urls:
                        unique_urls.add(sub_link_url)
                        sub_links.append(sub_link_url)
                        if len(sub_links) >= max_sub_links:
                            break

                for sub_link_url in sub_links:
                    scrape_links(sub_link_url, current_depth + 1)

        except requests.Timeout:
            print(f"Timeout occurred while fetching amenities from sub-link: {link_url}")
        except Exception as e:
            print(f"An error occurred while fetching amenities from sub-link {link_url}: {e}")

    for link_url, _ in site_links:
        scrape_links(link_url, 1)

    return list(amenities_found)[:8]



# Main function to run the app
def main():
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False

    if not st.session_state.logged_in:
        login_success = login()
        if login_success:

            st.title("SEM Creation Template")
            # # Input URL field
            url = st.text_input("Enter URL")
            # Input for output file path
            output_file = st.text_input("Enter Header")
            
            # Input for depth
            depth = st.number_input("Enter depth", min_value=1, step=1)
            
            if st.button("Scrape Data"):
                if url:
                    # Assuming these functions are defined elsewhere
                    ad_copy1, ad_copy2 = scrape_first_proper_paragraph(url)
                    header_text = extract_header_from_path(output_file) if output_file else None
            
                    amenities_found = scrape_amenities(url)
                    print("amenities_found", amenities_found)
            
                    # Fetch amenities from link URLs
                    site_links = scrape_site_links(url)
                    if site_links:
                        amenities_from_links = fetch_amenities_from_links(site_links)
                    else:
                        print("No site links found.")
                        amenities_from_links = []
                    print("amenities_from_links", amenities_from_links)
            
                    # Fetch amenities from subsequent links with specified depth
                    amenities_from_sub_links = fetch_amenities_from_sub_links(site_links, max_sub_links=10, depth=depth)
                    print("amenities_from_sub_links", amenities_from_sub_links)
            
                    # Combine all fetched amenities
                    all_amenities = amenities_found + amenities_from_links + amenities_from_sub_links
                    unique_amenities = list(set(all_amenities))[:8]
                
                    sub_links_processed = 0
                    while 4 < len(unique_amenities) < 8 and len(site_links) > 0 and sub_links_processed < 35:
                        max_sub_links = 35 - sub_links_processed  # Fetch amenities from remaining sub-links
                        additional_amenities_from_sub_links = fetch_amenities_from_sub_links(site_links, max_sub_links)
                        unique_amenities.extend(additional_amenities_from_sub_links)
                        unique_amenities = list(set(unique_amenities))[:8]  # Limit to a maximum of 8 unique amenities
                        sub_links_processed += max_sub_links  # Update the number of sub-links processed
                        if sub_links_processed >= 35:
                            break  # Break out of the loop after checking 20 sub-links
            
                    sorted_amenities = sorted(unique_amenities, key=lambda x: amenities_to_check.index(x))
                    # st.write("Fetched Amenities:", sorted_amenities)
            
                    sorted_amenities = sorted(unique_amenities, key=lambda x: amenities_to_check.index(x) if x in amenities_to_check else len(amenities_to_check))
                    # st.write("Fetched Amenities:", sorted_amenities)
            
                    property_name_variants = generate_variants(header_text) if header_text else []
            
                    negative_keywords = scrape_similar_hotels("https://www.google.com", header_text) if header_text else []
            
                    header_df = pd.DataFrame({'Header Text': [header_text] if header_text else []})
                    paragraph_df = pd.DataFrame({'Ad copy1': [ad_copy1], 'Ad copy2': [ad_copy2]})
                    site_links_df = pd.DataFrame(site_links, columns=['Link URL', 'Link Text'])
                    property_url = pd.DataFrame({'property_url': [url]})
                    property_name_variants_df = pd.DataFrame({'Variants of Property Name': property_name_variants})
                    negative_keywords_df = pd.DataFrame(negative_keywords, columns=['Negative Keywords'])
                    amenities_df = pd.DataFrame({'Amenities': sorted_amenities})
                    Callouts = ["Book Direct", "Great Location", "Spacious Suites"]
            
                    df = pd.concat([header_df, paragraph_df, site_links_df, property_url, property_name_variants_df, negative_keywords_df, amenities_df], axis=1)
            
                    try:
                        response = requests.get(url, timeout=10)
                        response.raise_for_status()
                        page_content = response.text
                        water_keywords = ["swimming pool", "Water Park", "pool", "sea", "Salt Water Swimming Pool", "Pool & sea", "Poolside", "Pool area", "Pool deck", "Pool bar"]
                        balcony_keywords = ["balcony", "terrace", "veranda", "patio", "deck", "outdoor seating", "private balcony", "balcony view", "balcony access", "sun deck", "rooftop terrace", "lanai", "courtyard", "loggia", "open-air balcony", "French balcony", "wrap-around balcony", "overlooking balcony", "scenic balcony", "balcony suite"]
                        pet_keywords = ["pet-friendly", "pet-friendly policy", "dog-friendly", "cat-friendly", "pet-friendly hotel", "pet-friendly apartment", "pet-friendly rental", "pet-friendly room", "pet-friendly amenities", "pet-friendly patio", "pet-friendly park", "pet-friendly restaurant", "pet-friendly neighborhood", "pet-friendly community", "pet-friendly activities", "pet-friendly events", "pet-friendly travel", "pet-friendly vacations", "pet-friendly establishments"]
            
                        water_found = [keyword for keyword in water_keywords if re.search(keyword, page_content, re.IGNORECASE)]
                        balcony_found = [keyword for keyword in balcony_keywords if re.search(keyword, page_content, re.IGNORECASE)]
                        pet_found = [keyword for keyword in pet_keywords if re.search(keyword, page_content, re.IGNORECASE)]
            
                        print("Water-related keywords found:", water_found)
                        print("Balcony-related keywords found:", balcony_found)
                        print("Pet-friendly keywords found:", pet_found)
            
                        if any(re.search(keyword, page_content, re.IGNORECASE) for keyword in water_keywords):
                            Callouts.append("Water Park")
                        if any(re.search(keyword, page_content, re.IGNORECASE) for keyword in balcony_keywords):
                            Callouts.append("Balcony")
                        if any(re.search(keyword, page_content, re.IGNORECASE) for keyword in pet_keywords):
                            Callouts.append("Pet-friendly")
                    except Exception as e:
                        print(f"An error occurred while checking for water-related keywords: {e}")
            
                    callouts_df = pd.DataFrame({'Callouts': Callouts})
                    df = pd.concat([df, callouts_df], axis=1)
            
                    # Define local file path
                    local_file_path = "C:\\SEM_automation_Excel_Reports\\data.xlsx"
                    directory = os.path.dirname(local_file_path)
            
                    # Debug print to check the directory and path
                    st.write(f"Local file path: {local_file_path}")
                    st.write(f"Directory: {directory}")
            
                    # Ensure the directory exists if directory path is not empty
                    if directory and not os.path.exists(directory):
                        try:
                            os.makedirs(directory)
                            st.write(f"Directory created: {directory}")
                        except Exception as e:
                            st.error(f"Error creating directory: {e}")
            
                    # Save to local path with error handling
                    try:
                        with pd.ExcelWriter(local_file_path, engine='openpyxl') as writer:
                            df.to_excel(writer, index=False, sheet_name='Sheet1')
                            workbook = writer.book
                            worksheet = writer.sheets['Sheet1']
                        
                            # Define header styles
                            header_fill = PatternFill(start_color='C0C0C0', end_color='C0C0C0', fill_type='solid')
                            header_font = Font(color='FFFFFF', bold=True)
                            for cell in worksheet[1]:
                                cell.fill = header_fill
                                cell.font = header_font
                        
                            # Adjust column widths
                            padding = 5
                            specific_columns = {
                                0: 15, 1: 15, 2: 15, 3: 40, 4: 18, 5: 30, 6: 22, 7: 30, 8: 18, 9: 15
                            }
                            for i, column in enumerate(worksheet.columns):
                                if i in specific_columns:
                                    adjusted_width = specific_columns[i]
                                else:
                                    max_length = 0
                                    column = [cell for cell in column]
                                    for cell in column:
                                        try:
                                            if len(str(cell.value)) > max_length:
                                                max_length = len(cell.value)
                                        except:
                                            pass
                                    adjusted_width = (max_length + padding)
                                worksheet.column_dimensions[column[0].column_letter].width = adjusted_width
                        st.success(f"File saved successfully at {local_file_path}")
                    except Exception as e:
                        st.error(f"Error saving file: {e}")
            
                    # Read the saved file back into a BytesIO buffer
                    buffer = io.BytesIO()
                    try:
                        with open(local_file_path, 'rb') as f:
                            buffer.write(f.read())
                        buffer.seek(0)
                    except Exception as e:
                        st.error(f"Error reading file: {e}")
            
                    # Provide the file for download
                    st.download_button(
                        label="Download data as Excel",
                        data=buffer,
                        file_name="data.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
            
                    buffer.seek(0)
                    try:
                        df_from_excel = pd.read_excel(buffer, sheet_name='Sheet1')
                        st.dataframe(df_from_excel)
                    except Exception as e:
                        st.error(f"Error loading dataframe: {e}")
                else:
                    st.warning("Please enter a URL.")
    

if __name__ == "__main__":
    main()  
