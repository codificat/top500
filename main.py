#!/usr/bin/env python3
'''
A web scraper to extract the details of the most powerful commercial
computing systems in the world from the Top500 list.

See https://www.top500.org/
'''

import argparse
import csv
import sys
from datetime import date
from top500.scraper import Scraper, ENTRY_FIELDS
from top500.urlgen import url_for_list, LAST_LIST, editions, VALID_YEARS, VALID_MONTHS

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

    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument('-y', '--year', help="Collect from year",
                        default=DEFAULT_YEAR, type=int,
                        choices=VALID_YEARS)
    parser.add_argument('-m', '--month', help="Collect from month",
                        default=DEFAULT_MONTH, type=int,
                        choices=VALID_MONTHS)
    parser.add_argument('-z', '--endyear', help="Collect until year",
                        default=DEFAULT_END_YEAR, type=int,
                        choices=VALID_YEARS)
    parser.add_argument('-n', '--endmonth', help="Collect until month",
                        default=DEFAULT_END_MONTH, type=int,
                        choices=VALID_MONTHS)
    parser.add_argument('-c', '--count', default=DEFAULT_COUNT, type=int,
                        help="Number of entries to get from each edition")
    parser.add_argument('-f', '--force', action='store_true',
                        help="Force a partial count")
    parser.add_argument('outfile', nargs='?', default=DEFAULT_OUTPUT_FILE,
                        help="Output file",
                        type=argparse.FileType('w', encoding='utf-8'))
    parser.parse_args(namespace=dest)

    if dest.count < 1 or dest.count > 500:
        parser.error("COUNT must be >1 and <500 (in hundreds unless forced)")
    if dest.count % 100 != 0 and not dest.force:
        parser.error("COUNT must be in hundreds. Use --force to override")
    if dest.endyear < dest.year or \
       (dest.endyear == dest.year and dest.endmonth < dest.month):
        parser.error("End year/month must be >= start year/month")

class TOP500:
    '''Main logic for the TOP500 website scraping'''

    # pylint: disable=too-many-instance-attributes
    def __init__(self):
        self.year = DEFAULT_YEAR
        self.month = DEFAULT_MONTH
        self.endyear = DEFAULT_END_YEAR
        self.endmonth = DEFAULT_END_MONTH
        self.count = DEFAULT_COUNT
        self.outfile = sys.stdout
        self.csvwriter = None
        self.scraper = Scraper()

    def init_writer(self):
        '''Initialize the CSV writer on top of the output file. This is not done
        inside __init__ to allow options to set a differnt outfile
        '''
        self.csvwriter = csv.writer(self.outfile,
                                    delimiter=',',
                                    quotechar='"',
                                    quoting=csv.QUOTE_MINIMAL)
        # Write header (column names)
        self.csvwriter.writerow(ENTRY_FIELDS)

    def write_entry(self, entry):
        'Writes an entry to the output file in CSV format'
        self.csvwriter.writerow(entry.values())

    def write_all(self):
        '''Alternative approach to writing: when calling scrape() with
        write=False, no entries will be written to the file during the
        scraping process. You can then call write_all() to write them
        all at once.'''
        self.init_writer()
        entries = self.scraper.get_list()
        if entries:
            for entry in entries:
                self.csvwriter.writerow(entry.values())
            print("Wrote a total of %d entries" % len(entries))

    def scrape(self, write=True):
        '''Scraping function. It drives the scraping by obtaining each of
        the list's pages and calling the scraper for each.'''
        if write:
            self.init_writer()
            self.scraper.set_entry_callback(self.write_entry)

        start = date(self.year, self.month, 1)
        end = date(self.endyear, self.endmonth, 1)
        pages = int(self.count / 100)
        limit = self.count % 100
        if limit:
            # The user requested a partial page
            pages += 1
        for edition in editions(start, end):
            print("* Scraping TOP500 list edition: %d/%d" % (edition.year, edition.month))
            for page in range(pages):
                pagenum = page + 1
                print("** Page %d of %d" % (pagenum, pages))
                url = url_for_list(edition, pagenum)
                if pagenum == pages and limit:
                    # Only partially parse the last page as requested
                    self.scraper.scrape_list_page(url, limit)
                else:
                    self.scraper.scrape_list_page(url)

if __name__ == '__main__':
    top500 = TOP500()  # pylint: disable=invalid-name
    parse_options(top500)
    top500.scrape()
