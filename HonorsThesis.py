import os #To get Slack API key/expand user directory path
import pandas as pd #For most data manipulations
import json #To prepare message for Slack
import requests #To send message to Slack
import subprocess #To run in2csv
import time #To pause after downloading the file
from io import StringIO #To convert a string to a file
from datetime import datetime #To check today's date
from calendar import monthrange #To find last day of month
from selenium import webdriver #To scrape UNLPD's data
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def clean_data(df):
    # Make sure there are no null values for the Case Number, Reported time, Location,
    # Stolen amount and Damaged amount
    assert df['Case #'].count() == len(df) != 0
    assert df['Reported'].count() == len(df) != 0
    assert df['Location'].count() == len(df) != 0
    assert df['Stolen'].count() == len(df) != 0
    assert df['Damaged'].count() == len(df) != 0

    #Replace non-numerical characters and cast data type to float
    df['Stolen'] = df['Stolen'].str.replace(',','')
    df['Stolen'] = df['Stolen'].str.replace('$','')
    df['Stolen'] = df['Stolen'].astype(float)
    df['Damaged'] = df['Damaged'].str.replace(',','')
    df['Damaged'] = df['Damaged'].str.replace('$','')
    df['Damaged'] = df['Damaged'].astype(float)

    #Cast data type to datetime
    df['Reported'] = pd.to_datetime(df['Reported'])

    #Double-check data types
    print(df.dtypes)

    #Create a new column with just the year and month from the Reported column
    df['Month'] = df['Reported'].dt.to_period('M')

    #Set index to Reported column; allows for slicing by month
    df2 = df.set_index(['Reported'])

    return df2

def count_crimes(df, all_years=False):
    #This holds the dictionary for each crime
    months_count = []
    #For each crime present in the dataframe
    for crime in df['Incident Code'].unique():
        print(crime)
        crime_dict = {}
        crime_dict['Crime'] = crime
        #For each month in the dataframe
        for month in df['Month'].unique():
            #Slice the dataframe for one month's data
            month_subset = df[str(month)]
            #Filter the subset for instances of the crime
            crime_subset = month_subset[month_subset['Incident Code'] == crime]
            #If multiple months, save the count with the month
            if all_years:
                crime_dict[str(month)] = len(crime_subset)
            #Otherwise, just save it with "Month"
            else:
                crime_dict['Month'] = len(crime_subset)
        #Append the dictionary to the months_count list
        months_count.append(crime_dict)
    #Convert the list into another dataframe
    months_count_df = pd.DataFrame(months_count)
    #To help with speed, save it to a csv
    if all_years:
        months_count_df.to_csv('month_count.csv', index=False)
    return months_count_df

def calculate_stats(df):
    #Creates a dataframe with the unique crimes
    std_df = df.filter(['Crime'])
    #Adds a column with the mean count for each crime
    std_df['mean'] = df.mean(axis=1)
    #Adds a column with the standard deviation for each crime
    std_df['std'] = df.std(axis=1)
    #Adds a column with a lower threshold
    std_df['lower'] = std_df['mean'] - std_df['std']
    #Adds a column with an upper threshold
    std_df['upper'] = std_df['mean'] + std_df['std']
    #Save the data to a csv
    std_df.to_csv('std.csv', index=False)
    return std_df

def check_last_day():
    #Get today's date
    today = datetime.today()
    #monthrange() returns weekday of first of the month and number of days in month.
    if today.day == monthrange(today.year, today.month)[1]:
        return True
    else:
        return False

def post_to_slack(message):
    #Put the message in a dictionary
    slack_data = {'text': message}
    #Send the message
    response = requests.post(
        #Convert the dictionary to a JSON object
        webhook_url, data=json.dumps(slack_data),
        #These headers help Slack interpret the messgae
        headers={'Content-Type': 'application/json'}
    )
    if response.status_code != 200:
        raise ValueError(
            'Request to slack returned an error {code}, the response is:\n{text}'.format(
                code=response.status_code,
                text=response.text,
            )
        )

