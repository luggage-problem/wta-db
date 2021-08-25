# wta-db
(+ scraper)

Creating a db of all 3897 hikes listed by the WTA via scraping their site. 
In an attempt to be at least slightly respectful, maximum rate is 1 request / second.
Code was initially created as a jupyter notebook, and includes bonus code to scrape all trip reports (which I decided would take way too long to run).

Original intent was to find all hikes with washed out roads for potential bikepacking adventures
(current map of trailheads w/ washed out roads available [here](https://caltopo.com/m/0F2EB).

## Example Query
```SQL
SELECT hike.name, alert.text FROM hike 
INNER JOIN alert ON alert.hike_id = hike.id 
WHERE alert.type = "red" AND alert.text LIKE "%road%"
```
Returns: all hikes with 'road' in alert text
