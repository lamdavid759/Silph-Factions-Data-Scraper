#!/usr/bin/env python
# coding: utf-8

# In[254]:


# Imports and URLs 
# DO NOT EDIT THIS PART UNLESS YOU ARE ADDING A TEAM INTO FACTION INFORMATION
import requests
from bs4 import BeautifulSoup
import re
import numpy as np
import csv
import requests

# Faction Information
factionsURLBase = "https://silph.gg/factions/cycle/season-2-cycle-1-"
factionsTiers = ["iron", "copper", "bronze", "silver", "gold", "platinum", "diamond", "emerald"]
factionsRegions = ["latam"] #, "emea", "na", "apac"]

# Example URL
EmeraldNA = "https://silph.gg/factions/cycle/season-2-cycle-1-emerald-na"

factionHomepages = []

# Procedurally generate URLs
for tier in factionsTiers: 
    for region in factionsRegions:
        url = factionsURLBase + tier + "-" + region
        get = requests.get(url)
        if get.status_code == 200: factionHomepages.append(url)


# In[267]:


#Initializes web scrape of factions in a given tier
def factionInfoScrape(URL):
    URLBase = "https://silph.gg"
    factionNames = []
    factionLinkDict = {}
    factionRosterDict = {}
    page = requests.get(URL)
    soup = BeautifulSoup(page.content, "html.parser")
    for faction in soup.find_all("div",class_="nameWrapper"): 
        factionName = faction.find("p").get_text()
        factionLink = URLBase + faction.find("a").get("href")
        factionNames.append(factionName)
        factionLinkDict[factionName] = factionLink
        factionRoster = []
        factionPage = requests.get(factionLinkDict[factionName])
        factionSoup = BeautifulSoup(factionPage.content, "html.parser")
        for player in factionSoup.findAll(True, {"class":["playerName", "playerName long"]}): 
            factionRoster.append(player.get_text().strip())
        factionRosterDict[factionName] = factionRoster
    return factionRosterDict

# Function for scraping individual user data
def individualUserScrape(Username):
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
        # Checks if the URL for the given event is a Faction bout and excludes postseason events
        if result.select("a[href*=faction]") == []: continue
        if "Global Melee" in result.find("div",class_="arenaBadge")["title"]: continue
        if "World Championship" in result.find("div",class_="arenaBadge")["title"]: continue

        fact = result.find("a", class_="logo")["title"] # Faction at time of battle
        
        # Conditional formatting to change cupType into proper form, then into database entry
        cupType = result.find("h5", class_="cupType").text.strip().strip("★").strip()
        if "Great" in cupType: cupType = "Great"
        elif "Ultra" in cupType: cupType = "Ultra"
        elif "Master" in cupType: cupType = "Master"    

        # Checks URL for bout information (season, cycle, tier) and region
        boutLink = result.find("a").get("href")
        region = ""
        if "may-2021-qualifiers" in boutLink:
            pattern = "https://silph.gg/factions/cycle/may-2021-qualifiers-(.*)"
            region = re.findall(pattern,boutLink)[0].upper()
            season = 0
            cycle = 1
            tier = "Qualifiers"
        elif "preseason-cycle-2-qualifiers" in boutLink:
            pattern = "https://silph.gg/factions/cycle/preseason-cycle-2-qualifiers-(.*)"
            region = re.findall(pattern,boutLink)[0].upper()
            season = 0
            cycle = 2
            tier = "Qualifiers"
        elif "season-" in boutLink:
            pattern = "https://silph.gg/factions/cycle/season-(.*)-cycle-(.*)-(.*)-(.*)"
            parsedBoutInfo = re.findall(pattern,boutLink)
            season = parsedBoutInfo[0][0]
            cycle = parsedBoutInfo[0][1]
            tier = parsedBoutInfo[0][2].title()
            region = parsedBoutInfo[0][3].upper()
        
        # Manually fixes some inconsistent data parsing
        if region == "": continue
        if region == "EU": region = "EMEA"

        # Checks title for bout number
        boutInfo = result.find("h5", class_="tourneyName").text.strip()
        pattern = "Bout (.*): (.*)"
        parsedBoutNumber = re.findall(pattern,boutInfo)
        #Check to see if this particular bout was part of a promotion/relegation battle
        if parsedBoutNumber[0][1] == "Promotions/Relegations": boutNumber = 8 
        else: boutNumber = int(parsedBoutNumber[0][0])

        record = result.find(class_="win").find("h3", class_="value").text+'-'+result.find(class_="loss").find("h3", class_="value").text

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
            elif "Size" in monName: 
                pattern = '\s\(*'
                result = re.split(pattern,monName)
                monName = result[0]+"-"+result[1]            
            elif "Castform" in monName:
                if "Snowy" in monName: monName = 'Castform-Snowy'
                elif "Rainy" in monName: monName = 'Castform-Rainy'
                elif "Sunny" in monName: monName = 'Castform-Sunny'
                elif "Normal" in monName: monName = 'Castform'
            if mon.find("img", class_="shadow"): monName = monName + '-S'
            roster.append(monName)
        tournamentResultDataHolder.append([region, tier, fact, Username, cupType, season, cycle, boutNumber, record] + roster)
    return tournamentResultDataHolder


# In[ ]:


# COMPUTATION INTENSIVE: Complete Scrape
# Completely scrape all active factions by determining active rosters and going through all Pokemon teams (even for previous faction membership)
boutData = []
exportedFileName = "Active LATAM Factions Scrape"
for tierLink in factionHomepages:
    factionRosterDict = factionInfoScrape(tierLink)
    for faction in factionRosterDict:
        for member in factionRosterDict[faction]:
            result = individualUserScrape(member)
            for entry in result: boutData.append(entry)
            
with open(exportedFileName+".csv", 'w', encoding="utf-8", newline='') as f:
    write = csv.writer(f)
    write.writerows([["Region", "Tier", "Team", "Player", "Format", "Season", "Cycle", "Bout", "Record", "Team #1", "Team #2", "Team #3", "Team #4", "Team #5", "Team #6"]])        
    write.writerows(boutData)