def find_outliers(all_years_stats, month_count):
    #This is the list of crimes we decided we were interested in
    flagged_crimes = [
        "LOST OR STOLEN ITEM",
        "FRAUD - CREDIT CARDS/ATM/BANK CARD",
        "LARCENY - FROM MOTOR VEHICLE",
        "NARCOTICS - POSSESSION",
        "BURGLARY",
        "LARCENY - FROM BUILDING",
        "ALCOHOL - DWI",
        "ALCOHOL - DRUNK",
        "ALCOHOL - MINOR IN POSSESSION",
        "VANDALISM - OTHER",
        "LARCENY - STOLEN BIKE",
        "VANDALISM - BY GRAFFITI",
        "NARCOTICS - OTHER",
        "NARCOTICS - SALE/DELIVER",
    ]
    #These two templates are used for the messages.
    plural_msg = "This month, there have been {month_total} {crime} incidents reported. There are normally {mean} incidents reported in a month, and one standard deviation {direction} is {bound}."
    sing_msg = "This month, there has been {month_total} {crime} incident reported. There are normally {mean} incidents reported in a month, and one standard deviation {direction} is {bound}."

    #If it's the last day, merge the data and keep everything
    #Then, check the low thresholds
    if check_last_day():
        merged = pd.merge(all_years_stats, month_count, on='Crime', how='outer')
        for index, row in merged.iterrows():
            if row['lower'] > row['Month'] and row['Crime'] in flagged_crimes:
                #If it has happened more than once, use plural words
                if row['Month'] != 1:
                    message = plural_msg.format(
                        crime=row['Crime'],
                        bound=round(row['lower'], 2),
                        month_total=row['Month'],
                        mean=round(row['mean'], 2),
                        direction='below',
                    )
                #Otherwise, use singular words
                else:
                    message = sing_msg.format(
                       crime=row['Crime'],
                       bound=round(row['lower'], 2),
                       month_total=row['Month'],
                       mean=round(row['mean'], 2),
                       direction='below',
                    )
                #Print the message here
                print(message)
                #Post the message to Slack
                post_to_slack(message)
    #Otherwise, only keep the data for crimes that have happened this month
    else:
        merged = pd.merge(all_years_stats, month_count, on='Crime', how='inner')
    #For each row, check if the count has crossed the upper bound
    for index, row in merged.iterrows():
        if row['upper'] < row['Month'] and row['Crime'] in flagged_crimes:
            #If it has happened more than once, use plural words
            if row['Month'] != 1:
                plural_msg.format(
                    crime=row['Crime'],
                    bound=round(row['upper'], 2),
                    month_total=row['Month'],
                    mean=round(row['mean'], 2),
                    direction='above',
                )
            #Otherwise, use singular words
            else:
                message = sing_msg.format(
                    crime=row['Crime'],
                    bound=round(row['upper'], 2),
                    month_total=row['Month'],
                    mean=round(row['mean'], 2),
                    direction='above',
                )
            #Print the message here
            print(message)
            #Post the message to Slack
            post_to_slack(message)

#Read in the csv file
all_years = pd.read_csv('all_years.csv')
#Clean the data
all_years_clean = clean_data(all_years)
#Count the crime occurences
all_years_count = count_crimes(all_years_clean, all_years=True)
#Calculate the thresholds
all_years_stats = calculate_stats(all_years_count)

#This is needed to set up selenium
#os.path.expanduser allows the use of a '~'
path_to_chromedriver = os.path.expanduser('~/Downloads/chromedriver')
browser = webdriver.Chrome(executable_path=path_to_chromedriver)
#The URL to the Daily Crime and Fire Log
url = "https://scsapps.unl.edu/policereports/MainPage.aspx"
#Go to the URL
browser.get(url)
#Find the advanced search button and click it
browser.find_element_by_id('ctl00_ContentPlaceHolder1_AdvancedSearchButton').click()
#Find the first date field, hit tab and hit '01'.
#This sets the date to the first day of the month
date_box = browser.find_element_by_id('ctl00_ContentPlaceHolder1_DateRange_MonthText1')
date_box.send_keys('\t01')
#Find the search button and click it
browser.find_element_by_id('ctl00_ContentPlaceHolder1_SearchButton').click()
#Switch to the iframe on the page
browser.switch_to.frame(browser.find_element_by_id('ctl00_ContentPlaceHolder1_ViewPort'))
#Find the export button once the iframe loads and click it
export_button = WebDriverWait(browser, 10).until(
    EC.presence_of_element_located((By.ID,'ExportButton'))
)
export_button.click()

#Wait for the file to download
time.sleep(5)

#Runs in2csv on the downloaded file and converts it to UTF-8
csv_data = subprocess.check_output([
    "in2csv",
    os.path.expanduser("~/Downloads/DailyCrimeLogSummary.xls"),
],stderr=subprocess.DEVNULL,).decode("utf-8")
#Creates a file instance for pandas to use on the next line
csv_file_instance = StringIO(csv_data)
#Reads in the csv to a dataframe, skipping the first eight rows
month_df = pd.read_csv(csv_file_instance, skiprows=8)

#Clean the data
month_clean = clean_data(month_df)
#Count the crime occurences
month_count = count_crimes(month_clean)

webhook_url = os.environ.get('SLACK_URL')

find_outliers(all_years_stats, month_count)
