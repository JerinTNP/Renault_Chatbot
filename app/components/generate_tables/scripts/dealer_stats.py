"""
File name: dealer_stats
Description: get high level dealer statistics
Approach: Rule based, can expect changes in future versions due to partial format changes in audit reports.
"""
import re
import pandas as pd

def detect_stats_high_level(above_line, below_line, column_name, dealer_high_level, last_row_flag = 0):
    """
    Detects required stats sandwitched between 2 lines.
    It also detects the data if the the entry is in the last rows of the tables.

    Args:
        above_line (String): line above required dealer stat
        below_line (String): line below required dealer stat
        column_name (int): colum were required dealer stat is present
        dealer_high_level (DataFrame): the first page table
        last_row_flag(Bool): flag to indicate if it is a last row or not

    Returns:
        stats_data (String): extracted data for dealer stats
    """    
    try:
        above_index = dealer_high_level.loc[dealer_high_level[column_name].str.contains(above_line)].index[0]
        below_index = dealer_high_level.loc[dealer_high_level[column_name].str.contains(below_line)].index[0]
        stats_data_list = list(dealer_high_level[column_name])
        if not last_row_flag:
            stats_data_list = stats_data_list[above_index+1:below_index]
            stats_data_list = [x for x in stats_data_list if x != ""]
            stats_data = ", ".join(stats_data_list)
        else:
            # handling if data available in last row, that is below line is absent.
            stats_data_list = stats_data_list[above_index+1:]
            stats_data_list = [x for x in stats_data_list if x != ""]
            stats_data = " ".join(stats_data_list)
        
        return stats_data
    except Exception as exception:
        print(exception)
    

def get_global_score(dealer_high_level):
    """
    Gets the global score from report.

    Args:
        dealer_high_level (DataFrame): the first page table

    Returns:
        global_score (String): extracted data for global score
    """
    try:
        column_data = list(set(list(dealer_high_level.iloc[:,2])))
        column_data.remove("Global Score")
        column_data.remove("")
        global_score = column_data[0]
        return global_score
    except Exception as exception:
        print(exception)

def get_digital_score(digital_table):
    try:
        column_data = list(set(list(digital_table.iloc[:,2])))
        column_data.remove("Digital Score")
        column_data.remove("")
        digital_score = column_data[0]
        return digital_score
    except Exception as exception:
        print(exception)



def detect_stats_detailed(stat_key, dealer_detailed, stat_position='left', occurrence=1):
    """Detects dealer statistics from complete report data. Looks for the statistic label and determines value.
    Args:
        stat_key (String): statistic label
        dealer_detailed (DataFrame): complete data in report
        stat_position (String, optional): Position of the the statistic value with respect to statistic label. Defaults to 'left'.
        occurrence (int, optional): The occurrence of the stat_key to look for. Defaults to 1 (first occurrence).

    Returns:
        stat_val (String): extracted data for dealer stats
    """
    try:
        # Flatten the entire DataFrame into a single string to search across all lines
        full_text = ' '.join(dealer_detailed['Detailed Report'].astype(str).tolist())
        full_text = full_text.replace("-", " ")

        # Find all positions of the stat_key in the full text
        positions = []
        start = 0
        while True:
            start = full_text.find(stat_key, start)
            if start == -1:
                break
            positions.append(start)
            start += len(stat_key)  # Move past the last found position

        if len(positions) < occurrence:
            raise ValueError(f"Stat key '{stat_key}' does not appear {occurrence} times in the detailed report.")

        key_index = positions[occurrence - 1]

        # Determine the immediate left or right value
        if stat_position == 'left':
            # Get the part of the text before the stat_key
            part_before_key = full_text[:key_index].strip()
            # Split the part before the stat_key by spaces and take the last element
            stat_val = part_before_key.split()[-1] if part_before_key else None
        else:
            # Get the part of the text after the stat_key
            part_after_key = full_text[key_index + len(stat_key):].strip()
            # Split the part after the stat_key by spaces and take the first element
            stat_val = part_after_key.split()[0] if part_after_key else None

        if not stat_val:
            raise ValueError(f"No value found {'before' if stat_position == 'left' else 'after'} the stat key '{stat_key}'.")

        return stat_val
    except Exception as exception:
        print(exception)
        return None



def detect_stats_below(stat_key, dealer_detailed):
    """Detects dealer statistics from complete report data. Looks for the statistic label and determines value located immediately below it.
    Args:
        stat_key (String): statistic label
        dealer_detailed (DataFrame): complete data in report

    Returns:
        stat_val (String): extracted data for dealer stats
    """
    try:
        # Locate the index of the row containing the stat_key
        row_index = dealer_detailed[dealer_detailed['Detailed Report'].str.contains(stat_key)].index[0]
        
        # Get the text of the row immediately below the row containing the stat_key
        stat_val = dealer_detailed.loc[row_index + 1, 'Detailed Report'].strip()
        
        if not stat_val:
            raise ValueError(f"No value found below the stat key '{stat_key}'.")

        return stat_val[-4:].split(" ")[1]
    except Exception as exception:
        print(exception)
        return None




def detect_management_detailed(dealer_detailed):
    """
    Detects statistics for MANAGEMENT.
    This is treated separately as it occurs twice in the data in the same line.

    Args:
        dealer_detailed (DataFrame): complete data in report

    Returns:
        management_val1 (String): extracted data for MANAGEMENT statistics 1
        management_val2 (String): extracted data for MANAGEMENT statistics 2
    """
    try:
        stat_key = "MANAGEMENT"
        # management will be detected in 2 rows. 2nd row is the actual management we require.
        df_line = str(dealer_detailed.loc[dealer_detailed['Detailed Report'].str.contains(stat_key),'Detailed Report'].iloc[1])
        df_line = df_line.replace("-"," ")
        df_list = df_line.split(' ')
        df_list = [x for x in df_list if x != '']

        # obtains the element( which is value) in the list before the statistic key.
        management_val1 = df_list[df_list.index(stat_key) - 1] 

        # obtains the element( which is value) in the list after the statistic key.
        management_val2 = df_list[df_list.index(stat_key) + 1]

        return management_val1, management_val2
    except Exception as exception:
        print(exception)



