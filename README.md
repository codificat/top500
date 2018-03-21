# Top 500 list web scraping

This is a project to do web scraping of the
[Top 500 list](https://www.top500.org/), which is a list of the fastest
supercomputers in the world.

The goal of this project is to extract the details of the computers from the
lists presented in the web site as HTML tables and store them in CSV format for
later processing.

## The top500.org web site structure

The lists are created twice a year (in June and November each year), and the web
site presents each edition of the list split across 5 pages, with 100 entries
each.

Each page has one table with one row per entry. Each row provides these details
about each supercomputer:

- **Rank**: the order of the supercomputer in that edition of the list
- **Site**: where is the supercomputer located
- **System**: name of the system
- **Cores**: number of compute cores
- **Rmax**: maximal LINPACK performance achieved (TFlop/s)
- **Rpeak**: theoretical peak performance
- **Power**: power consumption (kW)

Details of the collected information are available on their
[description page](https://www.top500.org/project/top500_description/).
