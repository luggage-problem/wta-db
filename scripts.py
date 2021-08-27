#!/usr/bin/env python

import json
import requests
from lxml import etree
import time
import sqlite3
from datetime import date
import typer

BASE_URL = 'https://www.wta.org/go-hiking/hikes/' # base + <hike_id> for individual page
REQUEST_DELAY = 10
DB_FILE = 'hikes.db'

app = typer.Typer()

## internal methods

def normalize_distance(value):
    if not value:
        return
    if 'roundtrip' in value or 'of trails' in value:
        return value.split(' ')[0]
    if 'one-way' in value:
        return float(value.split(' ')[0])*2
    raise ValueError('Distance value was not formed correctly.')

def retrieve_hike_urls(): 
    HIKE_LIST_URL = 'https://www.wta.org/go-hiking/@@trailhead-text-search?jsonp_callback=&query=&start=0&num=9999&_=1629843008980'
    response = requests.get(HIKE_LIST_URL)
    data = json.loads(response.text[1:-1])
    del data['start']
    for hike in data['data']:
        del hike['m']
        hike['url'] = BASE_URL + hike['id']
    return data['data']

def retrieve_hike_html(hike_id):
    time.sleep(REQUEST_DELAY)
    response = requests.get(BASE_URL + hike_id)
    return response.text

def extract_details(hike_id):
    hike_html = etree.HTML(retrieve_hike_html(hike_id))
    
    details = {
        'hike_id' : hike_id,
        'last_scraped' : date.today().strftime('%d/%m/%Y'),
        'alerts' : None,
        'last_maintained' : None,
        'name' : None,
        'features' : None,
        'distance' : None,
        'gain' : None,
        'highest_point' : None,
        'stars' : None,
        'num_votes' : None,
        'location' : None,
        'latitude' : None,
        'longitude' : None,
        'wta_author' : None,
        'driving_directions' : None,
        'hike_description' : None
    }
    
    try:
        alerts = []
        for alert in hike_html.xpath('//div[@id="hike-top"]/div[@class="alerts-and-conditions"]/div'):
            if 'red' in alert.attrib['class']:      
                alerts.append({
                    'type' : 'red',
                    'text' : alert.getchildren()[0].text
                })
            else:            
                alerts.append({
                    'type' : 'parking',
                    'text' : alert.getchildren()[1].text
                })
        details['alerts'] = alerts
    except IndexError:
        pass
    
    try:
        details['last_maintained'] = hike_html.xpath('//div[@class="last-maintained"]/div')[0].text
    except IndexError:
        pass
    
    try:
        details['name'] = hike_html.xpath('//div[@id="hike-top"]/h1')[0].text
    except IndexError:
        pass
        
    try:
        features = []
        for feature in hike_html.xpath('//div[@id="hike-features"]/div'):
            try: 
                features.append(feature.attrib['data-title'])
            except KeyError:
                pass
        details['features'] = features
    except IndexError:
        pass
    
    try: 
        details['distance'] = normalize_distance(hike_html.xpath('//div[@id="distance"]/span')[0].text)
    except IndexError:
        pass
        
    try:
        elevation = hike_html.xpath('//div[@class="hike-stat"]/div/span')
        if 'Highest Point' in ''.join(hike_html.xpath('//div[@class="hike-stat"]/div/text()')) and len(elevation) == 1:
            details['highest_point'] = elevation[0].text
        elif 'Gain' in ''.join(hike_html.xpath('//div[@class="hike-stat"]/div/text()')) and len(elevation) == 1:
            details['gain'] = elevation[0].text
        else:
            details['gain'] = elevation[0].text
            details['highest_point'] = elevation[1].text
    except IndexError:
        pass
        
    try:
        details['stars'] = hike_html.xpath('//div[@class="current-rating"]')[0].text
        details['num_votes'] = hike_html.xpath('//div[@class="rating-count"]')[0].text.strip()[1:].split(' ')[0]
    except IndexError:
        pass
        
    try:
        details['location'] = hike_html.xpath('//div[@id="hike-stats"]/div[@class="hike-stat"]/div')[0].text
    except IndexError:
        pass
        
    try: 
        details['latitude'] = hike_html.xpath('//div[@class="latlong"]/span')[0].text
        details['longitude'] = hike_html.xpath('//div[@class="latlong"]/span')[1].text
    except IndexError:
        pass
        
    try:
        details['wta_author'] = hike_html.xpath('//div[@class="img-text-grouping"]/p/a/span')[0].text
    except IndexError:
        pass
    
    try:
        details['driving_directions'] = hike_html.xpath('//div[@id="driving-directions"]/p')[1].text
    except IndexError:
        pass
        
    try:
        details['hike_description'] = '\n'.join(hike_html.xpath('//div[@id="hike-body-text"]/p/text()'))
    except IndexError:
        pass

    URL = BASE_URL + hike_id + '/@@related_tripreport_listing'
    
    def get_all_trs():
        current_page = get_tr_page(URL)
        trs = []
        while current_page:
            current_page = get_tr_page(current_page['next_page_url'])
            if current_page:
                trs += current_page['tr_urls']
        return trs
    
    def get_tr_page(url):
        time.sleep(REQUEST_DELAY)
        
        html = etree.HTML(requests.get(url).text)
        
        try:
            tr_urls = [tr.attrib['href'] for tr in html.xpath('//a[@class="show-with-full full-report-link visualNoPrint hidden-480 wta-action button"]')]
            return {
                'next_page_url' : html.xpath('//li[@class="next"]/a')[0].attrib['href'],
                'tr_urls' : tr_urls,
            }
        except IndexError:
            return None
        
    def get_tr(url):
        time.sleep(REQUEST_DELAY)
        
        html = etree.HTML(requests.get(url).text)
        
        tr = {}
        
        try:
            tr['author'] = html.xpath('string(//span[@itemprop="author"]/a)').strip()
        except IndexError:
            pass
        
        try:
            condition_elements = html.xpath('//div[@class="trip-condition"]')
            tr['conditions'] = [{
                c.getchildren()[0].text.lower().replace(' ', '_') : c.getchildren()[1].text
            } for c in condition_elements]
        except IndexError:
            pass
        
        try:
            tr['likes'] = html.xpath('//span[@class="tally-total"]/text()')[0]
        except IndexError:
            pass
        
        try:
            tr['report'] = '\n'.join(html.xpath('//div[@id="tripreport-body-text"]/p/text()'))
        except IndexError:
            pass
        
        try:
            tr['date_hiked'] = html.xpath('//span[@class="elapsed-time"]/text()')[0]
        except IndexError:
            pass
        
        return tr
    
    # # get trip reports
    # # likely tens of thousands of requests
    # trs = get_all_trs()
    # print('getting ' + str(len(trs)) + ' TRs...')
    # details['trip_reports'] = [get_tr(url) for url in get_all_trs()]

    return details

