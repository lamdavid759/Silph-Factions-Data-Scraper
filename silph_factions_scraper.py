# Page requests and web scraping
import requests
from bs4 import BeautifulSoup
import re
import csv
import time

# Writing results
import pandas as pd 

# Caching
import os
from ediblepickle import checkpoint
from urllib.parse import quote

# Global variables to manage the caching directories of the script. 
player_cache = "__player_cache__" 
faction_cache = "__faction_cache__"

# Faction Information
factions_url_base = "https://silph.gg/factions/cycle/season-2-cycle-3-" # Only thing that should be changed from cycle to cycle. 
factions_tiers = ["iron", "copper", "bronze", "silver", "gold", "platinum", "diamond", "emerald"]
factions_regions = ["na", "latam", "emea", "apac"]
results_categories = ["region", "tier", "faction", "player", "format", "season", "cycle", "bout", "record", "mon1", "mon2", "mon3", "mon4", "mon5", "mon6"]

# Function to set up cache directories
def _setup_cache(path): 
    """
    Helper function to set-up a cache directory for the setpoint. 
    Arguments: 
    - cache_dir: 
        path string for cache directory. Can be absolute or relative. Default is "cache"
    """
    if not os.path.exists(path):
        os.mkdir(path)

# Functions to generate the rosters for Silph Factions        
def generate_rosters(tiers = factions_tiers, regions = factions_regions, url_base = factions_url_base):
    """
    Function to generate active Silph Factions rosters for a specified season/cycle, tiers 
    and regions. 
    Arguments: 
    - url_base: 
        URL that points to latest Silph Season and Cycle; Format is 
        "https://silph.gg/factions/cycle/season-(season#)-cycle-(cycle#)-"
        Default value of "https://silph.gg/factions/cycle/season-2-cycle-3-"
    - tiers: 
        list of strings that correspond to valid Silph tier(s). 
        Must be input as a list, even with 1 element. 
        Default value of ["iron", "copper", "bronze", "silver", "gold", "platinum", 
                            "diamond", "emerald"] 
    - regions: 
        list of strings that correspond to valid Silph region(s). Must be input as a list, 
        even with 1 element. 
        Default value of ["na", "latam", "emea", "apac"]
    Returns:
    - faction_rosters: 
        a dictionary of {faction: [members]} in str: list of str format
    """
    faction_rosters = {}
    for tier in tiers:
        for region in regions: 
            faction_rosters = {**faction_rosters, **tier_region_scrape(tier, region, url_base)}
    return faction_rosters

@checkpoint(key=lambda args, kwargs: quote(args[0]+"_"+args[1]+".pkl"), work_dir=faction_cache)
def tier_region_scrape(tier, region, url_base = factions_url_base):
    """
    Function to scrape faction roster information for a given tier and region, as specified 
    by Silph Factions. 
    Arguments: 
    - tier: 
        str for valid tier in Silph Factions
    - region: 
        str for valid region in Silph Factions
    - url_base: 
        URL that points to latest Silph Season and Cycle; Format is 
        "https://silph.gg/factions/cycle/season-(season#)-cycle-(cycle#)-"
    Returns: 
    - factions_rosters: 
        a dict of {str: list of strs} where the key is the faction name and the value is a 
        list of active factions members. 
    """
    faction_rosters = {}
    
    url = url_base + tier + "-" + region
    page = requests.get(url)
    if page.status_code != 200: 
        return faction_rosters # If the page does not correspond to a valid tier/region, return an empty dict
    
    soup = BeautifulSoup(page.content, "html.parser")
    for faction in soup.find_all("div",class_="nameWrapper"): 
        faction_name = faction.find("p").get_text()
        faction_url = "https://silph.gg" + faction.find("a").get("href")
        faction_roster = []
        faction_page = requests.get(faction_url)
        faction_soup = BeautifulSoup(faction_page.content, "html.parser")
        for player in faction_soup.findAll(True, {"class":["playerName", "playerName long"]}): 
            faction_roster.append(player.get_text().strip())
        faction_rosters[faction_name] = faction_roster
    return faction_rosters

