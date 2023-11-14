#!/usr/bin/env python
# coding: utf-8

# In[1]:


from bs4 import BeautifulSoup, NavigableString, Tag
import pandas as pd
import requests
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import NoSuchElementException
import numpy as np
import glob
import time
import re


# In[2]:


chrome_options = webdriver.ChromeOptions()
# save any files in the current working directory
# prefs = {'download.default_directory' : os.getcwd()}
# chrome_options.add_argument("--headless")
# chrome_options.add_experimental_option('prefs', prefs)
service = ChromeService(executable_path=ChromeDriverManager().install())

driver = webdriver.Chrome(service=service, options=chrome_options)


# In[3]:


def getAllocationCategories(year, driver):

    # Navigate to the memorandums page for the given year
    url = "https://infohub.nyced.org/reports/financial/financial-data-and-reports/school-allocation-memorandums"
    year = str(year)
    driver.get(url)
    link2memorandums = ""
    elements = driver.find_elements(By.CSS_SELECTOR, 'a[target="_blank"]')
    for element in elements:
        if year in element.text:
            link2memorandums = element.get_attribute("href")
            break
    driver.get(link2memorandums)

    # Go to the 	School Allocation Memorandums sorted numerically
    driver.find_element(By.XPATH, "//*[contains(text(), 'SAMs by Numbers')]").click()

    # Make a list of all the links to allocation memorandums and category titles
    url_prefix = link2memorandums.split("am_")[0]
    urls = []
    categories = []
    page = requests.get(driver.current_url)
    soup = BeautifulSoup(page.text, "html.parser")
    table = soup.find("table")

    ran = False

    for row in table:
        try:
            # FSF has multiple entries but we only need the memorandum
            for a in row.find_all("a", href=True):
                if a.text == "Fair Student Funding Memorandum":
                    urls.append(url_prefix + a["href"])
                    categories.append(a.text)
                # After 'Allocation Summary by District' marks the start of memorandum links
                if "Allocation Summary by District" in a.text:
                    ran = True
                    continue
                # If you have passed 'Allocation Summary by District' start to save the category titles and links
                if ran:
                    if a["href"].startswith("http"):
                        urls.append(a["href"])
                    else:
                        urls.append(url_prefix + a["href"])
                    categories.append(a.text)
        except:
            continue

    # Formatting the titles
    for i, category_title in enumerate(categories):
        categories[i] = re.sub("\\r|\\t|\\n", "", category_title)

    # List of dictionaries with allocation titles and galaxy listing
    categories_list = []

    # Add the galaxy listings for every allocation title
    for i, url in enumerate(urls):
        driver.get(url)
        funding_titles = []

        # Find elements with style attritbute and are bold and blue
        elements = driver.find_elements(By.CSS_SELECTOR, "[style]")
        for element in elements:
            if (
                "fontweightbold"
                in (re.sub(r"\W+", "", element.get_attribute("style")).lower())
            ) and (
                "colorblue"
                in (re.sub(r"\W+", "", element.get_attribute("style")).lower())
                or "color0000FF"
                in (re.sub(r"\W+", "", element.get_attribute("style")).lower())
            ):
                funding_titles.append(element.text)

        # Find elements with bold tag that are blue
        elements = driver.find_elements(By.TAG_NAME, "b")
        for parentElement in elements:
            if parentElement.find_elements(By.CSS_SELECTOR, '[color="#0000FF"]'):
                childElements = parentElement.find_elements(
                    By.CSS_SELECTOR, '[color="#0000FF"]'
                )
                for childElement in childElements:
                    funding_titles.append(childElement.text)
            elif parentElement.find_elements(By.CSS_SELECTOR, '[style="color: blue"]'):
                childElements = parentElement.find_elements(
                    By.CSS_SELECTOR, '[style="color: blue"]'
                )
                for childElement in childElements:
                    funding_titles.append(childElement.text)

        # Find elements that are blue (first) and have a child element with the bold tag
        elements = driver.find_elements(By.CSS_SELECTOR, '[color="#0000FF"]')
        for parentElement in elements:
            if parentElement.find_elements(By.TAG_NAME, "b"):
                childElements = parentElement.find_elements(By.TAG_NAME, "b")
                for childElement in childElements:
                    funding_titles.append(childElement.text)

        # Find elements in a table that are blue and bold
        elements = driver.find_elements(By.CSS_SELECTOR, "tbody")
        for element in elements:
            if (
                "fontweightbold"
                in (re.sub(r"\W+", "", element.get_attribute("style")).lower())
            ) and (
                "colorblue"
                in (re.sub(r"\W+", "", element.get_attribute("style")).lower())
                or "color0000FF"
                in (re.sub(r"\W+", "", element.get_attribute("style")).lower())
            ):
                funding_titles.append(element.text)

        # Formatting for galaxy titles
        if "\n" in "".join(funding_titles):
            temp = funding_titles.copy()
            for title in funding_titles:
                if "\n" in title:
                    temp.remove(title)
                    temp = temp + title.split("\n")
                    funding_titles = temp

        # Remove duplicates
        funding_titles = list(set(funding_titles))

        categories_list.append(
            {"Category": categories[i], "Galaxy Titles": funding_titles}
        )

    return categories_list


