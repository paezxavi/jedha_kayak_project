import csv
import datetime
import urllib.parse
from pathlib import Path

import scrapy
from scrapy import Selector
from scrapy_playwright.page import PageMethod

# spiders/ -> booking_scraper_project/ -> booking_scraper_project/ -> repo root
CITIES_CSV = Path(__file__).resolve().parents[3] / "cities_with_geoposition.csv"


class BookingSpider(scrapy.Spider):
    # Name of your spider
    name = "booking_spider"

    # Replaces start_requests(), removed in Scrapy 2.17
    async def start(self):
        # Calculate dates
        today = datetime.date.today()
        # Search a month ahead: Booking returns far more available properties
        checkin_date = today + datetime.timedelta(days=30)
        checkout_date = checkin_date + datetime.timedelta(days=5)
        
        checkin_str = checkin_date.strftime('%Y-%m-%d')
        checkout_str = checkout_date.strftime('%Y-%m-%d')

        # Anchored on __file__, not the working directory, so the crawl can be
        # launched from anywhere -- the notebook runs it from the project root,
        # the CLI from booking_scraper_project/.
        #
        # No fallback list on purpose: the CSV is written by the geolocation step
        # of the notebook, and without it the hotels could not be tied back to a
        # city anyway. Missing file must stop the crawl, not start a silent one.
        with open(CITIES_CSV, mode='r', encoding='utf-8') as f:
            cities = [row['city'] for row in csv.DictReader(f)]

        print(f"Starting crawl for {len(cities)} cities: {cities}")

        for city in cities:
            params = {"ss": city, "lang": "fr", "checkin": checkin_str, "checkout": checkout_str}
            # Properly encode parameters for URL
            query_string = urllib.parse.urlencode(params)
            url = f"https://www.booking.com/searchresults.en-gb.html?{query_string}"
            
            yield scrapy.Request(
                url, 
                callback=self.parse, 
                cb_kwargs={'city': city}, 
                meta={
                    "playwright": True,
                    "playwright_page_methods": [
                        PageMethod("wait_for_selector", "div[data-testid='property-card']")
                    ]
                }
            )
    

    async def parse(self, response, city):
        # logger.info, not self.log: Spider.log defaults to DEBUG, and the run
        # log is kept at INFO. At DEBUG these few lines would be buried under
        # scrapy-playwright's per-subresource output -- 99% of a 520k-line file
        # on the 2026-08-16 crawl, and the reason a 123 MB log was needed to
        # answer a question these 900 lines answer on their own.
        self.logger.info(f"Parsing results for {city} - Status: {response.status}")

        # Save HTML for debugging if status is weird or empty results
        if response.status != 200:
             self.logger.warning(f"⚠️ Weird status code {response.status} for {city}")

        sel = Selector(text=response.text)

        # Iterate over cards to inspect data individually
        cards = sel.css('div[data-testid="property-card"]')
        self.logger.info(f"Found {len(cards)} cards for {city}")

        for card in cards:
            # Extract basic info
            name = card.css('div[data-testid="title"]::text').get()
            url = card.css('a[data-testid="title-link"]::attr(href)').get()
            score = card.xpath('.//div[@data-testid="review-score"]/div[@aria-hidden="true"]/text()').get()
            
            # Extract Address/Location from card
            # Booking often puts the city/location in a specific span or link
            # We look for the address text data-testid="address"
            address_text = card.css('[data-testid="address"]::text').get()
            
            # Fallback if address is not explicitly found, use distance as heuristic?
            # Better: Check if address contains city name
            if address_text and city.lower() not in address_text.lower():
                self.logger.info(f"Skipping {name} (Location: {address_text}) - Not in {city}")
                continue
                
            if url:
                yield scrapy.Request(url, callback=self.parse_detail, cb_kwargs={'name': name, 'score': score, 'city': city}, meta={"playwright": True})

    
    async def parse_detail(self, response, name, score, city):
        self.logger.info(f"Detail page for {name} - Status: {response.status}")
        sel = Selector(text=response.text)

        # Extract Lat/Lng
        lat_lng = sel.css('a[id="map_trigger_header"]::attr(data-atlas-latlng)').get()
        lat, lng = None, None
        if lat_lng:
             lat = lat_lng.split(',')[0]
             lng = lat_lng.split(',')[1]
        
        # Extract Description
        description = sel.css('p[data-testid="property-description"]::text').getall()
        # Clean description
        description = " ".join([d.strip() for d in description if d.strip()])
        
        dict_hotels = {
            "city": city,
            "name": name,
            "url": response.url,
            "score": score,
            "lat": lat,
            "lng": lng,
            "description": description
        }  
        yield dict_hotels