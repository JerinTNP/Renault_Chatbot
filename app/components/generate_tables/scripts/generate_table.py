"""
File name: generate_tables
Description: driver function
"""
 
from openpyxl import load_workbook
import pandas as pd
from app.components.generate_tables.scripts import classify as cl
from app.components.generate_tables.scripts import file_handling as fh
from app.components.generate_tables.scripts import data_extract as de
from app.components.generate_tables.scripts import dealer_stats as ds
from app.components.generate_tables.scripts import dealer_text as dt
# import verbatim_scoring as vs
from app.components.generate_tables.scripts import settings as ss

path = "app/components/generate_tables/data/external/questions_metadata.xlsx"
workbook = load_workbook(path,read_only=True)
all_questions_df = pd.read_excel(path,sheet_name="Sheet1",engine='openpyxl')
all_questions_df = all_questions_df.drop(columns = ['tag_1','subtag_1'])
 


def start_automation():
    """
    Main function for audit automation
 
    """
    try:
        report_type = cl.classify_pdf_file(ss.INPUT_PATH)
        if report_type is None:
            # Raise a specific error that can be caught by the API endpoint
            raise ValueError("Could not determine the report type. The PDF format may be unsupported or unrecognized.")
        
        config = ss.CONFIGURATIONS.get(report_type)
        if config is None:
            raise KeyError(f"No configuration found for the report type: '{report_type}'")
        
        print("classification done")

        questions_path = config["QUESTIONS_PATH"]
        
        dealer_statistics = pd.DataFrame(columns = ['statistic','value','filename'])
        dealers_answers = pd.DataFrame(columns = ['question_number', 'question','answer','status','pre-comment','post-comment','filename'])
        report_timeline = pd.DataFrame(columns = ['last modified file time','filename'])

        existing_reports = fh.get_existing_automated_files(report_timeline)
        report_paths, report_names = fh.get_input_files()
        partial_questions = fh.fetch_questions(questions_path)
       
       
        # handle deleted files
        deleted_reports = fh.get_deleted_files(existing_reports, report_names)
        dealer_statistics, dealers_answers, report_timeline =  fh.delete_records(dealer_statistics, dealers_answers,report_timeline, deleted_reports, True)
 
       
 
        for report_index,report_path in enumerate(report_paths):
 
            report_name = report_names[report_index]
            is_new, is_modified, report_timeline = fh.is_new_file(report_name, report_path, report_timeline,existing_reports)
           
            # ignore any old file and non-pdf formats
            if not is_new:
                continue
 
            # delete existing data from statistics and answers dataframes in case of replacement.
            if is_modified:
                dealer_statistics, dealers_answers, report_timeline = fh.delete_records(dealer_statistics, dealers_answers,report_timeline, [report_name])
 
            # get data from reports
            report_high_level, report_detailed, digital_data, digital_table = de.extract_data(report_path)
           
            # get dealer statistics
            dealer_statistics_temp = ds.get_dealer_stats(report_high_level, report_detailed, digital_data, digital_table,report_type)
           
            dealer_statistics_temp['filename'] = report_name
            print(report_name)
            dealer_statistics = pd.concat([dealer_statistics,dealer_statistics_temp], ignore_index = True)
            dealer_statistics['file_name'] = report_name
            # get quality assessment data
            report_qa = de.filter_answers_data(report_detailed,config, report_type)
 
            temp_value = dt.detect_quality_assessment_results(report_qa, partial_questions,config)
            dealers_answers_temp = temp_value
 
            dealers_answers_temp['filename'] = report_name
            dealers_answers = pd.concat([dealers_answers,dealers_answers_temp], ignore_index = True)
            dealers_answers['question'] = dealers_answers['question_number'].astype(str) + ' - ' + dealers_answers['question'].astype(str)
 
           
 
            #dealer_qa file transformation
           
            # print(all_questions_df)
            merged = all_questions_df.merge(dealers_answers,on='question',how='left')
            master_table = pd.concat([merged],axis=1)
            master_table = master_table.drop(columns=['question','question_number','pre-comment','post-comment','filename','answer'])
            master_table = master_table.T
            master_table.columns = master_table.iloc[0]
            master_table = master_table[1:].reset_index(drop=True)
            dealer_name = dealer_statistics['dealer_name']
            master_table.insert(loc=0,column='dealer_name',value=dealer_name)
            country_name = dealer_statistics['Country']
            master_table.insert(loc=1,column='country',value=country_name)
            master_table['ok_count'] = (master_table == 'OK').sum(axis=1)
            master_table['ko_count'] = (master_table == 'KO').sum(axis=1)
            master_table['file_name'] = report_name
 
 
        # change column names in dealer_statistics
        dealer_statistics = dealer_statistics.rename(columns={"Renault_sales_by_yr":"renault_sales_per_year"})
        dealer_statistics = dealer_statistics.rename(columns={"Dacia_sales_by_yr":"dacia_sales_per_year"})
        dealer_statistics = dealer_statistics.rename(columns={"Workshop Customers/day":"workshop_customers_per_day"})
        dealer_statistics = dealer_statistics.rename(columns={"appointment_booking":"appointment_booking_per_preparation"})
        dealer_statistics = dealer_statistics.rename(columns={"preperation_delivery":"preperation_per_delivery"})
        dealer_statistics = dealer_statistics.rename(columns={"management1":"new_vehicle_activity_management"})
        dealer_statistics = dealer_statistics.rename(columns={"management2":"aftersales_activity_management"})
        dealer_statistics = dealer_statistics.rename(columns={"RRG":"rrg"})
        dealer_statistics = dealer_statistics.rename(columns={"RRG":"rrg"})
        dealer_statistics = dealer_statistics.rename(columns={"Global_Score":"global_score"})
        dealer_statistics = dealer_statistics.rename(columns={"Auditor":"auditor"})
        dealer_statistics = dealer_statistics.rename(columns={"Country":"country"})
 
        combined_table = pd.concat([dealer_statistics,master_table],axis=1)
        combined_table = combined_table.iloc[:,3:]
        is_not_duplicate_name = ~combined_table.columns.duplicated(keep='first')
        combined_table = combined_table.loc[:, is_not_duplicate_name]

        # --- FIX: Clean NaN values and set correct data type ---
        combined_table['ok_count'] = combined_table['ok_count'].fillna(0).astype(int)
        combined_table['ko_count'] = combined_table['ko_count'].fillna(0).astype(int)
 
        # combined_table.to_excel("data\output\sample.xlsx", index=False)
        return combined_table

    except Exception as exception:
        # Re-raise the exception so the calling function knows something went wrong
        print(f"Error during table automation: {exception}")
        raise
 
# def start_verbatim_scoring():
#     """
#     Main function to generate verbatim and dealer scoring files
#     """
#     try:
 
#         dealer_statistics, dealers_answers, report_timeline = fh.get_output_data()
 
#         scoring_dealer = vs.get_dealer_scoring(dealer_statistics, dealers_answers)
#         fh.write_scoring_file(scoring_dealer)
#         verbatim_data = vs.get_verbatim(dealer_statistics, dealers_answers)
#         fh.write_verbatim_file(verbatim_data)
   
#     except Exception as exception:
#         print(exception)
 
# if __name__ == "__main__":
#     start_automation()
#     start_verbatim_scoring()
 