# Functions to process an individual user's Silph Factions directory
@checkpoint(key=lambda args, kwargs: quote(args[0]) + '.pkl', work_dir=player_cache)
def individual_user_scrape(username):
    """
    Function to scrape an individual user's results from their Silph Card. 
    Arguments: 
    - username: 
        String of properly formatted Silph username. 
    Returns: 
        pd.DataFrame of tournament results for an user
    """
    all_results = []
    #Initializes web scrape
    page = requests.get("https://sil.ph/" + username)
    soup = BeautifulSoup(page.content, "html.parser")
    silph_data = soup.find("div",id="networkAndAchievements")
    # Checks to see if someone is banned/no longer exists
    if silph_data == None: 
        return pd.DataFrame(all_results, columns=results_categories) 
        
    tournament_results = silph_data.find_all("div",class_="tournament")
    
    for result in tournament_results: 
        parsed_result = tournament_result_parse(result, username)
        if parsed_result: 
            all_results.append(parsed_result)
    return pd.DataFrame(all_results, columns=results_categories)

def tournament_result_parse(result, username): 
    """
    Helper function to parse the HTML of a specific tournament result as scraped from the 
    Silph User card. 
    Arguments: 
    - result: 
        A HTML snippet with the div tag "tournament" that denotes 
        an individual tournament entry.
    - username: 
        str of the username for the specific tournament result we are trying to parse. 
    Returns:
        For valid factions bouts, returns a list in the following order: 
            [region: str, tier: str, faction: str, username: str, cup_type: str, season: 
            int, cycle: int, bout_number: int, record: str] + roster: list of strs
        For non-factions bouts, returns the empty list. 
    """
    
    # Checks if the URL for the given event is a Faction bout and excludes postseason events or any alternative factions-esque bouts
    excluded = ["Global Melee", "World Championship", "Torneo"]
    if result.select("a[href*=faction]") == [] or any(map(result.find("div",class_="arenaBadge")["title"].__contains__, excluded)):
        return []

    faction = result.find("a", class_="logo")["title"] # Faction at time of battle

    # Conditional formatting to change cupType into proper form, then into database entry
    cup_type = result.find("h5", class_="cupType").text.strip().strip("★").strip()
    if "Great" in cup_type: cup_type = "Great"
    elif "Ultra" in cup_type: cup_type = "Ultra"
    elif "Master" in cup_type: cup_type = "Master"    

    # Checks URL for bout information (season, cycle, tier) and region
    bout_url = result.find("a").get("href")
    region = ""
    season = -1
    cycle = -1
    tier = ""
    if "may-2021-qualifiers" in bout_url:
        pattern = "https://silph.gg/factions/cycle/may-2021-qualifiers-(.*)"
        region = re.findall(pattern,bout_url)[0].upper()
        season = 0
        cycle = 1
        tier = "Qualifiers"
    elif "preseason-cycle-2-qualifiers" in bout_url:
        pattern = "https://silph.gg/factions/cycle/preseason-cycle-2-qualifiers-(.*)"
        region = re.findall(pattern,bout_url)[0].upper()
        season = 0
        cycle = 2
        tier = "Qualifiers"
    elif "season-" in bout_url:
        pattern = "https://silph.gg/factions/cycle/season-(.*)-cycle-(.*)-(.*)-(.*)"
        parsedBoutInfo = re.findall(pattern,bout_url)
        season = parsedBoutInfo[0][0]
        cycle = parsedBoutInfo[0][1]
        tier = parsedBoutInfo[0][2].title()
        region = parsedBoutInfo[0][3].upper()

    # Manually fixes some inconsistent data parsing
    if region == "": region = "Not Available"
    if region == "EU": region = "EMEA"
    if tier == "": tier = "Not Available"

    # Checks title for bout number
    bout_info = result.find("h5", class_="tourneyName").text.strip()
    pattern = "Bout (.*): (.*)"
    parsed_bout_number = re.findall(pattern,bout_info)
    #Check to see if this particular bout was part of a promotion/relegation battle
    if parsed_bout_number[0][1] == "Promotions/Relegations": bout_number = 8 
    else: bout_number = int(parsed_bout_number[0][0])

    record = result.find(class_="win").find("h3", class_="value").text+'-'+result.find(class_="loss").find("h3", class_="value").text

    roster = [pokemon_name_clean(mon) for mon in result.find_all(class_="pokemon")]
    
    return [region, tier, faction, username, cup_type, int(season), int(cycle), int(bout_number), record] + roster

