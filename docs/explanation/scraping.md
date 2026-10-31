# Scraping and duty times

How a duty list gets from a chamber's website to a visitor: what each scraper
reads, how it gets each pharmacy's duty window, when scrapes run, how a
scrape is written, how a request picks open or duty pharmacies, and how
`/health/data/` shows freshness. Terms are those of [`CONTEXT.md`](../../CONTEXT.md).
Read from the code and from scrapes in the testenv on 28 Oct 2026. Change
this page in the same PR as any change to a scraper, to `run_scraper`, to
`add_scraped_data_to_db` or to the scrape schedule.

```
chamber site ──scraper──▶ run_scraper ──add_scraped_data_to_db──▶ Pharmacy rows
                (worker)                                              │
visitor ──POST /get_pharmacy_points──▶ city status ─┬─ open ──▶ Google Places
                                                    └─ closed ─▶ rows on duty now
```

## Sources

`get_city_data` (`pharmacies/utils/utils.py`) maps a city to its scraper.
Every scraper returns the standard dict per pharmacy: `name`, `address`,
`district`, `phone`, `coordinates` (`lat`, `lng`), `duty_start`, `duty_end`.

### Eskişehir

- **Source:** the Eskişehir chamber's page
  `https://www.eskisehireo.org.tr/eskisehir-nobetci-eczaneler`, a plain `GET`
  (60 s timeout) of server-rendered HTML
  (`pharmacies/utils/eskisehireo_scraper.py`, `get_eskisehir_data`).
- **Format:** one `div.nobetci` per pharmacy. The `h4.text-danger` holds
  `NAME - DISTRICT`, the address follows the `fa-home` icon, the phone is the
  `tel:` link, the location is a `google.com/maps?q=<lat>,<lng>` link, and
  the duty window is a `span.text-danger` such as
  `28.10.2026 13:00 / 29.10.2026 08:30 nöbetçidir.`
- **Duty window: parsed.** `_get_duty_dates` reads the two dates and times
  from that span, so each pharmacy has its own window as the chamber
  publishes it (on 28 Oct 2026, a holiday eve, windows started at 13:00,
  18:00 or 18:30 and ended at 08:00, 08:30 or 09:00). The datetimes are
  naive; with `USE_TZ` Django stores them as `TIME_ZONE` (`Europe/Istanbul`)
  times, so 13:00 is stored as 10:00 UTC.
- **Quirks:**
  - The district is the last space-separated word of the heading
    (`_get_district_from_name`), so it is the chamber's `MERKEZ-ODUNPAZARI`
    form, not a plain district name. The name is the text before the first
    `-`.
  - The location is parsed by `get_coordinates_from_google_maps_url`, which
    takes everything after the last `=`. A pharmacy without a map link gets
    `coordinates` of `None`: a known pharmacy keeps its old location, but a
    new one makes `add_scraped_data_to_db` raise `TypeError`.
  - A malformed time span or map link raises `ValueError` or `IndexError`.
    `run_scraper` catches neither, nor that `TypeError`: the task fails and
    nothing of the scrape is written.

### Istanbul

