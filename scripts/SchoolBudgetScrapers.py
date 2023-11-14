#!/usr/bin/env python
# coding: utf-8

# In[3]:


# install packages
get_ipython().system(
    "pip install beautifulsoup4 selenium webdriver-manager pandas requests"
)


# In[2]:


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


# In[43]:


chrome_options = webdriver.ChromeOptions()
# save any files in the current working directory
prefs = {"download.default_directory": os.getcwd()}
chrome_options.add_argument("--headless")
chrome_options.add_experimental_option("prefs", prefs)
service = ChromeService(executable_path=ChromeDriverManager().install())


# In[38]:


BUDGET_TYPES = {
    "budget": {
        "url": "https://www.nycenet.edu/offices/d_chanc_oper/budget/dbor/galaxy/galaxybudgetsummaryto/default.aspx"
    },
    "allocation": {
        "url": "https://www.nycenet.edu/offices/d_chanc_oper/budget/dbor/galaxy/galaxyallocation/default.aspx"
    },
}


def openBudgetSite(driver, school_code, fiscal_year, budgetType):
    # go to url
    url = BUDGET_TYPES.get(budgetType, {}).get("url")
    if not url:
        raise ValueError(f"budgetType value must be either {BUDGET_TYPES.keys()}")
    driver.get(url)

    # type school code
    element = driver.find_element(By.XPATH, '//*[@id="School_Code"]')
    element.send_keys(school_code)

    # select fiscal year in drop down
    x = driver.find_element(By.XPATH, '//*[@id="Fiscal_Year"]')
    drop = Select(x)
    drop.select_by_visible_text(fiscal_year)

    # submit
    driver.find_element(By.XPATH, '//*[@id="Enter"]').click()

    try:
        element = driver.find_element(By.XPATH, '//*[@id="message"]/div[1]/div[3]/h2/a')
        element.text.index(school_code)
        return True

    except NoSuchElementException:
        print(
            "No "
            + budgetType
            + " data could be found for school code "
            + school_code
            + " in the year "
            + fiscal_year
        )
        return False

    except ValueError:
        print("Given School code and school code for retrieved data do not match")
        return False


# In[58]:


def allocationPageScraper(driver, school_code, fiscal_year):
    # final_df = pd.DataFrame()
    list_of_dfs = pd.read_html(driver.page_source)
    df = pd.concat(list_of_dfs, ignore_index=True)

    # rename columns
    df.columns = ["allocation_category", "amount"]

    # remove rows with total
    # df = df[df["allocation_category"].str.contains("total", case = False)==False]
    df = df[~df["allocation_category"].astype(str).str.contains("Grand Total")]

    # add id columns
    df["location_code"] = school_code
    df["fiscal_year"] = fiscal_year
    return df


# In[1]:


def budgetPageScraper(driver, school_code, fiscal_year):
    section_titles = driver.find_elements(By.CLASS_NAME, "TO_Section")
    list_of_dfs = pd.read_html(driver.page_source)
    final_df = pd.DataFrame()

    COLUMN_OPITONS = {
        2: ["budget_assignment", "amount"],
        3: ["budget_assignment", "num_positions", "amount"],
        4: ["budget_assignment", "service_type", "num_positions", "amount"],
    }

    for i, df in enumerate(list_of_dfs):
        # rename columns
        new_columns = COLUMN_OPITONS[len(df.columns)]
        df.columns = new_columns

        # add budget_category context (otps, per session , per diem, etc)
        df["budget_category"] = section_titles[i].text

        # todo: drop total
        df = df[
            ~df["budget_assignment"]
            .astype(str)
            .str.contains(section_titles[i].text + " Total")
        ]

        final_df = pd.concat([final_df, df], ignore_index=True)

    # remove rows with total
    final_df = final_df[
        ~final_df["budget_assignment"].astype(str).str.contains("Grand Total")
    ]
    final_df = final_df[~final_df["service_type"].astype(str).str.contains("Sub-Total")]

    # add id columns
    final_df["location_code"] = school_code
    final_df["fiscal_year"] = fiscal_year

    return final_df


# In[60]:


school_code = "K191"
fiscal_year = "2022"
driver = webdriver.Chrome(service=service, options=chrome_options)


# In[61]:


if openBudgetSite(driver, school_code, fiscal_year, "allocation"):
    df = allocationPageScraper(driver, school_code, fiscal_year)


