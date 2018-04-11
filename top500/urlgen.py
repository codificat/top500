#!/usr/bin/env python3

'''Utility functions and constants for URLs in the www.top500.org site.

We assume that all lists to date have been published, and that the latest
is always published on time.
'''

from datetime import date

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
    '''Exception raised when a date references a year/month that
    does not have a TOP500 list edition
    '''
    pass

def __ensure_valid(edition):
    'Verifies that year, month are valid list edition references'
    if not edition.year in VALID_YEARS:
        raise InvalidEdition('Invalid year: %d' % edition.year)
    if not edition.month in VALID_MONTHS:
        raise InvalidEdition('Invalid month: %d' % edition.month)

def __next(edition):
    '''Computes the next edition (date object)'''
    year = edition.year
    month = edition.month
    if month == 6:
        month = 11
    else:
        month = 6
        year += 1
    return date(year, month, 1)

def editions(start, end):
    '''Generator for list editions between 'start' and 'end', inclusive.
    Editions here are 'date' objects.
    '''
    __ensure_valid(start)
    __ensure_valid(end)
    edition = start
    while edition <= end:
        yield edition
        edition = __next(edition)

def url_for(edition, page=1):
    '''Returns the URL of a page of the top500 list for a specific edition.
    Params:
      - edition: a 'date' object.
      - page: page number
    '''
    __ensure_valid(edition)
    return "%s/list/%4d/%02d/?page=%d" % (BASE_URL,
                                          edition.year, edition.month, page)

if __name__ == '__main__':
    # Debug: list all the URLs this module would generate for
    # all the editions of the TOP500 list (only 1st page)
    for list_edition in editions(FIRST_LIST, LAST_LIST):
        print(url_for(list_edition))
