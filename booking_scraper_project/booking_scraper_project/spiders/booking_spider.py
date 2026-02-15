import os
import logging
import csv
import datetime
import urllib.parse
import scrapy
from scrapy import Selector
from scrapy_playwright.page import PageMethod


class BookingSpider(scrapy.Spider):
    # Name of your spider
    name = "booking_spider"

    def start_requests(self):
        # Calculate dates
        today = datetime.date.today()
        # Shift to next month (e.g. +30 days) to find more availability
        checkin_date = today + datetime.timedelta(days=30)
        checkout_date = checkin_date + datetime.timedelta(days=5)
        
        checkin_str = checkin_date.strftime('%Y-%m-%d')
        checkout_str = checkout_date.strftime('%Y-%m-%d')

        cities = []
        
        try:
            # 1. Try current directory (rare if running from spider dir)
            with open('cities_with_geoposition.csv', mode='r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    cities.append(row['city'])
        except FileNotFoundError:
            try:
                # 2. Try one level up (Common: running from booking_scraper_project root)
                with open('../cities_with_geoposition.csv', mode='r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        cities.append(row['city'])
            except FileNotFoundError:
                try: 
                    # 3. Try two levels up (Just in case)
                    with open('../../cities_with_geoposition.csv', mode='r', encoding='utf-8') as f:
                        reader = csv.DictReader(f)
                        for row in reader:
                            cities.append(row['city'])
                except FileNotFoundError:
                    print("⚠️ CSV file not found (tried '.', '..', '../..'). Using default list.")
                    cities = ["Mont Saint Michel", "St Malo", "Bayeux", "Le Havre", "Rouen", "Paris", "Amiens", "Lille", "Strasbourg", "Chateau du Haut Koenigsbourg", "Colmar", "Eguisheim", "Besancon", "Dijon", "Annecy", "Grenoble", "Lyon", "Gorges du Verdon", "Bormes les Mimosas", "Cassis", "Marseille", "Aix en Provence", "Avignon", "Uzes", "Nimes", "Aigues Mortes", "Saintes Maries de la mer", "Collioure", "Carcassonne", "Ariege", "Toulouse", "Montauban", "Biarritz", "Bayonne", "La Rochelle"]

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
        self.log(f"Parsing results for {city} - Status: {response.status}")
        
        # Save HTML for debugging if status is weird or empty results
        if response.status != 200:
             self.log(f"⚠️ Weird status code {response.status} for {city}")

        sel = Selector(text=response.text)

        # Iterate over cards to inspect data individually
        cards = sel.css('div[data-testid="property-card"]')
        self.log(f"Found {len(cards)} cards for {city}")

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
                self.log(f"Skipping {name} (Location: {address_text}) - Not in {city}")
                continue
                
            if url:
                yield scrapy.Request(url, callback=self.parse_detail, cb_kwargs={'name': name, 'score': score, 'city': city}, meta={"playwright": True})

    
    async def parse_detail(self, response, name, score, city):
        self.log(f"Detail page for {name} - Status: {response.status}")
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