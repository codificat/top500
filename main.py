#!/usr/bin/env python
'''
A web scraper to extract the details of the most powerful commercial
computing systems in the world from the Top500 list.

See https://www.top500.org/
'''

import argparse
import csv
import requests
from top500.scraper import Scraper
from top500.urlgen import *

#
# Default values for command line options
#
DEFAULT_YEAR = LAST_LIST.year
DEFAULT_MONTH = LAST_LIST.month
DEFAULT_END_YEAR = DEFAULT_YEAR
DEFAULT_END_MONTH = DEFAULT_MONTH
DEFAULT_COUNT = 500
DEFAULT_OUTPUT_FILE = 'top500.csv'

def parse_options(dest):
    '''Parses and validate command line arguments
    '''

    parser = argparse.ArgumentParser()
    parser.add_argument('-y', '--year', help="[Start] Year of the list",
                        default=DEFAULT_YEAR, type=int, choices=VALID_YEARS)
    parser.add_argument('-m', '--month', help="[Start] Month of the list",
                        default=DEFAULT_MONTH, type=int, choices=VALID_MONTHS)
    parser.add_argument('-z', '--endyear', help="Collect until this year",
                        default=DEFAULT_END_YEAR, type=int, choices=VALID_YEARS)
    parser.add_argument('-n', '--endmonth', help="Collect until this month",
                        default=DEFAULT_END_MONTH, type=int, choices=VALID_MONTHS)
    parser.add_argument('-c', '--count', default=DEFAULT_COUNT, type=int,
                        help="Number of entries to get from each list")
    parser.add_argument('outfile', nargs='?', default=DEFAULT_OUTPUT_FILE,
                        type=argparse.FileType('w', encoding='utf-8'))

    parser.parse_args(namespace=dest)

class TOP500:
    def __init__(self):
        self.systems = []

    def write_data(self):
        csvwriter = csv.writer(self.outfile,
                               delimiter=',',
                               quotechar='"',
                               quoting=csv.QUOTE_MINIMAL)
        # Write column names
        csvwriter.writerow(self.systems[0].keys())
        # Write data
        for system in self.systems:
            csvwriter.writerow(system.values())

    def scrape(self):
        url = url_for(self.year, self.month)
        print("Downloading: %s" % url)
        page = requests.get(url)
        if page.status_code == 200:
            print("Scraping")
            scraper = Scraper()
            scraper.scrape_list_page(page)
            self.systems += scraper.get_systems()
            print("Scraped %d systems" % len(self.systems))
        else:
            print("Something went wrong: %d" % page.status_code)

if __name__ == '__main__':
    top = TOP500()
    parse_options(top)
    top.scrape()
    top.write_data()
