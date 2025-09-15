"""
File name: data_extract
Description: extract data from PDF using available python packages
Approach: filtering QA data is rule based, can expect changes in future versions due to partial format changes in audit reports.
"""

import camelot
import pdfplumber
import pandas as pd

from app.components.generate_tables.scripts import settings as ss

def extract_data(file_path):
    """extract data from PDF in the form of tables and text.

    Args:
        file_path (String): input file path

    Returns:
        dealer_high_level (DataFrame): first page table data
        dealer_detailed (DataFrame): complete data in report
    """
    try:
        table = camelot.read_pdf(file_path,flavor='stream')
        # gets the first table in the first page of audit report
        dealer_high_level = table[0].df
        
        #get the 3rd page table
        table_ = camelot.read_pdf(file_path,pages="3",flavor='stream')
        digital_table = table_[0].df

        #gets the 3rd page text in the report (digital)
        text_ = ""
        with pdfplumber.open(file_path) as pdf:
            page = pdf.pages[2]
            text_ = page.extract_text()
        digital_data = (lambda x: pd.Series(pd.to_numeric(x[1:], errors='ignore'), name=x[0]))(text_.split('\n')).to_frame() 
        digital_data.columns = ['Detailed Report']
        

        #Get the entire text as a string
        text = ""
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                text += "\n" +  page.extract_text() 
        
        # text in split based on new line and filled into a panda series
        dealer_detailed = (lambda x: pd.Series(pd.to_numeric(x[1:], errors='ignore'), name=x[0]))(text.split('\n')).to_frame()  
        dealer_detailed.columns = ['Detailed Report']

        return dealer_high_level, dealer_detailed, digital_data, digital_table
    
    except Exception as exception:
        print(exception)



def filter_answers_data(dealer_detailed, activity_list = ss.ACTIVITIES):
    """
    Filters out QA data in the report.

    Args:
        dealer_detailed (DataFrame): complete data in report

    Returns:
        answer_data (DataFrame): qa data in report
    """
    try:
        above_line = "1 - The Dacia facade and dedicated entrance comply with the brand’s visual identity charter" # question 1 in dacia
        # above_line = "10 - The dealership exterior is in impeccable condition, is clean and is well maintained" # question 1 in renault
        below_line = "zoom" # zoom occurs twice in the data, 2nd zoom is the endpoint of question answers.
        
        digital_line = "201 - The dealer is correctly represented by Google via his GMB profile" # question 1 in digital
        # digital_line = "201 - The dealer is correctly represented by Google via his GPB (GMB) profile" # question 1 in digital-v2
        digital_index = dealer_detailed.loc[dealer_detailed['Detailed Report'].str.contains(digital_line,regex=False)].index[0]

        above_index = dealer_detailed.loc[dealer_detailed['Detailed Report'].str.contains(above_line)].index[0]
        below_index = dealer_detailed.loc[dealer_detailed['Detailed Report'].str.lower().str.contains(below_line)].index[1]

        digital_data = dealer_detailed.iloc[digital_index:, :].reset_index(drop=True)

        answer_data_ = dealer_detailed.iloc[above_index:below_index,:].reset_index(drop=True)
        answer_data = pd.concat([answer_data_, digital_data], ignore_index=True)

        # the data contains simple numbers and % activity. This is also removed
        answer_data = answer_data.loc[~answer_data['Detailed Report'].str.isnumeric()].reset_index(drop=True)
        answer_data = answer_data.loc[~answer_data['Detailed Report'].str.lstrip('0123456789 ').isin(activity_list)].reset_index(drop=True)

        return answer_data
    except Exception as exception:
        print(exception)


