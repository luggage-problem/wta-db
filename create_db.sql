CREATE TABLE IF NOT EXISTS hike (
	id INTEGER PRIMARY KEY,
	slug TEXT UNIQUE NOT NULL,
	last_maintained TEXT,
	name TEXT NOT NULL,
	distance TEXT,
	gain INTEGER,
	highest_point INTEGER,
	stars TEXT,
	num_votes INTEGER,
	th_lat TEXT,
	th_long TEXT,
	wta_author TEXT,
	driving_directions TEXT,
	hike_description TEXT,
	last_scraped TEXT
);

CREATE TABLE IF NOT EXISTS alert (
	id INTEGER PRIMARY KEY,
	hike_id INTEGER NOT NULL,
	type TEXT NOT NULL,
	text TEXT NOT NULL,
	FOREIGN KEY(hike_id) REFERENCES hike(id)
);

CREATE TABLE IF NOT EXISTS feature (
	id INTEGER PRIMARY KEY,
	hike_id INTEGER NOT NULL,
	type TEXT NOT NULL,
	FOREIGN KEY(hike_id) REFERENCES hike(id)
);