#!/usr/bin/env python

import locale
import re
from bs4 import BeautifulSoup

# Columns in a site list page's table
LIST_COLS = ('rank', 'site', 'system', 'cores', 'rmax', 'rpeak', 'power')

# The list of rows with details about a site, on the site's details page
SITE_ROWS = ('URL', 'Segment', 'City', 'Country')

# The list of rows on a system's details page
SYSTEM_ROWS = {
    'Site:': 'site',
    'Manufacturer:': 'manufacturer',
    'Cores:': 'cores',
    'Memory:': 'memory',
    'Processor:': 'processor',
    'Interconnect:': 'interconnect',
    'Linpack Performance (Rmax)': 'rmax',
    'Theoretical Peak (Rpeak)': 'rpeak',
    'Nmax': 'nmax',
    'Nhalf': 'nhalf',
    'HPCG [TFlop/s]': 'hpcg',
    'Power:': 'power',
    'Operating System:': 'os',
    'Compiler:': 'compiler',
    'Math Library:': 'math',
    'MPI:': 'mpi',
}

def _list_edition(page):
    '''Identifies which edition of the list a page corresponds to,
    based on its URL.
    Params: page: a 'requests' Response object for the page
    Returns: a tuple: (year, month)
    '''
    match = re.search(r'/list/(\d{4})/(\d{2})', page.url)
    if not match:
        return (None, None)
    year = int(match.group(1))
    month = int(match.group(2))
    return (year, month)

def id_from_link(link):
    '''Expects an URL of the form "https://some.thing/some/path/XXXX
    and returns XXXX
    '''
    match = re.search(r'(\d+)$', link)
    if match:
        return int(match.group(0))
    return None

def _parse_system_column(system, col):
    '''Parses a column value corresponding to a system in one of the
    list pages. These include various system details. Such a column
    looks like this:

      <td><a href="https://www.top500.org/system/SYSTEM_ID">
          SYSTEM_NAME
      </a><br/>MANUFACTURER</td>

    Params:
     - system: the dict object for the system, where system details
       will be added
     - col: a BeautifulSoup Tag object corresponding to the TD
       element with the data to parse.
    '''
    link = col.a
    system['system_url'] = link['href']
    system['system_id'] = id_from_link(system['system_url'])
    system['system_name'] = link.get_text(strip=True)
    # Remove system details, so we're left only with manufacturer
    link.decompose()
    system['manufacturer'] = col.get_text(strip=True)

def _parse_site_column(system, col):
    '''Parses a column value corresponding to a site in one of the
    list pages. Such a column looks like this:

      <td><a href="https://www.top500.org/site/SITE_ID">
          SITE_NAME</a><br>COUNTRY</td>

    Params:
     - system: the dict object for the system, where site details
       will be added
     - col: a BeautifulSoup Tag object corresponding to the TD
       element with the data to parse.
    '''
    link = col.a
    system['site_url'] = link['href']
    system['site_id'] = id_from_link(system['site_url'])
    system['site_name'] = link.get_text(strip=True)
    # Remove system details, so we're left only with the country
    link.decompose()
    system['country'] = col.get_text(strip=True)

class Scraper:
    "scrappety scrap"

    def __init__(self):
        # TODO: ideally set locale from page content and headers instead of
        # hardcoding
        locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')
        self.systems = []

    def __add_system(self, system):
        "Adds a system to the list"
        self.systems.append(system)

    def get_keys(self):
        '''Returns a list of keys for the systems.
        Assumes all systems have the same keys'''
        if self.systems:
            return self.systems[0].keys()
        return []

    def get_systems(self):
        "Returns the list of scraped systems"
        return self.systems

    def scrape_list_page(self, page):
        '''This function parses one single page from one of the lists,
        to extracts the data from the table

        '''
        (year, month) = _list_edition(page)
        if not year or not month:
            # TODO something's wrong, raise an exception
            return

        soup = BeautifulSoup(page.text, 'html.parser')

        rows = soup.find_all('tr')
        for row in rows:
            cols = row.find_all('td')
            if not cols or len(cols) != len(LIST_COLS):
                # If there are no TDs in this row it means we must be
                # in the header row, which uses TH instead of TD.
                # The code below assumes LIST_COLS are present, so
                # we check we have so many cols.
                # TODO: improve validation for the list structure
                continue
            system = dict(rank=int(cols[0].get_text()))
            system['year'] = year
            system['month'] = month
            _parse_site_column(system, cols[1])
            _parse_system_column(system, cols[2])
            system['cores'] = locale.atoi(cols[3].get_text())
            system['rmax'] = locale.atof(cols[4].get_text())
            system['rpeak'] = locale.atof(cols[5].get_text())
            try:
                system['power'] = locale.atof(cols[6].get_text())
            except ValueError:
                system['power'] = None

            self.__add_system(system)
