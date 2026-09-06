# What the queries say

Ten queries in this folder, run against `data/processed/bus_access.db`. Build
it with `python scripts/07_build_database.py`, then:

```bash
sqlite3 data/processed/bus_access.db < sql/01_city_summary.sql
```

Results below are from the run of 6 September 2026, on the BMTC feed dated
12 July 2026.

---

## 1. The city as a whole

| wards | people | mean ward minutes | under 30 min | over 45 min | over 60 min |
|---|---|---|---|---|---|
| 198 | 8,443,675 | 22.6 | 5,790,535 | 1,033,678 | 291,185 |

Two thirds of Bengaluru is within half an hour of a hospital by bus. That is
the good news and it is real. The rest of this file is about the other third.

## 2. The bands

| band | wards | people | share of city |
|---|---|---|---|
| Under 30 min | 149 | 5,790,535 | 68.6% |
| 30 to 45 min | 31 | 1,619,462 | 19.2% |
| 45 to 60 min | 13 | 742,493 | 8.8% |
| Over 60 min | 5 | 291,185 | 3.4% |

Note how uneven the ward counts and the population counts are. The five worst
wards hold 3.4% of the city between them, which sounds small until you write
it as 291,185 people.

## 3. The worst served wards

| ward | typical | best corner | worst corner | people | km to hospital |
|---|---|---|---|---|---|
| 149-Varthuru | 102.7 | 28.4 | 130.1 | 54,625 | 5.1 |
| 150-Bellanduru | 77.2 | 25.3 | 130.1 | 80,180 | 5.5 |
| 86-Marathahalli | 71.1 | 33.6 | 135.3 | 39,768 | 3.2 |
| 191-Singasandra | 70.4 | 32.0 | 80.8 | 71,004 | 6.8 |
| 196-Anjanapura | 66.3 | 49.1 | 96.5 | 45,608 | 5.6 |

Every one of them is on the outer ring, and four of the five are on the east
or south east: the corridor that grew fastest after 2005.

Varthur is the sharpest case. Only 54% of the sample points in that ward have
any bus journey to a hospital at all within three hours. Without a change of
bus, none of them do.

## 4. Close to a hospital, slow to reach one

`bus_vs_crow` compares the modelled bus journey with the time it would take to
walk the straight-line distance. Above 1 means the bus loses to the crow.

| ward | typical | km away | bus vs crow |
|---|---|---|---|
| 86-Marathahalli | 71.1 | 3.2 | 1.76 |
| 13-Mallasandra | 43.6 | 2.2 | 1.59 |
| 197-Vasanthpura | 41.6 | 2.2 | 1.49 |
| 87-HAL Airport | 40.3 | 2.2 | 1.48 |
| 84-Hagadur | 48.6 | 2.6 | 1.47 |

These are the interesting ones for anyone deciding where to put a bus rather
than where to put a hospital. Marathahalli is 3.2 km from a hospital and takes
over an hour to reach one. The hospital is not the problem there.

## 5. Far away and still all right

| ward | typical | km away | bus vs crow |
|---|---|---|---|
| 131-Nayandahalli | 35.3 | 4.3 | 0.66 |
| 71-Hegganahalli | 40.1 | 5.0 | 0.64 |
| 129-Jnana Bharathi | 43.0 | 4.6 | 0.75 |

None of these are quick. But at four to five kilometres out they still beat
several wards half the distance from a hospital, because one direct route runs
the whole way. A single good route is worth more than two kilometres.

## 6. How much depends on changing buses

| situation | stops | share | mean minutes |
|---|---|---|---|
| reached with one bus | 6,358 | 65.7% | 52.8 |
| needs a change | 2,926 | 30.2% | 91.5 |
| no bus journey at all | 397 | 4.1% | — |

Nearly a third of the network only reaches a hospital by changing buses, and
those journeys average an hour and a half. The transfer penalty in the model
is a flat 8 minutes; in practice a missed connection on a route that runs
twice a day is not an 8 minute problem.

## 7. Which hospitals the network leans on

Assigning each stop to its nearest hospital, the top sites by stop count are
teaching hospitals on the periphery: Rajarajeshwari (1,073 stops, mean 13.4 km
away), Sapthagiri (793) and Vydehi (703). Those large mean distances are the
finding. A hospital that is the nearest option for a thousand stops averaging
thirteen kilometres away is not really serving them.

## 8. How often the buses run

| frequency | patterns | daily trips |
|---|---|---|
| every 15 min or better | 199 | 18,094 |
| 15 to 30 min | 273 | 12,399 |
| 30 to 60 min | 347 | 7,670 |
| 1 to 4 hours | 1,627 | 10,931 |
| less than four times a day | 4,736 | 7,348 |

This surprised me more than anything else in the project. Two thirds of the
route patterns in the timetable run fewer than four times a day. Under 7% run
every half hour or better, and those few carry more trips than everything
below them combined. The headline figures cap waiting at 20 minutes, which is
generous to BMTC on most of this network.

## 9. Wards divided against themselves

| ward | best corner | typical | worst corner | spread |
|---|---|---|---|---|
| 114-Agaram | 1.9 | 34.3 | 121.2 | 119.3 |
| 150-Bellanduru | 25.3 | 77.2 | 130.1 | 104.8 |
| 86-Marathahalli | 33.6 | 71.1 | 135.3 | 101.7 |

A ward average can hide a two-hour gap between one end of a ward and the
other. Agaram has a corner two minutes from a hospital and a corner two hours
from one. This is why the ward figure is a median of sample points rather than
a single reading at the centroid.

## 10. Does the finding survive its assumptions

| assumption | people over 45 min |
|---|---|
| headline: 500 m walk, all routes, all hospitals | 1,033,678 |
| walk up to 800 m to a stop | 564,050 |
| only routes running every 30 min or better | 1,585,268 |
| excluding single-specialty hospitals | 1,132,769 |
| no changing buses allowed | 1,033,678 |

The catchment radius is the assumption that matters most: stretching the walk
from 500 m to 800 m nearly halves the affected population. That is worth being
honest about, and it is the first question I would expect from anyone reading
this.

The direction of the other three is reassuring. Insisting on a bus that turns
up at least twice an hour makes things markedly worse, not better, and so does
dropping the cancer, cardiac and chest hospitals from the list. Nothing here
makes the finding disappear.
