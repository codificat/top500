'''Utility functions and constants for URLs in the www.top500.org site.

We assume that all lists to date have been published, and that the latest
is always published on time.
'''

from datetime import date, timedelta

BASE_URL = "https://www.top500.org"

def last_edition():
    '''Computes the latest edition of the TOP500 list based on the
    current date.'''
    today = date.today()
    if today.month < 6:
        last = date(today.year-1, 11, 1)
    elif today.month < 11:
        last = date(today.year, 6, 1)
    else:
        last = date(today.year, 11, 1)
    return last

# The first list was published on June 1993
FIRST_LIST = date(1993, 6, 1)
LAST_LIST = last_edition()
VALID_MONTHS = (6, 11) # Lists are released June and November each year
VALID_YEARS = range(FIRST_LIST.year, LAST_LIST.year + 1)

class InvalidEdition(Exception):
    pass

def __is_valid(year, month):
    'Verifies that year, month are valid list edition references'
    return year in VALID_YEARS and month in VALID_MONTHS

def url_for(year, month, page=1):
    'Returns the URL of a page of the top500 list for year/month'
    if not __is_valid(year, month):
        raise InvalidEdition('%d/%d is not a valid edition' % (year,month))
    return "%s/list/%4d/%02d/?page=%d" % (BASE_URL, year, month, page)
