'''Scraper for the TOP500 list pages'''

import locale
import re
from difflib import SequenceMatcher
import requests
from bs4 import BeautifulSoup
from top500.urlgen import id_from_link, list_edition, url_for_system, url_for_site

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
    # Site information that comes from the site details page
    'site_url': 'site_url',
    'city': 'city',
    'segment': 'segment',
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

# The list of fields we know about for a site includes details that don't
# come from the details table: name comes from the header, ID comes from
# the URL
SITE_FIELDS = list(SITE_ROWS.values()) + ['site_id', 'site_name']

# Fields that store numeric values. These will be cleaned up (some entries
# include units) and their type will be updated
INTEGER_FIELDS = ('memory', 'cores', 'nmax', 'nhalf')
FLOAT_FIELDS = ('rmax', 'rpeak', 'power', 'hpcg')
NUMERIC_FIELDS = INTEGER_FIELDS + FLOAT_FIELDS

# The minimum ratio for difflib's SequenceMatcher to accept two strings
# as equal. This is used when cleaning up a system's listing entry by
# removing details about known other fields (processor, interconnect)
SM_RATIO = 0.79

# The site uses the en_US locale with UTF8 encoding. Setting this for
# the number parsing functions (i.e. separators)
locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')

class DownloadError(Exception):
    'A problem occurred while fetching a page with "requests.get"'
    pass

def _fetch(url, session):
    '''Downloads an URL and returns a 'requests' response object'''
    print("-- Downloading: %s" % url)
    page = session.get(url)
    if page.status_code != 200:
        raise DownloadError("Something went wrong: %d" % page.status_code)
    return page

def _numeric_value(var, val):
    '''Clean up a value for a numeric variable:
       - remove any text on it (e.g. units, thousands separators)
       - use correct type
    '''
    # Negative values are incorrect: there's no numeric variable in the
    # dataset where negative numbers make sense. If the value starts
    # with a minus we replace it with an empty value
    if re.match(r'-', val):
        return None

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

def _could_be(part1, part2):
    '''Helper function for fuzzy_remove: check if 2 items could be the same
    component/variable value'''
    #if part1 == part2 or part1 in part2 or part2 in part1:
    #    return True
    could_be = SequenceMatcher(None, part1, part2).ratio() > SM_RATIO
    return could_be

def _fuzzy_remove(parts, system):
    '''Attempts to detect known system parts to remove them, comparing strings
    with difflib's SequenceMatcher allowing "close enough" matches.

    For example, system 177556 has these parts in its listing name:
    ['Sequoia-BlueGene/Q', 'Power BQC 16C 1.60 GHz', 'Custom']

    In its details page, though, the interconnect is 'Custom Interconnect', and
    the processor is 'Power BQC 16C 1.6GHz'
    '''
    toremove = []
    for part in parts:
        if system['processor'] and _could_be(part, system['processor']):
            if not part in toremove:
                toremove.append(part)
        if system['interconnect'] and _could_be(part, system['interconnect']):
            if not part in toremove:
                toremove.append(part)
    for part in toremove:
        parts.remove(part)