# In[7]:


allocationCategories2021 = getAllocationCategories(2021, driver)
allocationCategories2021


# In[10]:


allocationCategories2020 = getAllocationCategories(2020, driver)
allocationCategories2020


# In[4]:


allocationCategories2022 = getAllocationCategories(2022, driver)
allocationCategories2022


# In[208]:


district_5_allocations = pd.read_csv(
    r"C:\Users\ebroh\BetaNYC\School Budgets\School-Budget-and-Allocations\data\district 5\allocation_district_5.csv"
)
district_5_allocations


# In[209]:


M125_allocations = district_5_allocations[
    district_5_allocations["location_code"] == "M125"
]
M125_allocations


# In[274]:


M125_2022 = M125_allocations[M125_allocations["fiscal_year"] == 2022]
M125_2022 = M125_2022.drop(columns=("Unnamed: 0"))
M125_allocation_categories = M125_2022["allocation_category"].unique()
all_2022_categories = []
for i in allocationCategories2022:
    all_2022_categories = all_2022_categories + i["Galaxy Titles"]
overlap = [x for x in M125_allocation_categories if x not in all_2022_categories]
overlap


# In[289]:


M125_2021 = M125_allocations[M125_allocations["fiscal_year"] == 2021]
M125_2021 = M125_2021.drop(columns=("Unnamed: 0"))
M125_allocation_categories = M125_2021["allocation_category"].unique()
all_2021_categories = []
for i in allocationCategories2021:
    all_2021_categories = all_2021_categories + i["Galaxy Titles"]
overlap = [x for x in M125_allocation_categories if x not in all_2021_categories]
overlap


# In[288]:


M125_2020 = M125_allocations[M125_allocations["fiscal_year"] == 2020]
M125_2020 = M125_2020.drop(columns=("Unnamed: 0"))
M125_allocation_categories = M125_2020["allocation_category"].unique()
all_2020_categories = []
for i in allocationCategories2020:
    all_2020_categories = all_2020_categories + i["Galaxy Titles"]
overlap = [x for x in M125_allocation_categories if x not in all_2021_categories]
overlap


# In[282]:


district_5_allocations = district_5_allocations.drop(columns="Unnamed: 0")


# In[298]:


district_5_allocations_2022 = district_5_allocations["allocation_category"][
    district_5_allocations["fiscal_year"] == 2022
].unique()
district_5_allocations_2022


# In[11]:


memorandum_lookup = pd.DataFrame()
for memorandum_category in allocationCategories2020:
    for galaxy_title in memorandum_category["Galaxy Titles"]:
        memorandum_lookup = pd.concat(
            [
                memorandum_lookup,
                pd.DataFrame(
                    {
                        "memorandum_category": [memorandum_category["Category"]],
                        "galaxy_title": [galaxy_title],
                    }
                ),
            ],
            ignore_index=True,
        )
memorandum_lookup


# In[ ]:


# district_5_allocations_2022 = district_5_allocations['allocation_category'][district_5_allocations['fiscal_year'] == 2022].unique()
# district_5_allocations_2022 = pd.DataFrame({'galaxy_title': district_5_allocations_2022})
# district_5_allocations_2022['galaxy_title'] = district_5_allocations_2022['galaxy_title'].astype(str)
# memorandum_lookup['galaxy_title'] = memorandum_lookup['galaxy_title'].astype(str)
# district_5_allocations_2022 = district_5_allocations_2022.join(memorandum_lookup, on = 'galaxy_title', how = 'left', lsuffix='_left', rsuffix='_right')
# district_5_allocations_2022


# In[ ]:


# Added pre-commit file test (part 3)


# In[ ]:
