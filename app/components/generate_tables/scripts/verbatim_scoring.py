"""
File name: verbatim_scoring
Description: Generate Additional outputs for the client.
1. Dealer scoring excel - get statuses and create score for all dealerships. Also calculates average score for each question.
                        (A specific format data required)
2. Verbatim - filters out data is not NA/NE and that has only pre-comments.
"""
import pandas as pd

from app.components.generate_tables.scripts import file_handling as fh
from app.components.generate_tables.scripts import settings as ss

def get_country(address,country_mapper = ss.COUNTRY_MAPPER):
    """
     get the country name from the address in the report.

    Args:
        address (String): Address in report.
        country_mapper (Dict, optional):dictionary of countries. Defaults to ss.COUNTRY_MAPPER.

    Returns:
        (String): Country name
    """
    try:
        countries = country_mapper.keys()
        for country in countries:
            if country.lower() in address.lower():
                return country_mapper[country]
    except Exception as exception:
        print(exception)   

def calculate_percentage(average_value):
    """
    Convert average to percentage

    Args:
        average_value (int): calculated average

    Returns:
        percentage_value(String): average represented in percentage
    """
    percentage_value = str(round(average_value * 100,2)) + str('%')
    return percentage_value


# def get_dealer_scoring(dealer_stats, dealer_qa):
    """
    Generates dealer scoring in specified format.

    Args:
        dealer_stats (DataFrame): dealer_statistics
        dealer_qa (DataFrame): dealer question and answer data

    Returns:
        dealer_scoring (DataFrame): dealer scoring as in specified format
    """
    
    try:
        
        # select only the required data for dealer scoring
        required_statistics = ['name1', 'address_full','audit_date','Global_Score', 'new_vehicle_activity', 'aftersales_activity','digital_score','digital_renault','digital_dacia','dealer_code']
        # required_statistics = ['name1', 'address_full','audit_date','Global_Score', 'new_vehicle_activity', 'aftersales_activity','digital_score','digital_renault','dealer_code']
        required_dealer_stats = dealer_stats.loc[dealer_stats['statistic'].isin(required_statistics),]
        pivot_dealer_stats = required_dealer_stats.pivot(index='statistic', columns='filename', values='value')
        pivot_dealer_stats = pivot_dealer_stats.reindex(required_statistics) # re-arranges the order in the required format
        pivot_dealer_stats.loc['address_full'] = pivot_dealer_stats.loc['address_full'].apply(get_country)
        
        # pivot_dealer_stats = pivot_dealer_stats[pivot_dealer_stats.loc['address_full'] == country]    
        
        # Extract the country information from the 'address_full' row
        # country_series = pivot_dealer_stats.loc['address_full'].apply(get_country)

        # Filter the DataFrame based on the extracted country
        # pivot_dealer_stats = pivot_dealer_stats.loc[:, country_series == country]

        # pivot_dealer_stats.loc['address_full'] = pivot_dealer_stats.loc['address_full'].apply(get_country)

        # new_index_names = ['DEALERNAME', 'COUNTRY','AUDIT DATE','GLOBAL SCORE', 'SALES SCORE', 'AFTER SALES SCORE','DIGITAL','DIGITAL RENAULT','DEALER ID'] # as required by the format.
        new_index_names = ['DEALERNAME', 'COUNTRY','AUDIT DATE','GLOBAL SCORE', 'SALES SCORE', 'AFTER SALES SCORE','DIGITAL','DIGITAL RENAULT','DIGITAL DACIA','DEALER ID'] # as required by the format.
        pivot_dealer_stats.insert(loc=0, column='header_name', value=new_index_names)  # as required by the format.
        pivot_dealer_stats.insert(loc=0, column='Question scoring', value=None)  # as required by the format.
        pivot_dealer_stats['Question scoring'].iloc[-1] = 'Question scoring'  # as required by the format.

        required_dealer_qa = dealer_qa[['question_number', 'status', 'filename']]
        required_dealer_qa = required_dealer_qa.reset_index(drop = True)

        required_dealer_qa.loc[required_dealer_qa['status'] == "OK",'status'] = 1 # scoring as specified
        required_dealer_qa.loc[required_dealer_qa['status'] == "KO",'status'] = 0 # scoring as specified
        required_dealer_qa.loc[required_dealer_qa['status'] == "PA",'status'] = 0.5 # scoring as specified
        required_dealer_qa.loc[required_dealer_qa['status'] == "NE",'status'] = 0 # scoring as specified
        
        # Ensure that the 'status' column is numeric
        required_dealer_qa['status'] = pd.to_numeric(required_dealer_qa['status'], errors='coerce')
        
        
        pivot_dealer_qa = required_dealer_qa.pivot(index='question_number', columns='filename', values='status')   
        

        # calculate scoring average for each question
        question_scoring = pivot_dealer_qa.mean(axis = 1)
        
        
        pivot_dealer_qa.insert(loc=0, column='Question scoring', value=question_scoring)
        pivot_dealer_qa['Question scoring'] = pivot_dealer_qa['Question scoring'].apply(calculate_percentage)

        
        pivot_dealer_qa = pivot_dealer_qa.fillna('-') # as required by the format.

        pivot_data = pd.concat([pivot_dealer_stats, pivot_dealer_qa]) # dynamically created data as required by the format

        
        # ref_scoring = fh.fetch_scoring_reference(ss.SCORING_PATH_DACIA)
        ref_scoring = fh.fetch_scoring_reference()
        ref_scoring.index = ref_scoring.index.map(str)
        # pivot_data.reset_index(drop= True, inplace=True)
        # ref_scoring.reset_index(drop= True, inplace=True)

        dealer_scoring = pd.concat([ref_scoring, pivot_data],axis=1) #axis=1

        return dealer_scoring
        
    except Exception as exception:
        print(exception)

# def get_verbatim(dealer_stats, dealer_qa):
    """
    Generates verbatim output
    Args:
        dealer_stats (DataFrame): dealer_statistics
        dealer_qa (DataFrame): dealer question and answer data

    Returns:
        verbatim_data (DataFrame): Verbatim output
    """
    try:
        dealer_qa_required = dealer_qa[['question_number','answer','pre-comment', 'status', 'filename']]
        dealer_qa_required = dealer_qa_required.loc[dealer_qa_required['pre-comment'].notnull(),] # condition for verbatim
        dealer_qa_required = dealer_qa_required.loc[dealer_qa_required['status'].notnull(),]# condition for verbatim
        dealer_qa_required.columns = ['Question Number','Comment','pre-comment', 'status', 'filename']

        dealer_code = dealer_stats.loc[dealer_stats['statistic'] == 'dealer_code',].reset_index(drop = True)[['value', 'filename']] # create dealer code table
        dealer_name = dealer_stats.loc[dealer_stats['statistic'] == 'name1',].reset_index(drop = True)[['value', 'filename']]  # create dealer name table
        dealer_code.columns = ['Dealer ID', 'filename']
        dealer_name.columns = ['Dealer Name', 'filename']
        
        dealer_qa_required = dealer_qa_required.merge(dealer_code)
        dealer_qa_required = dealer_qa_required.merge(dealer_name)

        verbatim_data = dealer_qa_required[['Dealer ID','Dealer Name', 'Question Number','Comment' ]]
        return verbatim_data
    except Exception as exception:
        print(exception)



    






