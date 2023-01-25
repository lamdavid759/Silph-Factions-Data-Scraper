# Page requests and web scraping
import requests
from bs4 import BeautifulSoup, SoupStrainer
import re
import csv
import time
from requests.exceptions import ConnectionError

# Writing results
import pandas as pd 

# Caching
import os
import shutil
from ediblepickle import checkpoint
from urllib.parse import quote

# Global variables to manage the caching directories of the script. 
player_cache = "__player_cache__" 
faction_cache = "__faction_cache__"

# Faction Information
factions_url_base = "https://silph.gg/factions/cycle/season-2-cycle-3-" # Only thing that should be changed from cycle to cycle. 
factions_tiers = ["Iron", "Copper", "Bronze", "Silver", "Gold", "Platinum", "Diamond", "Emerald"]
factions_regions = ["NA", "LATAM", "EMEA", "APAC"]
results_categories = ["region", "tier", "faction", "player", "format", "season", "cycle", "bout", "record", "mon1", "mon2", "mon3", "mon4", "mon5", "mon6"]

# Setting up caching directories for checkpoint. 
def _setup_cache(path, overwrite = False): 
    """
    Helper function to set-up a cache directory for the setpoint. 
    Arguments: 
    - cache_dir: 
        path string for cache directory. Can be absolute or relative.
    - overwrite: 
        bool for whether to delete the current path. Default is set to False
    """
    if overwrite and os.path.exists(path): 
        shutil.rmtree(path, ignore_errors=True)
    if not os.path.exists(path):
        os.mkdir(path)

# Set of functions that generate rosters for arbitrary tier and region.        
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

# Set of functions that operate on an individual user's Silph Card to scrape all valid Faction bouts. 
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
    
    # If roster is for some reason empty, pad it with "N/A" until it is an array of 6 Pokemon
    while len(roster) < 6: 
        roster.append("N/A")
    
    return [region, tier, faction, username, cup_type, int(season), int(cycle), int(bout_number), record] + roster

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
    factions_strainer = SoupStrainer("div", attrs={"class": "display bouts"})
    soup = BeautifulSoup(markup=page.content, features="html.parser", parse_only=factions_strainer)
    tournament_results = soup.find_all("div",class_="tournament")
    for result in tournament_results: 
        parsed_result = tournament_result_parse(result, username)
        if parsed_result: 
            all_results.append(parsed_result)
    return pd.DataFrame(all_results, columns=results_categories)

# Main function to scrape results for all valid tiers and regions. 
def full_scrape(tiers = factions_tiers, regions = factions_regions, url_base = factions_url_base, clear_player_cache = False, connection_timeout = 60, interval = 1):
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
        Default is 60 seconds. 
    - interval: 
        time in integer amount of seconds to wait after a failed connection before 
        attempting to reconnect to the same user. Default is 1 second. 
    Returns:
    - bout_data: 
        pd.DataFrame of tournament results for the specified factions
    """
    _setup_cache(faction_cache)
    _setup_cache(player_cache, clear_player_cache)
    
    bout_data = pd.DataFrame(columns=results_categories)
    factions_rosters = generate_rosters(tiers, regions, url_base)
    start_time = time.time()
    for ind, faction in enumerate(factions_rosters.keys()):
        for member in factions_rosters[faction]:
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
            #print(f"{member}: {round(time.time()-start_time, 3)} s to process {len(member_scrape)} entries.")
        if (ind+1) % 10 == 0: 
            print(f"{ind+1}/{len(factions_rosters)} factions completed. Total elapsed time: {round((time.time() - start_time)/60, 2)} min.")
    return bout_data

# Set of additional functions to further filter the full scrape in a programmatic fashion. 
def enumerate_bouts(bout_start, bout_end = None):
    """
    Helper function to convert desired bouts into a suitable dictionary format for filtered_results()
    Arguments: 
    - bout_start: 
        Starting bout for scrape in (season, cycle, bout) format. Must be a valid bout. 
    - bout_end: 
        (Optional) ending bout for scrape in (season, cycle, bout) format. If no value is specified, defaults to enumerating all bouts after the starting bout. 
    Returns: 
    - filter_list: 
        A list of dictionaries of the form {filter: value} that is properly formatted. Each dictionary corresponds to a specific bout.  
    """
    # Tuples of valid bouts in (season, cycle, bout) format
    valid_bouts = ([(0, 1, i) for i in range(1, 5+1)] 
                   + [(0, 2, i) for i in range(1, 5+1)] 
                   + [(1, 1, i) for i in range(1, 8+1)] 
                   + [(1, 2, i) for i in range(1, 8+1)] 
                   + [(1, 3, i) for i in range(1, 7+1)]
                   + [(2, 1, i) for i in range(1, 9+1)]
                   + [(2, 2, i) for i in range(1, 9+1)]
                   + [(2, 3, i) for i in range(1, 9+1)])
    try: 
        start = valid_bouts.index(bout_start)
    except ValueError as e:
        print(f"{e}. Please enter a valid starting bout.")
    
    try: 
        if bout_end: 
            end = valid_bouts.index(bout_end)+1
        else: 
            end = None
    except ValueError as e:
        print(f"{e}. Please enter a valid ending bout.")
        
    filter_list = []
    for season, cycle, bout in valid_bouts[start:end]: 
        bout_dict = {}
        bout_dict["season"] = season
        bout_dict["cycle"] = cycle
        bout_dict["bout"] = bout
        filter_list.append(bout_dict)
    return filter_list

def add_filter(filter_list, filter_on, values): 
    """
    Arguments: 
    - filter_list: a list of dictionaries with filters that will be augmented by an additional filter. Dictionaries are in {filter: value}
    - filter_on: str of desired filter, provided in lowercase. The filter must correspond to the columns of a pd.DataFrame scrape, enumerated in results_categories: 
        ["region", "tier", "faction", "player", "format", "season", "cycle", "bout", "record", "mon1", "mon2", "mon3", "mon4", "mon5", "mon6"]
    - values: a str or list of strs of desired values to filter on corresponding to filter_on.
        A secondary check is done on the values if the filter_on is "region" or "tier". This check is done by setting proper. 
        No secondary check exists on the 
    
    Returns: 
    - modified_filtered_list: A modified list of dictionaries that contain the same filters as the input filter_list with the additional filter added on each dictionary. If 
        values is a single str, the length of modified_filtered_list will be the same as filter list, otherwise it will be n*len(filter_list), where n is the number of entries
        provided in values. 
    """
    # Handling argument formatting and checking for valid filters. 
    filter_on = str.lower(filter_on)
    if filter_on not in results_categories:
        raise Exception("""The desired filter is not a valid option in the available filters 
            ['region', 'tier', 'faction', 'player', 'format', 'season', 'cycle', 'bout', 'record', 'mon1', 'mon2', 'mon3', 'mon4', 'mon5', 'mon6']. 
            Please correct your filter name or change the desired filter.""")  
    if not isinstance(values, list): 
        values = [values]
    
    diff = None
    if filter_on == "region":
        values = [string.upper() for string in values]
        diff = set(values)-set(factions_regions)
    if filter_on == "tier":
        values = [string.title() for string in values]
        diff = set(values)-set(factions_tiers)   
    if diff: 
        raise Exception(f"Some values were improperly entered. Please check the values {diff} and correct your input.")
    
    # If the arguments pass all checks, continue onward to generate the modified_filtered_list. 
    return [{**filter_dict, **{filter_on: value}} for value in values for filter_dict in filter_list]

def filtered_results(results,save=False,**kwargs):
    """
    Filters results for more fine-grained data. 
    Arguments: 
    - results: 
        a pd.DataFrame obtained by running full_scrape() with the following columns: 
        [region: str, tier: str, faction: str, username: str, cup_type: str, season: 
         int, cycle: int, bout: int, record: str, mon1: str, mon2: str, mon3: str, 
         mon4: str, mon5: str, mon6: str]
    - kwargs: 
        Filter criteria. Currently acceptable criteria are enumerated in results_categories: 
        ["region", "tier", "faction", "player", "format", "season", "cycle", "bout", "record", "mon1", "mon2", "mon3", "mon4", "mon5", "mon6"]
        Accepts either manually entered in filters in keyword = value format or takes a dictionary of filters generated from enumerate_bouts() and add_filter() functions by
        passing **dict. 
    Returns: 
    - filtered_results:
        a pd.DataFrame with the same columns as the results DataFrame after applying the relevant filters 
    """
    filtered_result = results
    for key, value in kwargs.items():
        filtered_result = filtered_result[filtered_result[key] == value].copy()
    filtered_result.sort_values(["season", "cycle", "bout"], ascending=False)    
    
    if save: 
        filtered_result.to_csv(save)
    return filtered_result

def subset_results(results, filter_list, save=False):
    """
    Wrapper function to collect the DataFrames of multiple filter conditions. 
    Arguments: 
    - results: 
        a pd.DataFrame obtained by running full_scrape() with the following columns: 
        [region: str, tier: str, faction: str, username: str, cup_type: str, season: 
         int, cycle: int, bout: int, record: str, mon1: str, mon2: str, mon3: str, 
         mon4: str, mon5: str, mon6: str]
    - filter_list: list of dictionaries with filters in {filter: value} format. Each filter has exactly 1 value. 
    - (optional) save: Default to False. If a csv file is desired, set save = name of file in str form, e.g., "S2_C3_B1.csv"
    
    Output: 
    - subset: 
         a pd.DataFrame obtained by concatenating each DataFrame for a given filter query with the following columns: 
        [region: str, tier: str, faction: str, username: str, cup_type: str, season: 
         int, cycle: int, bout: int, record: str, mon1: str, mon2: str, mon3: str, 
         mon4: str, mon5: str, mon6: str]
    """
    subset = pd.DataFrame(columns=results.columns)
    for filters in filter_list: 
        subset = pd.concat([subset, filtered_results(results, **filters)])
    subset.sort_values(["season", "cycle", "bout"], ascending=False)
    
    if save: 
        subset.to_csv(save)
    return subset

_setup_cache("__player_cache__")
_setup_cache("__faction_cache__")