- **Source:** the Health Ministry's e-Devlet service "TİTCK Nöbetçi Eczane
  Sorgulama", `https://www.turkiye.gov.tr/saglik-titck-nobetci-eczane-sorgulama`
  (no login). A `GET` of the form gives the session cookie and the `token`
  hidden input; one city-wide `POST` to `...?submit` with
  `ilkod-address-il=34` and `nobetTarihi` = the duty day on duty now
  (day/month/year, such as 31/10/2026; the Istanbul date until 09:00 belongs to
  the previous day's list) lists every district, so there is
  no per-district loop. Both requests have a 10 s timeout (`pharmacies/utils/istanbul_edevlet_scraper.py`,
  `get_istanbul_data`).
- **Format:** an HTML page with `table#searchTable`, one `tr` per pharmacy:
  district, name, address, phone, the source's own duty start and end text
  (not used), a status and a "Haritada Göster" link. The coordinates come from
  that link's map page, the `latti` and `longi` values in its
  `parseFloat(...)` calls, fetched with the session's cookies, four pages at a
  time (0.4 to 3 s each). The phone keeps digits only (`02163812112`).
- **Duty window: computed** from the time of the scrape and the city's
  `WorkingSchedule`, not read from the source (which also lists per-pharmacy
  start and end times, unused), by `get_duty_window`
  (`pharmacies/utils/duty_window.py`, shared with Ankara). Weekday: from
  `weekday_end` to the later of 06:00 UTC the next day and the next opening,
  so Friday's runs to `saturday_start`. Saturday: from `saturday_end` to
  Sunday 06:00 UTC. Sunday: 06:00 to Monday 06:00 UTC. A Turkish public
  holiday (Istanbul date) is a Sunday: 06:00 UTC that day to the later of
  06:00 and the next opening, and a working day before a holiday ends at
  06:00. On a half-day eve the window starts at 13:00 TRT (10:00 UTC) or the
  usual end if earlier, like `WorkingSchedule.is_open`. Before 06:00 UTC,
  and on Saturday before `saturday_start`, it is the window that started the
  previous day. With the seeded hours: Mon-Thu
  15:30 UTC (18:30 TRT) to 06:00 UTC (09:00 TRT), Friday to Saturday 07:00
  UTC, Saturday 15:00 UTC to Sunday 06:00 UTC. Every pharmacy of a scrape
  gets the same window.
- **Quirks:**
  - No list at all raises `RequestException`, so `run_scraper` logs an
    upstream failure instead of an empty duty list: a request error or HTTP
    error status, a form without its token, the form returned again (the
    query was rejected), a page without `table#searchTable`, or a table with
    no rows.
  - A map page that fails with any request error (connection error, timeout,
    HTTP error status) is retried once; about 3 to 8 % fail transiently. If the
    retry also fails, or the page has no valid coordinates, that pharmacy is
    skipped with a warning and the others are kept.
  - When four pharmacies in a row (in table order) still fail with a connection
    error or timeout after their retry, the host is taken as gone: the scrape
    raises `RequestException` and requests no further batch. Only a success
    resets that count; an HTTP error or a page without coordinates neither
    counts nor resets it.

### Ankara

- **Source:** the Ankara chamber's `https://www.aeo.org.tr/getPharmacies/<YYYY-MM-DD>`,
  the endpoint behind its duty page, a `GET` with redirects off (10 s
  timeout) (`pharmacies/utils/ankaraeo_scraper.py`, `get_ankara_data`). The
  date is the Istanbul date of the duty window's start, so before 09:00 TRT it
  is the previous day's list.
- **Format:** JSON `{"status": "success", "html": "..."}`; the HTML holds a
  notice paragraph and one `div.inline-box` per pharmacy, with `data-name`
  and `data-district` attributes, the address and phone in its `p`, and the
  location as the `query=<lat>,<lng>` parameter of a Google Maps link. Each
  date's list is the duty that starts that evening (on a Sunday or a public
  holiday, that morning); the notice may say
  otherwise ("29.10.2026 saat 08:30'a kadar 28.10.2026 tarihli nöbet listesi
  geçerlidir").
- **Duty window: computed**, with the same `get_duty_window` rules as
  Istanbul (`pharmacies/utils/duty_window.py`).
- **Quirks:**
  - A redirect, a non-JSON body, a status other than `success` or a missing
    `html` raises `AnkaraScraperError`, a `RequestException`. An entry
    without name, phone or location is skipped with a warning.
  - The phone keeps digits only, without leading zeros (`3122155354`), so it
    matches rows written from the chamber's older API.
  - The name is `data-name` in Turkish title case plus ` Eczanesi`
    (`_turkish_title`).
  - The notice's own times (13:00 on a holiday eve, 08:30 the next morning)
    are not read.

## Schedule

Beat uses `django_celery_beat`'s `DatabaseScheduler`, so the schedule is rows
in the database ([ADR 0007](../decisions/0007-drive-scrape-schedules-from-the-database-and-remove-their-tasks.md)).
Each city has five `PeriodicTask` rows that call
`pharmacies.tasks.run_scraper` with the city name:

| Task | Written by | When (as `seed_cities` sets it) |
|---|---|---|
| `Scrape <city> (<pk>)` | `ScraperConfig.save()` | every `interval` hours: 1 (model default 24) |
| `Scrape <city> Weekday Start` | `WorkingSchedule.save()` | Mon to Fri 05:30 UTC (08:30 TRT) |
| `Scrape <city> Weekday End` | `WorkingSchedule.save()` | Mon to Fri 15:30 UTC (18:30 TRT) |
| `Scrape <city> Saturday Start` | `WorkingSchedule.save()` | Sat 07:00 UTC (10:00 TRT) |
| `Scrape <city> Saturday End` | `WorkingSchedule.save()` | Sat 15:00 UTC (18:00 TRT) |

`WorkingSchedule` times are UTC and their crontabs use `timezone="UTC"`,
although `CELERY_TIMEZONE` is `Europe/Istanbul`. Deleting a `WorkingSchedule`
removes its four crontab tasks and deleting a `ScraperConfig` its interval
task, including through the admin's bulk delete and a `City` cascade
(`pre_delete` receivers in `pharmacies/models.py`). Renaming a city in
`City.save()` replaces its tasks with ones under the new name. In production beat runs on
`unit-01` and the worker on `monolith` ([production](production.md)).

## Ingest

`run_scraper` (`pharmacies/tasks.py`) is one scrape:

1. `get_city_data(city_name)` fetches the list.
2. An empty list is logged as a warning and nothing is written, so
   `ScraperConfig.last_run` stays as it was.
3. `_persist_scraped_data` runs, in one transaction,
   `add_scraped_data_to_db` and the update of `ScraperConfig.last_run` to
   now. A stale database connection (`InterfaceError`) gets one retry.
4. `JSONDecodeError` and `RequestException` (Ankara's `AnkaraScraperError`
   and Istanbul's no-list and unreachable-map-page failures included) are
   logged as a warning and the task ends without writing. Other errors fail
   the task.

`add_scraped_data_to_db` (`pharmacies/utils/utils.py`) loads the city's rows
once and keys them by `(name, phone)`
([ADR 0005](../decisions/0005-identify-a-pharmacy-by-name-and-phone-and-never-delete-rows.md)).
An unseen key becomes a new row (`bulk_create`). A known key gets its
`duty_start`, `duty_end`, `address` and `district` overwritten, and its
`location` when the scraped coordinates are valid (`_point_from_coordinates`),
in one `bulk_update`; ADR 0005's "only duty times update" predates that
change (#241). Rows are never deleted: a pharmacy missing from a scrape keeps
its old window, which simply passes.

`City.last_scraped_at` is not written by any scrape; freshness is
`ScraperConfig.last_run`.

## Open or duty pharmacies

`get_pharmacy_points` (`pharmacies/views.py`) answers
`POST /get_pharmacy_points` with `{"lat": ..., "lng": ...}`
([ADR 0006](../decisions/0006-serve-open-pharmacies-from-google-and-duty-pharmacies-from-the-database.md)):

1. It rounds the location to 4 decimals and finds the city by reverse
   geocoding (`get_city_name_from_location`), matching Google's province
   name against the `City` names with `normalize_string`.
2. `City.get_city_status` asks the city's `WorkingSchedule`: **open** inside
   working hours (Mon to Fri and Sat, start and end exclusive, compared in
   UTC), otherwise **closed**. Sunday is always closed, and so is a Turkish
   public holiday all day; on a half-day eve ("arefe": 28 Oct and the eves of
   Ramazan and Kurban Bayramı) the city is open from the usual start until
   13:00 TRT (10:00 UTC, or the usual end if earlier). The dates come from the
   `holidays` package (`holidays.Turkey`, categories `PUBLIC` and `HALF_DAY`,
   which computes the moving Bayram dates), looked up by the date of the
   query time in `Europe/Istanbul`. The computed duty windows of Istanbul
   and Ankara cover holidays and eves too, so a holiday daytime has rows on
   duty. In `DEBUG` the time is
   `TEST_TIME`, ten hours after the process started, not now.
3. **Open:** `get_nearest_pharmacies_open` asks Google Places for the nearest
   pharmacies (`fetch_nearest_pharmacies`, cached in the process). Nothing
   comes from this database.
4. **Closed:** `get_nearest_pharmacies_on_duty` takes the city's rows with
   `duty_start <= time <= duty_end`, the 10 nearest by distance. None gives a
   400, "No pharmacies are on duty at this time."
5. Either way `add_travel_distances_to_pharmacy_data` adds the travel
   distance from Google's Distance Matrix, the list is sorted by it, and the
   first 5 are returned.

So a city's duty windows matter only while it is closed, and a closed city
with no window covering the time answers 400.

## Data health

`GET /health/data/` (`data_health`) is public, makes no outbound call, is not
rate limited and is cached for 60 seconds. Per city it reports:

- `last_scrape`: `ScraperConfig.last_run`, the end of the last scrape that
  wrote something, or `null` if none has;
- `duty_now`: rows whose duty window covers now;
- `duty_next_12h`: rows whose window overlaps the next 12 hours.

```json
{"cities": {"ankara": {"last_scrape": "2026-10-28T19:39:46.674836+00:00", "duty_now": 66, "duty_next_12h": 66},
            "eskisehir": {"last_scrape": "2026-10-28T19:39:45.940562+00:00", "duty_now": 14, "duty_next_12h": 14},
            "istanbul": {"last_scrape": null, "duty_now": 0, "duty_next_12h": 0}},
 "time": "2026-10-28T19:46:29.814792+00:00"}
```

A city with an old `last_scrape` or `duty_now` of 0 while closed is the sign
of a broken scraper; the testenv answer above is Istanbul's (#204). Because
failed and empty scrapes leave `last_run` alone, `last_scrape` is the last
good scrape, not the last attempt; the attempts are in the worker's log.
