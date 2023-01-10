from pprint import pprint
import requests
import json
import selenium
from selenium.common.exceptions import ElementNotInteractableException, ElementClickInterceptedException, StaleElementReferenceException
from selenium import webdriver
from selenium.webdriver.firefox.service import Service as FirefoxService
from webdriver_manager.firefox import GeckoDriverManager
from selenium.webdriver.common.by import By
import argparse
from bs4 import BeautifulSoup

parser = argparse.ArgumentParser()
parser.add_argument('-s', '--slugs', action='store_true', dest='update_slugs')
parser.add_argument('-t', '--transcripts',
                    action='store_true', dest='update_transcripts')
parser.add_argument('-o', '--open-browser',
                    dest='open_browser', action='store_true')
args = parser.parse_args()

LINK_FILE = "./episode_slugs.txt"
TRANSCRIPT_DIR = "./transcripts"

PODCAST_NAME = 'lex-fridman-podcast-10'
PODCAST_LINK = f'https://steno.ai/{PODCAST_NAME}'
GET_PODCAST_PAGE_URL = f'{PODCAST_LINK}/fetch-podcast'
print(GET_PODCAST_PAGE_URL)

s = requests.Session()


def get_podcast_page(page):
    params = {'page': page}
    res = s.get(GET_PODCAST_PAGE_URL, params=params)
    return res.json()


def print_status(*args):
    print("\r\033[2K", end='')
    print(*args, end='', flush=True)


options = webdriver.FirefoxOptions()
options.headless = not args.open_browser

slugs = []

if args.update_slugs:
    # selenium 4
    if args.open_browser:
        with webdriver.Firefox(service=FirefoxService(GeckoDriverManager().install()), options=options) as driver:
            driver.get(PODCAST_LINK)

            def at_last():
                end_str = "Sorry, there are no more episodes for this podcast."
                elems = driver.find_elements(By.TAG_NAME, "h3")
                for elem in elems:
                    if elem.text == end_str:
                        return True
                return False

            def close_popup():
                # try:
                driver.find_element(By.ID, "modal__close").click()
                return True
                # except ElementNotInteractableException:
                #     return False

            loaded_more_count = 0
            while True:
                try:
                    driver.find_element(By.ID, "loadMoreButton").click()
                    loaded_more_count += 1
                    print('Loaded More: ', loaded_more_count, end='', flush=True)
                    print("\r", end='')
                except ElementNotInteractableException:
                    if at_last():
                        break
                    # wait for button to load
                    continue
                except StaleElementReferenceException as e:
                    if at_last():
                        break
                    # else:
                    #     raise e
                except ElementClickInterceptedException:
                    close_popup()
                    continue
            elems = driver.find_elements(By.CLASS_NAME, "article")
            print(len(elems))
            with open(LINK_FILE, 'r+') as f:
                existing_slugs = f.read().split('\n')
                print('existing slugs:', '\n'.join(slugs))
                for elem in elems:
                    slug = elem.find_element(
                        By.CLASS_NAME, "card").get_attribute("data-episode-slug").strip()
                    if slug not in slugs:
                        print('found new slug:', slug)
                        slugs.append(slug)
            slugs.sort()
                # f.write(slug+'\n')
            print("PARSED SLUGS")
    else:
        # res = requests.get()
        first_page = get_podcast_page(1)
        last_page_num = first_page['episodes']['last_page']
        print("Total Pages:", last_page_num)
        for page_num in range(1, last_page_num):
            page = get_podcast_page(page_num)['episodes']
            podcasts = page['data']

            page_slugs = [pod['slug'] for pod in podcasts]
            print_status('Current Page:', page['current_page'], 'Podcast:', page_slugs[-1])
            slugs += page_slugs
            # print(*page_slugs, sep='\n')

    # common
    with open(LINK_FILE, 'w') as f:
        f.write('\n'.join(slugs))
elif args.update_transcripts:
    try:
        with open(LINK_FILE, 'r') as f:
            slugs = f.read().split('\n')
    except FileNotFoundError as e:
        import sys
        print(f"{LINK_FILE} does not exist. Run this script again with the `-s` flag to create it", file=sys.stderr)
        exit(1)


def to_link(slug):
    return PODCAST_LINK + '/' + slug


def to_path(slug):
    return TRANSCRIPT_DIR + '/' + slug + '.json'


def parse_transcript(link):
    soup = BeautifulSoup(requests.get(link).content, features='html.parser')
    passages = soup.find_all(class_="transcript")
    transcript = {}
    for passage in passages:
        try:
            info = {}
            timestamp = passage['id']
            info['timestamp'] = timestamp
            info['text'] = passage.p.mark.text
            transcript[timestamp] = info
        except:
            print(f"Error reading transcript of {link}")
            continue
    # print(soup)
    return transcript


if args.update_transcripts:
    for slug in slugs:
        transcript = parse_transcript(to_link(slug))
        print("Parsed:", slug)
        json.dump(transcript, open(to_path(slug), 'w'), indent=4)

# <h3>Sorry, there are no more episodes for this podcast.</h3>
    # print(driver.page_source)