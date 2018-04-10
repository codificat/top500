
from datetime import date, timedelta

BASE_URL = "https://www.top500.org"

# The first list was published for June 1993
FIRST_LIST = date(1993, 6, 1)

today = date.today()
if today.month > 6:
    # Assuming that lists are published on time, we should have a list for this
    # year by now, so make sure this year is available in the range
    today += timedelta(weeks=52)

VALID_MONTHS = (6, 11) # Lists are released June and November each year
VALID_YEARS = range(FIRST_LIST.year, today.year)

def __is_valid(year, month):
    'Verifies that year, month are valid list edition references'
    return year in VALID_YEARS and month in VALID_MONTHS

def url_for(year, month):
    'Returns the URL of the first page of the list for year/month'
    if not __is_valid(year, month):
        return None
    return "%s/list/%4d/%02d" % (BASE_URL, year, month)