class Scraper:
    "scrappety scrap"

    def __init__(self, entry_callback=None):
        self.entry_callback = entry_callback
        self.sites = {}
        self.systems = {}
        self.entries = []
        self.session = requests.Session()

    def __add_list_entry(self, entry):
        "Adds a system entry to the list"
        # We cache systems by their ID, so we don't have to re-scrape their
        # details pages.
        self.systems[entry['system_id']] = entry
        self.entries.append(entry)
        if self.entry_callback:
            self.entry_callback(entry)

    def __scrape_system_page(self, system_id):
        '''Downloads and scrapes a system's details page.
        Sample row from a details page:

            <tr>
                <th>Cores:</th>
                <td>12,345</td>
            </tr>

        Returns a dictionary of system properties.'''

        system = dict.fromkeys(ENTRY_FIELDS)
        system['system_id'] = system_id
        page = _fetch(url_for_system(system_id), self.session)
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
            except KeyError:
                print("Igoring unkown detail '%s' in system %s" %
                      (fieldname, system_id))
                continue
            system[variable] = value

        return system

    def __scrape_site_page(self, site_id):
        '''Downloads and scrapes a site's details page.
        Returns a dictionary of site properties with SITE_FIELDS as keys.
        '''

        site = dict.fromkeys(SITE_FIELDS)
        site['site_id'] = site_id
        page = _fetch(url_for_site(site_id), self.session)
        soup = BeautifulSoup(page.text, 'html.parser')

        # The name of the site is in the first non-empt H1 element
        # of a site details page
        for header in soup.find_all('h1'):
            site['site_name'] = header.get_text(strip=True)
            if site['site_name']:
                break

        # There are 3 tables in a Site details page:
        # - the details of the site itself
        # - a list of systems from the site
        # - a history of number of systems and ranks
        # We are only interested in the first list, the others can be
        # computed from the rest of the data
        for row in soup.table.find_all('tr'):
            try:
                fieldname = row.th.get_text(strip=True)
                variable = SITE_ROWS[fieldname]
                value = row.td.get_text(strip=True)
            except KeyError:
                print("Igoring unkown site detail '%s' in site %s" %
                      (fieldname, site_id))
                continue
            site[variable] = value

        return site

    def __get_site_details(self, site_id):
        '''Find details about a site. Check the site cache first, scrape
        if not found.
        '''
        try:
            site = self.sites[site_id]
        except KeyError:
            site = self.__scrape_site_page(site_id)
            # Add it to the cache
            self.sites[site_id] = site
        return site

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
            system = self.__scrape_system_page(system_id)
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
        parts = link.get_text(strip=True).split(',')
        parts = [x.strip() for x in parts]

        # Remove the components that we already have in the details
        _fuzzy_remove(parts, system)

        # Once the interconnect and processor are removed, the first
        # element is assumed to be the system name
        if parts:
            system['name'] = parts.pop(0)
        else:
            # If we are here it very likely means we should tune SM_RATIO
            # because it removed all parts thinking they belonged elsewhere
            print('... Warning: System without name')
            system['name'] = 'Unknown'

        # Any remaining content is assumed to be the GPU/co-processor.
        # It should be one part, but some systems have extra content.
        if parts:
            system['gpu'] = ', '.join(parts)

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

    def __parse_site_column(self, system, col):
        '''Parses a column value corresponding to a site in one of the
        list pages. Such a column looks like this:

          <td><a href="/site/SITE_ID">SITE_NAME</a><br>COUNTRY</td>

        We are only interested in the SITE_ID; the rest of a site's
        details are scraped from the site's details page (and cached).

        Params:
         - system: the dict object for the system, where site details
           will be added
         - col: a BeautifulSoup Tag object corresponding to the TD
           element with the data to parse.
        '''
        link = col.a
        site = self.__get_site_details(id_from_link(link['href']))
        system.update(site)

    def set_entry_callback(self, callback):
        'Sets the callback function to be called when a list entry is added'
        self.entry_callback = callback

    def get_list(self):
        "Returns the list of scraped systems"
        return self.entries

    def scrape_list_page(self, url, limit=100):
        '''This function parses one single page from one of the lists,
        to extracts the data from the table

        '''
        edition = list_edition(url)

        page = _fetch(url, self.session)
        soup = BeautifulSoup(page.text, 'html.parser')

        rows = soup.find_all('tr')
        count = 0
        for row in rows:
            if count > limit:
                print("... Partial scraping of %d entries from the page"
                      % limit)
                break
            count += 1

            cols = row.find_all('td')
            if not cols or len(cols) != len(LIST_COLS):
                # If there are no TDs in this row it means we must be
                # in the header row, which uses TH instead of TD.
                # The code below assumes LIST_COLS are present, so
                # we check we have so many cols.
                continue
            entry = dict.fromkeys(ENTRY_FIELDS)
            self.__parse_system_column(entry, cols[2])
            self.__parse_site_column(entry, cols[1])
            entry['rank'] = int(cols[0].get_text())
            entry['year'] = edition.year
            entry['month'] = edition.month
            entry['cores'] = locale.atoi(cols[3].get_text())
            entry['rmax'] = locale.atof(cols[4].get_text())
            entry['rpeak'] = locale.atof(cols[5].get_text())
            # Several systems don't provide details about Power
            try:
                entry['power'] = locale.atof(cols[6].get_text())
            except ValueError:
                entry['power'] = None

            self.__add_list_entry(entry)