## user-facing methods

@app.command()
def create_db():
    """
    Creates sqlite database in local directory and adds all tables.
    """
    with open('create_db.sql') as file:
        with sqlite3.connect(DB_FILE) as con:
            cursor = con.cursor()
            cursor.executescript(file.read())
            con.commit()

@app.command()
def save_all_hikes():
    """
    Scrapes all WTA hike pages and updates or inserts into database where necessary. Can take a while (nearly 4k pages, max rate 1 page / second).
    """
    SQL = ''' INSERT INTO HIKE (slug, last_maintained, name, distance, gain, highest_point, stars, num_votes, th_lat, th_long, wta_author, driving_directions, hike_description, last_scraped, location) 
              VALUES (:hike_id, :last_maintained, :name, :distance, :gain, :highest_point, :stars, :num_votes, :latitude, :longitude, :wta_author, :driving_directions, :hike_description, :last_scraped, :location)
              ON CONFLICT(slug) DO UPDATE
              SET slug=:hike_id, last_maintained=:last_maintained, name=:name, distance=:distance, gain=:gain, 
              highest_point=:highest_point, stars=:stars, num_votes=:num_votes, th_lat=:latitude, th_long=:longitude, 
              wta_author=:wta_author, driving_directions=:driving_directions,last_scraped=:last_scraped, hike_description=:hike_description, location=:location
          '''
    hikes = []
    all_hike_urls = retrieve_hike_urls()
    with typer.progressbar(all_hike_urls) as progress:
        for index, hike in enumerate(progress):
            hike = extract_details(hike['id'])
            with sqlite3.connect(DB_FILE) as con:
                cursor = con.cursor()
                cursor.execute(SQL, hike)
                hike_id = cursor.lastrowid
                # clear any old features
                cursor.execute('DELETE FROM feature WHERE hike_id=?', [hike_id])
                cursor.execute('DELETE FROM alert WHERE hike_id=?', [hike_id])
                # add current features
                if hike.get('features'):
                    for feature in hike['features']:
                        cursor.execute('INSERT INTO feature (hike_id, type) VALUES (?, ?)', [hike_id, feature])
                if hike.get('alerts'):
                    for alert in hike['alerts']:
                        cursor.execute('INSERT INTO alert (hike_id, type, text) VALUES (?, ?, ?)', [hike_id, alert['type'], alert['text']])
                con.commit()

@app.command()
def washed_out_roads_geojson():
    """
    Saves any hikes with alerts including the word 'road' as geojson Points in 'washed_out_roads.json'.
    """
    with sqlite3.connect('hikes.db') as con:
        cursor = con.cursor()
        results = cursor.execute('SELECT hike.name, alert.text, hike.th_lat, hike.th_long FROM hike INNER JOIN alert ON alert.hike_id = hike.id WHERE alert.type = "red" AND alert.text LIKE "%road%"').fetchall()
        return {
            'type' : 'FeatureCollection',
            'features' : [{
                'type' : 'Feature',
                'geometry' : {
                    'type' : 'Point',
                    'coordinates' : [result[3], result[2]]
                },
                'properties' : {
                    'title' : result[0],
                    'description' : result[1]
                }
                } for result in results]
        }
    with open('washed_out_roads.json', 'w+') as file:
        file.write(json.dumps(washed_out_roads_geojson()))

if __name__ == '__main__':
    app()