def pokemon_name_clean(pokemon_html): 
    """ 
    Helper function to standardize Pokemon name formatting: 
    Arguments: 
    - pokemon: 
        HTML snipped scraped from Silph's website that contains the information of a 
        specific Pokemon. 
        The Pokemon name will be formatted in the following way: 
        (Base Name)-(Forme/Region/Size/Cloak)*-(S)*
        where the fields denoted in * correspond to alternative formes and an optional 
        designation of whether a Pokemon is shadow. 
    Returns:
    - cleaned_name: 
        reformatted Pokemon name as a str
    """
    name = pokemon_html["title"]
    
    if name == 'Armored Mewtwo': name = 'Mewtwo-Armor'
    elif "Alolan" in name: name = name.replace('Alolan ', '') + '-Alola'
    elif "Galarian" in name: name = name.replace('Galarian ', '') + '-Galar'
    elif "Hisuian" in name: name = name.replace('Hisuian ', '') + '-Hisui'
    elif "Forme" in name: 
        pattern = '\s\(*'
        result = re.split(pattern,name)
        name = result[0]+"-"+result[1]
    elif "Cloak" in name: 
        pattern = '\s\(*'
        result = re.split(pattern,name)
        name = result[0]+"-"+result[1]
    elif "Size" in name: 
        pattern = '\s\(*'
        result = re.split(pattern,name)
        name = result[0]+"-"+result[1]            
    elif "Castform" in name:
        if "Snowy" in name: name = 'Castform-Snowy'
        elif "Rainy" in name: name = 'Castform-Rainy'
        elif "Sunny" in name: name = 'Castform-Sunny'
        elif "Normal" in name: name = 'Castform'                
    
    if pokemon_html.find("img", class_="shadow"): name = name + '-S'
    
    return name

# Functions to scrape for results for a given period of bouts for the currently active factions. 
def full_scrape(tiers = factions_tiers, regions = factions_regions, url_base = factions_url_base, connection_timeout = 30, interval = 1):
    """
    Fuction to scrape all of the results for all specified factions in given season-cycles, tiers, and regions. 
    Arguments: 
    - tiers: 
        list of strings that correspond to valid Silph tier(s). 
        Must be input as a list, even with 1 element. 
        Default value of ["iron", "copper", "bronze", "silver", "gold", "platinum", 
                            "diamond", "emerald"] 
    - regions: 
        list of strings that correspond to valid Silph region(s). Must be input as a list, 
        even with 1 element. 
        Default value of ["na", "latam", "emea", "apac"]
    - url_base: 
        URL that points to latest Silph Season and Cycle; Format is 
        "https://silph.gg/factions/cycle/season-(season#)-cycle-(cycle#)-"
        Default value of "https://silph.gg/factions/cycle/season-2-cycle-3-"
    - connection_timeout: 
        time in integer amount of seconds to wait for attempting to 
        scrape a specific user before giving up and moving to the next user. 
        Default is 30 seconds. 
    - interval: 
        time in integer amount of seconds to wait after a failed connection before 
        attempting to reconnect to the same user. Default is 1 second. 
    Returns:
    - bout_data: 
        pd.DataFrame of tournament results for the specified factions
    """
    bout_data = pd.DataFrame(columns=results_categories)
    factions_rosters = generate_rosters(tiers, regions, url_base)
    for faction in factions_rosters.keys():
        for member in factions_rosters[faction]:
            start_time = time.time()
            while True: 
                try: 
                    member_scrape = individual_user_scrape(member)
                    break
                except ConnectionError: 
                    if time.time() > start_time + connection_timeout:
                        raise Exception(f"Unable to connect to {member}'s page after {connection_timeout} seconds of ConnectionErrors")
                    else: 
                        print(f"Unable to connect to {member}'s page. Waiting 1 second before attempting again...")
                        time.sleep(1)
            bout_data = pd.concat(objs = [bout_data, member_scrape])
            #print(member, ":", round(time.time()-start_time, 3), "s to process")
    return bout_data



# Initialization during importing    
_setup_cache(faction_cache)
_setup_cache(player_cache)