# In[42]:


if openBudgetSite(driver, school_code, fiscal_year, "budget"):
    df = budgetPageScraper(driver, school_code, fiscal_year)


# In[3]:


school_data = pd.read_csv(
    "https://data.cityofnewyork.us/api/views/wg9x-4ke6/rows.csv?accessType=DOWNLOAD"
)
demographic_data = pd.read_csv(
    "https://data.cityofnewyork.us/api/views/c7ru-d68s/rows.csv?accessType=DOWNLOAD"
)


# In[9]:


district_5_school_data = school_data[school_data["Administrative_District_Code"] == 5]
district_5_demographic_data = demographic_data[
    demographic_data["DBN"].isin(district_5_school_data["system_code"])
]


# In[13]:


district_5_school_data.to_csv("district_5_school_data.csv")
district_5_demographic_data.to_csv("district_5_demographic_data.csv")


# In[12]:


district_5_demographic_data


# In[51]:


budget_data_district_5 = pd.DataFrame()
allocation_data_district_5 = pd.DataFrame()
years = ["2018", "2019", "2020", "2021", "2022"]

district_5_school_codes = school_data[school_data["Administrative_District_Code"] == 5][
    "location_code"
].unique()

for school in district_5_school_codes:
    print(school)
    for year in years:
        if openBudgetSite(driver, school, year, "budget"):
            print(year + " Budget Data Opened")
            budget_data_district_5 = pd.concat(
                [budgetPageScraper(driver, school, year), budget_data_district_5],
                ignore_index=True,
            )
        if openBudgetSite(driver, school, year, "allocation"):
            print(year + " Allocation Data Opened")
            allocation_data_district_5 = pd.concat(
                [
                    allocationPageScraper(driver, school, year),
                    allocation_data_district_5,
                ],
                ignore_index=True,
            )


# In[63]:


budget_data_district_17 = pd.DataFrame()
allocation_data_district_17 = pd.DataFrame()
years = ["2018", "2019", "2020", "2021", "2022"]

district_17_school_codes = school_data[
    school_data["Administrative_District_Code"] == 17
]["location_code"].unique()

for school in district_17_school_codes:
    print(school)
    for year in years:
        if openBudgetSite(driver, school, year, "budget"):
            print(year + " Budget Data Opened")
            budget_data_district_17 = pd.concat(
                [budgetPageScraper(driver, school, year), budget_data_district_17],
                ignore_index=True,
            )
        if openBudgetSite(driver, school, year, "allocation"):
            print(year + " Allocation Data Opened")
            allocation_data_district_17 = pd.concat(
                [
                    allocationPageScraper(driver, school, year),
                    allocation_data_district_17,
                ],
                ignore_index=True,
            )


# In[66]:


budget_data_district_26 = pd.DataFrame()
allocation_data_district_26 = pd.DataFrame()
years = ["2018", "2019", "2020", "2021", "2022"]

district_26_school_codes = school_data[
    school_data["Administrative_District_Code"] == 26
]["location_code"].unique()

for school in district_26_school_codes:
    print(school)
    for year in years:
        if openBudgetSite(driver, school, year, "budget"):
            print(year + " Budget Data Opened")
            budget_data_district_26 = pd.concat(
                [budgetPageScraper(driver, school, year), budget_data_district_26],
                ignore_index=True,
            )
        if openBudgetSite(driver, school, year, "allocation"):
            print(year + " Allocation Data Opened")
            allocation_data_district_26 = pd.concat(
                [
                    allocationPageScraper(driver, school, year),
                    allocation_data_district_26,
                ],
                ignore_index=True,
            )


# In[65]:


budget_data_district_5.to_csv("budget_district_5.csv")
allocation_data_district_5.to_csv("allocation_district_5.csv")
budget_data_district_17.to_csv("budget_district_17.csv")
allocation_data_district_17.to_csv("allocation_district_17.csv")
budget_data_district_26.to_csv("budget_district_26.csv")
allocation_data_district_26.to_csv("allocation_district_26.csv")


# In[14]:


budget_data_district_5 = pd.read_csv(
    r"C:\Users\ebroh\BetaNYC\School Budgets\School-Budget-and-Allocations\data\district 5\budget_district_5.csv"
)


# In[15]:


budget_data_district_5.columns


# In[20]:


budget_data_district_5["budget_category"].unique()


# In[ ]:
