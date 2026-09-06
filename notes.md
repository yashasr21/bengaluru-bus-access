# Notes, dead ends and things that went wrong

Kept because the finished pipeline makes the work look tidier than it was, and
because half of these are the answer to "why did you do it that way".

## What GTFS actually is, in my own words

I had not heard of GTFS before this project. I assumed a timetable would be
one file. It is not. It is a zip of about ten CSVs that point at each other,
and until I worked out which file points at which, none of it made sense.

Here is the order that finally made it click.

`routes.txt` is the list of routes the way a passenger thinks about them.
500D is one row.

`trips.txt` is one row for every time that route actually runs. 500D leaving
at 07:10 is one row, 500D leaving at 07:40 is another. Both carry the same
`route_id`, which is how they point back to the route.

`stops.txt` is every stop with a latitude and longitude. Nothing complicated
there.

`stop_times.txt` is where the timetable really lives, and it is enormous.
One row for every trip at every stop that trip visits. 1.5 million rows in
this feed. It took me a while to see why it has to be that big. A route with
40 stops running 60 times a day produces 2,400 rows on its own, and BMTC has
4,381 routes.

`calendar.txt` says which days a service runs. `shapes.txt` holds the drawn
path of the route so you can put it on a map. I did not need shapes and
ignored the file, which is a good thing because it is 112 MB on its own.

Once I could see it that way, the question I actually wanted to answer got
easy to say out loud. To find out whether you can get from stop A to stop B,
look for a trip that stops at A and then stops at B further along its
sequence, and subtract the two times. Everything in `03_bus_network.py` and
`04_journey_times.py` is that one sentence, written so it runs over a million
and a half rows without taking all night.

One thing caught me out badly. Times in GTFS can read `25:10:00`. I was sure
the file was corrupt. It is not. It means ten past one in the morning on the
service day that started the previous morning, so a bus leaving at half past
midnight is still part of Tuesday's service and not Wednesday's. If you parse
the hour as 0 to 23 it throws, and it throws a long way into the file.

## Which projection, and why

Everything geometric happens in **EPSG:32643**, UTM zone 43 North, which is the
zone Bengaluru falls in. Coordinates in that system are metres, so `500` really
is five hundred metres on the ground and `numpy.hypot` gives a real distance.

Doing the same arithmetic in plain latitude and longitude (EPSG:4326) would be
wrong, because a degree of longitude at 13 degrees north is about 108 km while
a degree of latitude is about 111 km, and neither is a unit you can hand to a
distance function. A 500 m buffer would come out as an ellipse of the wrong
size, and the error would vary across the city.

Latitude and longitude are used in exactly two places: reading the source files
in, and writing the folium map out, because web maps expect degrees. Between
those two points everything is in metres. Part of why I chose the BBMP
delimitation ward file over other ward layers is that it already arrives in
EPSG:32643.

## Data sources I tried and abandoned

**OpenStreetMap via the Overpass API.** This was the original plan for the
hospital layer and it is what most versions of this project use. I could not
reach Overpass from the machine I built the pipeline on, and rather than stall
I went looking for an alternative. The Karnataka health GIS turned out to be
better for this purpose anyway: it names the facility type, which is what the
inclusion rule ends up hanging on. `scripts/fetch_osm_hospitals.py` is still
here and still works; run it and step 2 merges OSM points in automatically.
The published figures do not include them, and the README says so.

**A separate census table joined to a ward shapefile.** This is the standard
route and it is where ward-level projects usually go wrong, because ward
numbering changes between census years and delimitation exercises. The BBMP
2022 delimitation layer carries the population inside the same file as the
boundary. Using it removed the join entirely.

**Bed counts as a weight.** I wanted a 900-bed teaching hospital to count for
more than a 30-bed community centre. The `BedCount` column exists in four of
the KGIS layers and is zero in all 401 rows of them. Check 9 in the quality
gate exists only to make sure nobody later assumes the column works. The
fallback is the facility-type rule in `02_prepare_hospitals.py`.

## Things that broke

**`trip_id` is not a number.** Most of them read like `1042`. About three
thousand read like `21172_PF9`. Reading the column as `int64` fails on row
900,000 of `stop_times.txt`, which is far enough in that it took a while to
find. `stop_id` has the same problem for a different reason: large bus
stations are split into platforms with ids like `20623_PF1`.

**206 bus stops in the wrong district.** The feed contains stops scattered up
to several hundred kilometres from Bengaluru. They are dropped by distance
from the city centre rather than by name, because the names look normal.

**407 trips with impossible times.** Times that run backwards, single hops of
several hours, an eleven-hour crossing of the city. 0.7% of the feed. They are
filtered before the pattern medians are taken; without the filter, one broken
trip drags a whole route's timings with it.

**Ward medians that flattered the worst wards.** The first version dropped
sample points with no journey before taking the median. This quietly rewarded
the wards with the most unreachable corners: throw away the points nobody can
leave and the survivors look fine. Varthur came out at 78 minutes that way and
103 minutes once unreachable points were charged the ceiling instead. The
second number is the honest one. Checks 12 and 13 in the quality gate exist
because of this class of mistake, not because I expected them to fail.

**Wards smaller than the grid.** A 0.32 sq km ward can fall between the 250 m
sample points and end up with no score at all. `build_grid` gives those wards a
representative point so no ward disappears silently.

**Carto basemap tiles now need an API key.** The interactive map looked better
on Carto Positron, but a map that needs a key is a map that breaks for whoever
opens the repository next. Switched to plain OpenStreetMap tiles.

## Choices I would have to defend

**500 metres.** Chosen because it is the standard planning figure for a bus
stop catchment and works out at about a ten minute walk once you allow for the
fact that streets are not straight. It is also the assumption the result is
most sensitive to: at 800 m the affected population nearly halves. Both
numbers are in the sensitivity table rather than only the flattering one.

**Waiting capped at 20 minutes.** Half the average headway is the usual model
for a passenger who turns up without checking. On this network the median
pattern runs twice a day, so half the headway is four hours, which is not a
wait, it is a decision not to travel. The cap keeps the model sane and makes
it generous to BMTC. Anyone arguing the results are too pessimistic has to
argue past this.

**One transfer, not two.** Two transfers would connect a few more places, and
the journeys would be long enough that nobody would make them. Stopping at one
also keeps the algorithm to two linear passes over the feed, which matters
because I reran the whole thing dozens of times.

**Median of sample points, not the ward centroid.** Wards here range from 0.32
to 29.6 sq km. The centroid of Hemmigepura is a field. Query 9 in
`sql/findings.md` shows why: some wards have a two-hour gap between their best
and worst corner.

**Single-specialty hospitals kept in the headline.** Kidwai treats cancer and
Jayadeva treats hearts; you cannot take a broken wrist to either. They are
still hospitals, so they stay in the headline, and the whole analysis is rerun
without them as a sensitivity check. Removing them moves the affected
population from 1.03 million to 1.13 million.

## Still to do

- Walk the model against reality for five or six journeys using a live app,
  and write down how far off it is.
- Rerun with the OSM private hospitals merged in and publish both numbers
  side by side rather than replacing one with the other.
- The eastern wards are the story; a short section on when Varthur, Bellandur
  and Marathahalli were added to BBMP would put the finding in context.
