#!/usr/bin/env python
'''
A web scraper to extract the details of the most powerful commercial
computing systems in the world from the Top500 list.

See https://www.top500.org/
'''

import csv
import requests
from top500.scraper import Scraper

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
    for system in systems:
        csvwriter.writerow(system.values())
    outfile.close()

if __name__ == '__main__':
    # Scrape the top 100 of the June 2017 list
    scrape_url('https://www.top500.org/list/2017/06/', 'top100.csv')
