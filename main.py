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

def parse_options():
    '''Parses and validate arguments
    '''

    parser = argparse.ArgumentParser()
    parser.add_argument('-y', dest='year', help="[Start] Year", required=True,
                        type=int, choices=VALID_YEARS)
    parser.add_argument('-m', dest='month', help="[Start] Month", required=True,
                        type=int, choices=VALID_MONTHS)

    args = parser.parse_args()
    return (args.year, args.month)

def scrape_url(url, csvfile):
    '''This function downloads one single page from one of the lists,
    extracts the data from the table and stores it in a file in CSV format.

    '''
    outfile = open(csvfile, 'w', newline='')
    csvwriter = csv.writer(outfile,
                           delimiter=',',
                           quotechar='"',
                           quoting=csv.QUOTE_MINIMAL)

    page = requests.get(url)
    scraper = Scraper()
    scraper.scrape_list_page(page)
    systems = scraper.get_systems()
    # Write column names
    csvwriter.writerow(systems[0].keys())
    # Write data
    for system in systems:
        csvwriter.writerow(system.values())
    outfile.close()

if __name__ == '__main__':
    (year, month) = parse_options()

    scrape_url(url_for(year, month), 'top100.csv')
