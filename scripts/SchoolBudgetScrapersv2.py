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


# In[11]:


chrome_options = webdriver.ChromeOptions()
prefs = {"download.default_directory": os.getcwd()}
# chrome_options.add_argument("--headless")
chrome_options.add_experimental_option("prefs", prefs)
driver = webdriver.Chrome(
    ChromeDriverManager().install(), chrome_options=chrome_options
)
service = ChromeService(executable_path=ChromeDriverManager().install())


# In[3]:


def openBudgetSite(driver, school_code, fiscal_year, budgetOrAllocation="budget"):
    if budgetOrAllocation == "allocation":
        driver.get(
            "https://www.nycenet.edu/offices/d_chanc_oper/budget/dbor/galaxy/galaxyallocation/default.aspx"
        )

    elif budgetOrAllocation == "budget":
        driver.get(
            "https://www.nycenet.edu/offices/d_chanc_oper/budget/dbor/galaxy/galaxybudgetsummaryto/default.aspx"
        )

    else:
        raise ValueError(
            'Budget or Allocation value must be either "budget" or "allocation"'
        )

    # get element
    element = driver.find_element(By.XPATH, '//*[@id="School_Code"]')

    # send keys
    element.send_keys(school_code)

    x = driver.find_element(By.XPATH, '//*[@id="Fiscal_Year"]')
    drop = Select(x)

    # select by visible text
    drop.select_by_visible_text(fiscal_year)

    driver.find_element(By.XPATH, '//*[@id="Enter"]').click()

    try:
        element = driver.find_element(By.XPATH, '//*[@id="message"]/div[1]/div[3]/h2/a')
        element.text.index(school_code)
        return True

    except NoSuchElementException:
        print(
            "No "
            + budgetOrAllocation
            + " data could be found for school code "
            + school_code
            + " in the year "
            + year
        )
        return False

    except ValueError:
        print("Given School code and school code for retrieved data do not match")
        return False


def allocationPageScraper(driver, school_code, fiscal_year):
    list_of_dfs = pd.read_html(driver.page_source)
    final_df = pd.DataFrame(
        columns=["location_code", "fiscal_year", "allocation_category", "amount"]
    )

    for df in list_of_dfs:
        df = df.rename(
            columns={df.columns[0]: "allocation_category", df.columns[1]: "amount"}
        )
        df = df[df["allocation_category"].str.contains("total", case=False) == False]
        df["location_code"] = school_code
        df["fiscal_year"] = fiscal_year
        final_df = pd.concat([final_df, df])

    return final_df


def budgetPageScraper(driver, school_code, fiscal_year):
    section_titles = driver.find_elements(By.CLASS_NAME, "TO_Section")
    list_of_dfs = pd.read_html(driver.page_source)

    final_df = pd.DataFrame(
        columns=[
            "location_code",
            "fiscal_year",
            "budget_category",
            "budget_assignment",
            "num_positions",
            "service_type",
            "amount",
        ]
    )

    for i, df in enumerate(list_of_dfs):
        if len(df.columns) == 2:
            df = df.rename(
                columns={df.columns[0]: "budget_assignment", df.columns[1]: "amount"}
            )
            df = df[df["budget_assignment"].str.contains("total", case=False) == False]
            df["location_code"] = school_code
            df["fiscal_year"] = fiscal_year
            df["budget_category"] = section_titles[i].text
            df["num_positions"] = None
            df["service_type"] = None
            final_df = pd.concat([final_df, df])

        elif len(df.columns) == 3:
            df = df.rename(
                columns={
                    df.columns[0]: "budget_assignment",
                    df.columns[1]: "num_positions",
                    df.columns[2]: "amount",
                }
            )
            df = df[df["budget_assignment"].str.contains("total", case=False) == False]
            df["location_code"] = school_code
            df["fiscal_year"] = fiscal_year
            df["budget_category"] = section_titles[i].text
            df["service_type"] = None
            final_df = pd.concat([final_df, df])

        elif len(df.columns) == 4:
            df = df.rename(
                columns={
                    df.columns[0]: "budget_assignment",
                    df.columns[1]: "service_type",
                    df.columns[2]: "num_positions",
                    df.columns[3]: "amount",
                }
            )
            df = df[df["budget_assignment"].str.contains("total", case=False) == False]
            df = df[df["service_type"].str.contains("total", case=False) == False]
            df["location_code"] = school_code
            df["fiscal_year"] = fiscal_year
            df["budget_category"] = section_titles[i].text
            final_df = pd.concat([final_df, df])

    return final_df


# In[4]:


if openBudgetSite(driver, "M125", "2022", "budget"):
    df = budgetPageScraper(driver, "M125", "2022")


# In[5]:


df


# In[6]:


school_data = pd.read_csv(
    r"C:\Users\ebroh\Downloads\2019_-_2020_School_Locations (2).csv"
)


# In[7]:


school_data["location_code"].unique()


# In[13]:


budget_data = pd.DataFrame()
allocation_data = pd.DataFrame()
years = ["2018", "2019", "2020", "2021", "2022"]

for school in school_data["location_code"].unique():
    print(school)
    for year in years:
        if openBudgetSite(driver, school, year, "budget"):
            print(year + " Budget Data Opened")
            budget_data = pd.concat(
                [budgetPageScraper(driver, school, year), budget_data]
            )
        if openBudgetSite(driver, school, year, "allocation"):
            print(year + " Allocation Data Opened")
            allocation_data = pd.concat(
                [allocationPageScraper(driver, school, year), allocation_data]
            )


# In[14]:


budget_data


# In[15]:


allocation_data


# In[ ]:
