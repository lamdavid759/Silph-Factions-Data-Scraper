#!/usr/bin/env python
# coding: utf-8

# In[137]:


# Inputs for Factions Scraping
# Must be case specific and matches with factionDict below
factionTeam = "Evanstonks" # Make sure to check and see if the faction roster is set. Roster is a dict of "Team": [Roster]

# Change for each faction you import (in order of season, cycle)
# Note: depending on how each faction does, they might be in the same tier and as a result, you will need to manually go in and change it. :()
# If you are running a bout scrape, include all possible (1,1) entries like Gold and Diamond
cycleDictionary =  {"North America's First Cycle!": (0,1), "North America's Qualifiers": (0,2), "North America's Gold Cycle": (1,1),
                   "North America's Diamond Cycle": (1,1), "North America's Platinum Cycle":(1,2), "Promotions/Relegations":(1,1)}


# In[138]:


# Imports and URLs 
# DO NOT EDIT THIS PART UNLESS YOU ARE ADDING A TEAM INTO FACTION INFORMATION
import requests
from bs4 import BeautifulSoup
import re
import numpy as np
import csv

# Faction Information. Roster is a dict of "Team": [Roster]. Case sensitive.
factionRoster = {"Team MichiGengar": ['AhmadZR', 'ashsaigh','TrentSzcz','CarissaV123','Red4Novak','TerdFergus0nn','Stodds92','Piscivore','HookedOnOnix19'], 
"Wing Attack": ['bhulbert', 'x3DxJMar159', 'Chellmic07', 'Motiks', 'Chrisdadude', 'Rhyblet', 'WinstontheChamp', 'pheon18', 'x3Dxconno7'], 
"TEAM OMEGALUL": ['FrostyACY','CustomApproach','Monstars50','SaadMunir','MagicMayson','Maxy1000000P','MysticSparkle24','KimleyHorn','Jonathankelly'],
"Icy Wind":['Wallower','MrKnollItAll','KevinSaludares','x3TheGOAT3x','jaysfan55','Dylan9497','DragOns1lk','FreakyBot9','Uberjudgement'],
"Helmet Heroes": ['HoldinMcNuggets','0h0khaha','KakunaMattata42','AlphaFeeb','HangPJs','howardgarwong','recabecaaa','officialTT','Mhndztr'],
"AquaTail HungerForce": ['NNNNino468','CraigJames1','651Ryan','gastonagustin','OGPlayerOne','Leecifer','Bobonya5000','DD420x','YYdsPlusnull'],
"Madison Miltanks": ['NitroBuster','GottaKarchEmAll','Waterbug8','GBikekachu','SeawardObject9','WilliamPeter','GngrGirthQuake','HypnosProjectHQ','Logabibi'],
"Evanstonks": ['dgill5581', 'Warnerg', 'ProfSlade', 'Gundam95', 'leogeo0', 'basherbubbles', 'WindyQ','RandomDreamer','SageShadows']}

PlatinumS1C2 = ["Team MichiGengar","Wing Attack", "TEAM OMEGALUL", "Icy Wind", "Helmet Heroes", "AquaTail HungerForce", "Madison Miltanks", "Evanstonks"]
test = ["Evanstonks"]
# Function for scraping
def individualUserScrape(Username, queriedFaction):
    #Variables and Definitions
    URLBase = "https://sil.ph/"
    URL = URLBase + Username

    #Initializes web scrape
    page = requests.get(URL)
    soup = BeautifulSoup(page.content, "html.parser")
    silphData = soup.find("div",id="networkAndAchievements")
    tournamentResults = silphData.find_all("div",class_="tournament")
    tournamentResultDataHolder = []
    for result in tournamentResults: 
        #Conditional formatting to check if factions bout and if so, sanitizes information for database entry
        boutInfo = result.find("h5", class_="tourneyName").text.strip()
        if not boutInfo.startswith('Bout'): continue

        #Check to see if given result is for the team listed (i.e. is this from a previous faction?)
        if not queriedFaction == result.find("a", class_="logo")["title"]: continue

        #Conditional formatting to change cupType into proper form, then into database entry
        cupType = result.find("h5", class_="cupType").text.strip().strip("★").strip()
        if "Great" in cupType: cupType = "Great"
        elif "Ultra" in cupType: cupType = "Ultra"
        elif "Master" in cupType: cupType = "Master"

        pattern = "Bout (.*): (.*)"
        parsedBoutInfo = re.findall(pattern,boutInfo)
        season = cycleDictionary[parsedBoutInfo[0][1]][0]
        cycle = cycleDictionary[parsedBoutInfo[0][1]][1]
        #Check to see if this particular bout was part of a promotion/relegation battle
        if parsedBoutInfo[0][1] == "Promotions/Relegations": boutNumber = 8 
        else: boutNumber = int(parsedBoutInfo[0][0])

        team = result.find_all(class_="pokemon")
        roster = []
        for mon in team:
            monName = mon["title"]
            #Conditional name edits to massage into proper form
            if monName == 'Armored Mewtwo': monName = 'Mewtwo-Armor'
            elif "Alolan" in monName: monName = monName.replace('Alolan ', '') + '-Alola'
            elif "Galarian" in monName: monName = monName.replace('Galarian ', '') + '-Galar'
            elif "Forme" in monName: 
                pattern = '\s\(*'
                result = re.split(pattern,monName)
                monName = result[0]+"-"+result[1]
            elif "Cloak" in monName: 
                pattern = '\s\(*'
                result = re.split(pattern,monName)
                monName = result[0]+"-"+result[1]
            if mon.find("img", class_="shadow"): monName = monName + '-S'
            roster.append(monName)
        tournamentResultDataHolder.append([queriedFaction, Username, cupType, season, cycle, boutNumber] + roster)
    return tournamentResultDataHolder


# In[135]:


# Run Factions Scraping and Writing (first time)
factionData = []
for member in factionRoster[factionTeam]:
    result = individualUserScrape(member,factionTeam)
    for entry in result: factionData.append(entry)
#Take all data and export to csv (for first time imports)
with open(factionTeam+".csv", 'w', newline='') as f:
    write = csv.writer(f)
    write.writerows([["Team", "Player", "Format", "Season", "Cycle", "Bout", "Team #1", "Team #2", "Team #3", "Team #4", "Team #5", "Team #6"]])
    write.writerows(factionData)


# In[139]:


# Run Factions Scraping for a given bout in a tier
# This will return erroneous results if the faction has been in the same tier -- blame Silph for not distinguishing the different cycles. 
boutData = []
desiredSeasons = range(1,1+1)# Starting season, ending season + 1, e.g. range(1,1+1) will get just season 1
desiredCycles = range(2,2+1) # Starting cycle, ending cycle +1
desiredBouts = range(2,3+1) # Starting bout, ending bout +1
desiredTier = PlatinumS1C2
for faction in desiredTier:
    for member in factionRoster[faction]:
        result = individualUserScrape(member,faction)
        for entry in result:
            if (entry[3] in desiredSeasons and entry[4] in desiredCycles and entry[5] in desiredBouts): boutData.append(entry)
with open("Individual Bout Data"+".csv", 'w', newline='') as f:
    write = csv.writer(f)
    write.writerows([["Team", "Player", "Format", "Season", "Cycle", "Bout", "Team #1", "Team #2", "Team #3", "Team #4", "Team #5", "Team #6"]])        
    write.writerows(boutData)


# In[140]:


with open("Individual Bout Data"+".csv", 'w', newline='') as f:
    write = csv.writer(f)
    write.writerows([["Team", "Player", "Format", "Season", "Cycle", "Bout", "Team #1", "Team #2", "Team #3", "Team #4", "Team #5", "Team #6"]])        
    write.writerows(boutData)


# In[80]:


# Inputs and Code for Individual Scraping

result = individualUserScrape('FragginWagon', 'Canadian Shieldon')
with open('FragginWagon'+".csv", 'w', newline='') as f:
    write = csv.writer(f)
    write.writerows([["Team", "Player", "Format", "Season", "Cycle", "Bout", "Team #1", "Team #2", "Team #3", "Team #4", "Team #5", "Team #6"]])        
    write.writerows(result)

