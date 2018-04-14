
import locale
import re
import requests
from bs4 import BeautifulSoup
from top500.urlgen import id_from_link, list_edition, url_for_system

# The list of fields we know about for a system.
# This is a dictionary where the keys are the name of the fields
# as found in the TOP500 system details page (i.e. the table headers),
# and the values are the resulting name of the field (i.e. what will be
# stored in the generated data set).
SYSTEM_FIELDS = {
    'Site:': 'site_name',
    'System URL:': 'system_url',
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
    # Fields that don't come directly from full column values:
    'gpu': 'gpu',             # the coprocessor/GPU is a sub-field
    'country': 'country',     # country is a sub-field in the listings
    'site_id': 'site_id',     # site_id is taken from its URL
    'system_id': 'system_id', # the system_id is taken from its URL
    'name': 'name',           # the name is a sub-field in the listing
}

# The complete list of fields that we store for each list entry.
# This is: the fields about a system's details, plus the list edition
# (year and month) and the corresponding rank.
ENTRY_FIELDS = list(SYSTEM_FIELDS.values()) + ['year', 'month', 'rank']

# Which columns do we find in a TOP500 list page's table.
# Note that the table in the highlights page for each edition (the page
# that only lists the top 10 systems) has one less column (it combines
# site and system). We don't scrape that page as it's redundant.
LIST_COLS = ('rank', 'site', 'system', 'cores', 'rmax', 'rpeak', 'power')

# The list of rows with details about a site, on the site's details page
SITE_ROWS = {
    'URL': 'site_url',
    'City': 'city',
    'Country': 'country',
    'Segment': 'segment'
}

# Fields that store numeric values. These will be cleaned up (some entries
# include units) and their type will be updated
INTEGER_FIELDS = ('memory', 'cores', 'nmax', 'nhalf')
FLOAT_FIELDS = ('rmax', 'rpeak', 'power', 'hpcg')
NUMERIC_FIELDS = INTEGER_FIELDS + FLOAT_FIELDS

# The site uses the en_US locale with UTF8 encoding. Setting this for
# the number parsing functions (i.e. separators)
locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')

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

def _numeric_value(var, val):
    '''Clean up a value for a numeric variable:
       - remove any text on it (e.g. units, thousands separators)
       - use correct type
    '''
    match = re.match(r'([\d,.]+)', val)
    if not match:
        # The provided value doesn't start with a number
        return val
    value = match.group(0)
    if var in INTEGER_FIELDS:
        value = locale.atoi(value)
    elif var in FLOAT_FIELDS:
        value = locale.atof(value)
    return value

def _scrape_system_page(system_id):
    '''Downloads and scrapes a system's details page.
    Sample row from a details page:

        <tr>
            <th>Cores:</th>
            <td>12,345</td>
        </tr>

    Returns a dictionary of system properties.'''

    system = dict.fromkeys(ENTRY_FIELDS)
    system['system_id'] = system_id
    page = _fetch(url_for_system(system_id))
    soup = BeautifulSoup(page.text, 'html.parser')

    # There are two tables in a system details page: the details
    # themselves and the history of ranks. We scrape the first one.
    for row in soup.table.find_all('tr'):
        try:
            header = row.th
            if header.has_attr('colspan'):
                # This row is a title/category, it doesn't contain any variable
                continue
            fieldname = header.get_text(strip=True)
            variable = SYSTEM_FIELDS[fieldname]
            value = row.td.get_text(strip=True)
            if variable in NUMERIC_FIELDS:
                value = _numeric_value(variable, value)
            # TODO: clean up values: remove units (TFlop/s, kW, ...) and convert
            # types. Note that this is not necessary for some fields like cores,
            # rmax or rmax, as they will be overriden by the values from the
            # list's page, which are more current.
        except KeyError:
            print("Igoring unkown detail '%s' in system %s" %
                  (fieldname, system_id))
            continue
        system[variable] = value

    return system

class Scraper:
    "scrappety scrap"

    def __init__(self):
        self.systems = {}
        self.entries = []

    def __add_list_entry(self, entry):
        "Adds a system entry to the list"
        self.entries.append(entry)

    def __get_system_details(self, system_id):
        '''Find details about a system. Check if we scraped its details before,
        and if not, scrape them.
        Note: we don't add the scraped system to the cache here, we only add it
        when all details are scraped - i.e. we cache full list entries. This saves
        a bit of time and memory.
        '''
        try:
            system = self.systems[system_id]
        except KeyError:
            system = _scrape_system_page(system_id)
        return system

    def __parse_system_details(self, system, link):
        '''Parses system details in the text within a link in a listing.

        Details can include the system name, processor, interconnect or GPU.
        Information is obtained from the text within the link and from the
        system's dedicated details page.

        Params:
         - system: the dict object for the system, where system details
           will be added. It must already have its system_id filled in
         - link: a BeautifulSoup Tag object corresponding to the A
           element with the data to parse.
        '''

        details = self.__get_system_details(system['system_id'])
        # Update only the fields that we found about
        system.update({field: details[field]
                       for field in ENTRY_FIELDS if details[field]})

        # Parse the text within the link.
        # NOTE: some systems have GPU information in their name!!!
        # e.g. https://www.top500.org/system/177996. For these, rsplit
        # instead of split works; but this breaks others that properly
        # list multiple co-processors at the end
        parts = link.get_text(strip=True).split(',', 3)
        system['name'] = parts[0].strip()
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

    def __parse_system_column(self, system, col):
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
        self.__parse_system_details(system, link)
        # Remove system details, so we're left only with manufacturer
        link.decompose()
        system['manufacturer'] = col.get_text(strip=True)

    def get_keys(self):
        '''Returns a list of keys (variable names) for list entries.
        If the entries list is empty (no data yet) it returns None.
        '''
        if not self.entries:
            return None
        return ENTRY_FIELDS

    def get_list(self):
        "Returns the list of scraped systems"
        return self.entries

    def scrape_list_page(self, url, limit=100):
        '''This function parses one single page from one of the lists,
        to extracts the data from the table

        '''
        edition = list_edition(url)

        page = _fetch(url)
        soup = BeautifulSoup(page.text, 'html.parser')

        rows = soup.find_all('tr')
        count = 1
        for row in rows:
            if count > limit:
                break
            count += 1

            cols = row.find_all('td')
            if not cols or len(cols) != len(LIST_COLS):
                # If there are no TDs in this row it means we must be
                # in the header row, which uses TH instead of TD.
                # The code below assumes LIST_COLS are present, so
                # we check we have so many cols.
                # TODO: improve validation for the list structure
                continue
            entry = dict.fromkeys(ENTRY_FIELDS)
            entry['rank'] = int(cols[0].get_text())
            entry['year'] = edition.year
            entry['month'] = edition.month
            _parse_site_column(entry, cols[1])
            self.__parse_system_column(entry, cols[2])
            entry['cores'] = locale.atoi(cols[3].get_text())
            entry['rmax'] = locale.atof(cols[4].get_text())
            entry['rpeak'] = locale.atof(cols[5].get_text())
            # Several systems don't provide details about Power
            try:
                entry['power'] = locale.atof(cols[6].get_text())
            except ValueError:
                entry['power'] = None

            self.__add_list_entry(entry)
