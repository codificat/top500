
import locale
import requests
from bs4 import BeautifulSoup
from top500.urlgen import *

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

class DownloadError(Exception):
    'A problem occurred while fetching a page with "requests.get"'
    pass

def _fetch(url):
    '''Downloads an URL and returns a 'requests' response object'''
    print("Downloading: %s" % url)
    page = requests.get(url)
    if page.status_code != 200:
        raise DownloadError("Something went wrong: %d" % page.status_code)
    return page

def _get_system_details(system, link):
    '''Parses system details in the text within a link in a listing.

    Details can include the system name, processor, interconnect or GPU.
    Information is obtained from the text within the link and from the
    system's dedicated details page.

    Params:
     - system: the dict object for the system, where system details
       will be added
     - link: a BeautifulSoup Tag object corresponding to the A
       element with the data to parse.
    '''

    # Parse the text within the link.
    # NOTE: some systems have GPU information in their name!!!
    # e.g. https://www.top500.org/system/177996. For these, rsplit
    # instead of split works; but this breaks others that properly
    # list multiple co-processors at the end
    parts = link.get_text(strip=True).split(',', 3)
    system['system_name'] = parts[0].strip()
    if len(parts) > 1:
        system['processor'] = parts[1].strip()
    else:
        system['processor'] = None
    if len(parts) > 2:
        system['interconnect'] = parts[2].strip()
    else:
        system['interconnect'] = None
    if len(parts) > 3:
        system['gpu'] = parts[3].strip()
    else:
        # Assume that the missing part is GPU.
        # FIXME: this is not true on all systems,
        # e.g. https://www.top500.org/system/176929
        system['gpu'] = None

def _parse_system_column(system, col):
    '''Parses a column value corresponding to a system in one of the
    list pages. These include various system details. Such a column
    looks like this:

      <td><a href="https://www.top500.org/system/SYSTEM_ID">
          SYSTEM_NAME, PROCESSOR, INTERCONNECT, GPU
      </a><br/>MANUFACTURER</td>

    However, the details of name, processor, interconnect or GPU
    vary wildly across systems, so they are parsed in a specific
    function and completed with the system details page.

    Params:
     - system: the dict object for the system, where system details
       will be added
     - col: a BeautifulSoup Tag object corresponding to the TD
       element with the data to parse.
    '''
    link = col.a
    system['system_id'] = id_from_link(link['href'])
    _get_system_details(system, link)
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
    system['site_id'] = id_from_link(link['href'])
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

    def scrape_list_page(self, url):
        '''This function parses one single page from one of the lists,
        to extracts the data from the table

        '''
        edition = list_edition(url)

        page = _fetch(url)
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
            system['year'] = edition.year
            system['month'] = edition.month
            _parse_site_column(system, cols[1])
            _parse_system_column(system, cols[2])
            system['cores'] = locale.atoi(cols[3].get_text())
            system['rmax'] = locale.atof(cols[4].get_text())
            system['rpeak'] = locale.atof(cols[5].get_text())
            # Several systems don't provide details about Power
            try:
                system['power'] = locale.atof(cols[6].get_text())
            except ValueError:
                system['power'] = None

            self.__add_system(system)
