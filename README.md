[![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/lamdavid759/Silph-Factions-Data-Scraper/main)

# Silph Factions Data Scraper

## Project Motivation
This repository is dedicated to scraping data from a team-based competitive format for the mobile game [Pokémon GO](https://pokemongolive.com/). In addition to a collectable aspect, Pokémon GO offers a player vs. player (PvP) component where individual players can battle one another using teams of 3 Pokémon subject to some restrictions. In response to this feature, the local grassroots organization, [The Silph Road](https://thesilphroad.com/) has offered several different competitive opportunities through [The Silph Arena](https://silph.gg) for Pokémon GO trainers to play against others in a variant of this format, by setting specific rules on the allowed Pokémon (hereby called a meta) and allowing trainers to bring a team of 6 Pokémon, from which they will select 3. In addition to this individual focused mode of PvP, The Silph Road has also created a format called [Factions](https://silph.gg/factions/about) which brings alongside a team-based component to battling. 

Due to the specific nature of Factions, players know exactly who they will be playing against prior to the battle. This encourages building teams not only to fit a specific metagame, but also to counter preferences of the opponent. To facilitate quick and compact digesting of prior opponent teams, I started this project in order to effectively scrape all teams brought in each week of Silph Factions. In addition to providing my faction with information on week-to-week match-ups, this also provides a larger scale picture of the metagame as it evolves every week, allowing larger-scale analyses on which Pokémon contribute most effectively to winning for a given meta. This analysis has been used to provide more macroscopic trends and has also been featured on Twitch streams in post-mortem analysis of formats. As of date, over 170,000 unique teams have been scraped across several seasons of the Factions competition. 

## Project Outline
To obtain this data, I first scrape the active roster of each faction that can be found on a tier and region for the Silph Factions system. Then, I scrape the Silph Card of each trainer that is those rosters. Among other things, the Silph Card contains information on each Factions bout that the trainer contributes in. I use BeautifulSoup to effectively extract this data. After some cleaning of the data to standardize Pokémon names, the data is then stored as a pandas DataFrame for future manipulation. 

In addition, there is a sizeable fraction of the module devoted to programatically creating filters to filter down on the larger DataFrame. This feature is as of now restricted to use by importing [silph_factions_scraper.py](silph_factions_scraper.py) and using the functions directly. For convenience, a Binder link is now live, where you can do so directly in a Jupyter Notebook. 

## Usage
All scraped data periodically goes to the [Silph Factions Database](https://docs.google.com/spreadsheets/d/1r_iLB2JamSRHRJMjNrum2zbVJSA0uGJKQ9VqRprWYuk/edit#gid=1264267133) to provide an easy-to-use and maintain spreadsheet for team members to view opponent teams in order to gain a competitive advantage by identifying team composition preferences and range. This spreadsheet has very rudimentary filtering options, and also simple aggregating statistics to help describe a player's tendencies and most brought Pokémon. 

In addition, there is now a Binder link located at the top of this repository for more analysis via the [interactive notebook](Silph-Factions-Data-Scraper-Interactive.ipynb). This Jupyter notebook offers the additional functionality of having more sophisticated filters powered by pandas. 

## Future Plans for Improvement
Minor improvements to the code are implementing a function similar to the frequency tables found in the spreadsheet implementation so that a user could generate frequency tables of usage rates for a given filter criteria. 

More broadly, the strategy of scraping individual Silph Cards is relatively straightforward because the Silph Card is a static page, but as a result, additional information about the bout (namely, the competitor and their selected team) is lost, making it difficult to connect individual observations with the context surrounding the observations (i.e., did the player lose because their team was not matched up well or did they lose because of the Pokémon they used were rated worse in the meta?). Furthermore, the scrape is extremely time-intensive and redundant, as each page must be reaccessed for a few updates and the data scraped in its entirety. 

To address these two concerns, scraping directly from the Factions bout page (e.g., for Season 2, Cycle 3 in North America's Emerald tier, the bout page would be [here](https://silph.gg/factions/cycle/season-2-cycle-3-emerald-na)) would both be computationally more efficient and provide additional information. The problem is that these webpages are dynamically generated. To address this, I plan on using a combination of Selenium to simulate clicks and BeautifulSoup to scrape the data in the next iteration of this project. 
