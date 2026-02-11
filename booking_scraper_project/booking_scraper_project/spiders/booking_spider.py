import os
import logging
import csv
import datetime
import urllib.parse
import scrapy
from scrapy import Selector


class BookingSpider(scrapy.Spider):
    # Name of your spider
    name = "booking_spider"

    def start_requests(self):
        # Calculate dates
        today = datetime.date.today()
        today_str = today.strftime('%Y-%m-%d')
        delta_days = datetime.timedelta(days=4)
        future_date = today + delta_days
        future_date_str = future_date.strftime('%Y-%m-%d')

        cities = []
        
        # Check if 'city' or 'cities' argument was passed via command line (-a city=Paris)
        if hasattr(self, 'city'):
             cities = [self.city]
        elif hasattr(self, 'cities'):
             cities = self.cities.split(',')
        else:
            # Ensure correct path to CSV (assuming it's in the project root)
            try:
                # When running 'scrapy crawl', the CWD is the project root
                with open('cities_with_geoposition.csv', mode='r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        cities.append(row['city'])
            except FileNotFoundError:
                try:
                    # Fallback if running from a different directory
                    with open('../cities_with_geoposition.csv', mode='r', encoding='utf-8') as f:
                         reader = csv.DictReader(f)
                         for row in reader:
                            cities.append(row['city'])
                except FileNotFoundError:
                    print("CSV file not found, using default cities.")
                    cities = ["Mont Saint Michel", "St Malo", "Bayeux", "Le Havre", "Rouen", "Paris", "Amiens", "Lille", "Strasbourg", "Chateau du Haut Koenigsbourg", "Colmar", "Eguisheim", "Besancon", "Dijon", "Annecy", "Grenoble", "Lyon", "Gorges du Verdon", "Bormes les Mimosas", "Cassis", "Marseille", "Aix en Provence", "Avignon", "Uzes", "Nimes", "Aigues Mortes", "Saintes Maries de la mer", "Collioure", "Carcassonne", "Ariege", "Toulouse", "Montauban", "Biarritz", "Bayonne", "La Rochelle"]

        print(f"Starting crawl for {len(cities)} cities: {cities}")

        for city in cities:
            params = {"ss": city, "lang": "fr", "checkin": today_str, "checkout": future_date_str}
            # Properly encode parameters for URL
            query_string = urllib.parse.urlencode(params)
            url = f"https://www.booking.com/searchresults.en-gb.html?{query_string}"
            
            yield scrapy.Request(url, callback=self.parse, cb_kwargs={'city': city})
    

    # Callback function that will be called when starting your spider
    def parse(self, response, city):
        self.log(f"Parsing results for {city} - Status: {response.status}")
        
        # Save HTML for debugging if status is weird or empty results
        if response.status != 200:
             self.log(f"⚠️ Weird status code {response.status} for {city}")

        sel = Selector(text=response.text)

        titres = sel.css('div[data-testid="title"]::text').getall()
        urls = sel.css('a[data-testid="title-link"]::attr(href)').getall()
        scores = sel.xpath('//div[@data-testid="review-score"]/div[@aria-hidden="true"]/text()').getall()
        
        self.log(f"Found {len(titres)} hotels for {city}")

        for t, u, s in zip(titres, urls, scores):
            # Log first hotel to check data
            if t == titres[0]:
                 self.log(f"Sample hotel: {t} - {u[:30]}...")

            dict_hotels = {
                "city": city,
                "name": t,
                "url": u,
                "score": s
            }   
            
            # Use yield request to go to details
            yield scrapy.Request(u, callback=self.parse_detail, cb_kwargs={'name': t, 'score': s, 'city': city})
    
    def parse_detail(self, response, name, score, city):
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
            "description": description[:200] # Truncate for cleaner JSON
        }  
        yield dict_hotels