def get_dealer_stats(data_high_level, data_detailed, digital_data, digital_table):
    """
    Fetches dealer details and auditor details(stats)
    Args:
        data_high_level (DataFrame): the first page table
        data_detailed (DataFrame): complete data in report

    Returns:
        dealer_stat (DataFrame): dealer stats
    """
    try:
        dealer_stat = {}
        dealer_stat["name1"] = detect_stats_high_level("Dealer name","Dealer code",0, data_high_level)
        dealer_stat["address_full"] = detect_stats_high_level("Location","RRG",1, data_high_level)
        dealer_stat["dealer_code"]  = detect_stats_high_level("Dealer code","NV Renault Sales / year",0, data_high_level)
        dealer_stat["RRG"]  = detect_stats_high_level("RRG","NV Dacia Sales / Year",1, data_high_level)
        dealer_stat["Renault_sales_by_yr"] = detect_stats_high_level("NV Renault Sales / year","Workshop Customers / Day",0, data_high_level)
        dealer_stat["Dacia_sales_by_yr"] = detect_stats_high_level("NV Dacia Sales / Year","Principal Audited Brand",1, data_high_level)
        dealer_stat["wkshp_date"] = detect_stats_high_level("Workshop Customers / Day","Auditor",0, data_high_level)
        dealer_stat['Global_Score'] = get_global_score(data_high_level)
        dealer_stat["Auditor"] = detect_stats_high_level("Auditor","",0, data_high_level,1)
        dealer_stat["audit_date"] = detect_stats_high_level("Audit Date","",1, data_high_level,1)

        dealer_stat['new_vehicle_activity'] = detect_stats_detailed("NEW VEHICLES ACTIVITY", data_detailed,'right')
        dealer_stat['aftersales_activity'] = detect_stats_detailed("AFTERSALES ACTIVITY", data_detailed,'right') #
        dealer_stat['appointment_booking'] = detect_stats_detailed("APPOINTMENT BOOKING / PREPARATION", data_detailed)
        dealer_stat['customer_journey'] = detect_stats_detailed("CUSTOMER JOURNEY", data_detailed)
        dealer_stat['product_presentation'] = detect_stats_detailed("PRODUCT PRESENTATION", data_detailed)
        dealer_stat['reception'] = detect_stats_detailed("RECEPTION", data_detailed)
        dealer_stat['order_management'] = detect_stats_detailed("ORDER MANAGEMENT", data_detailed)
        dealer_stat['production'] = detect_stats_detailed("PRODUCTION", data_detailed)

        if data_detailed['Detailed Report'].str.contains("PREPARATION / DELIVERY").any():
            dealer_stat['preperation_delivery'] = detect_stats_detailed("PREPARATION / DELIVERY", data_detailed)
        elif data_detailed['Detailed Report'].str.contains("Preparation / Delivery").any():
            dealer_stat['preperation_delivery'] = detect_stats_detailed("Preparation / Delivery", data_detailed) 
        dealer_stat['restitution'] = detect_stats_detailed("RESTITUTION", data_detailed)
        dealer_stat['management1'], dealer_stat['management2'] = detect_management_detailed(data_detailed)
        dealer_stat['basics_sales_methods'] = detect_stats_detailed("Basics Sales Methods", data_detailed)
        dealer_stat['brand_store_renault'] = detect_stats_detailed("BRAND STORE RENAULT", data_detailed)
        dealer_stat['basics_aftersales_methods'] = detect_stats_detailed("Basics Aftersales Methods", data_detailed)
        dealer_stat['flash_ares_maintainence'] = detect_stats_detailed("FLASH ARES MAINTENANCE", data_detailed)
        dealer_stat['brand_store_dacia'] = detect_stats_detailed("BRAND STORE DACIA", data_detailed) 
        dealer_stat['digital_dacia'] = detect_stats_detailed("DIGITAL DACIA", digital_data,'right')

        dealer_stat['digital_renault'] = detect_stats_detailed("DIGITAL RENAULT", digital_data,'right')
        dealer_stat['journey_experience_renault'] = detect_stats_detailed("JOURNEY", digital_data,'left')
        dealer_stat['website_conformity_renault'] = detect_stats_detailed("Website conformity", digital_data,'left')
        
        dealer_stat['journey_experience_dacia'] = detect_stats_detailed("JOURNEY", digital_data,'left',occurrence=2) 
        dealer_stat['website_conformity_dacia'] = detect_stats_detailed("Website conformity", digital_data,'right')

        dealer_stat['digital_score'] = detect_stats_below("Digital Score", digital_data) #dacia


        # dealer_stat['digital_score'] = get_digital_score(digital_table) # without dacia
        # digital average
        # dealer_stat['digital_score'] = detect_stats_detailed("DIGITAL RENAULT", digital_data,'right')

        # digital average
        # if dealer_stat['digital_renault'] == "NA":
        #     digital_renault = dealer_stat['digital_dacia']
        # else:
        #     digital_renault = dealer_stat['digital_renault']
        # if dealer_stat['digital_dacia'] == "NA":
        #     digital_dacia = dealer_stat['digital_renault']
        # else:
        #     digital_dacia = dealer_stat['digital_dacia']
        # # digital_score = str(round((int(digital_dacia.replace("%", "")) + int(digital_renault.replace("%", "")))/2)) + "%"
        # digital_score = "{}%".format(int((int(digital_dacia.replace("%", "")) + int(digital_renault.replace("%", ""))) / 2))


        # dealer_stat['digital_score'] = digital_score

        dealer_stat = pd.DataFrame(dealer_stat.items(), columns = ['statistic', 'value'])   
        return dealer_stat
    
    except Exception as exception:
        print(exception)

