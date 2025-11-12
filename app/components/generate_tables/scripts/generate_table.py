"""
File name: generate_tables
Description: driver function
"""
 
from openpyxl import load_workbook
import pandas as pd
from app.logger import logging
from app.components.generate_tables.scripts import classify as cl
from app.components.generate_tables.scripts import file_handling as fh
from app.components.generate_tables.scripts import data_extract as de
from app.components.generate_tables.scripts import dealer_stats as ds
from app.components.generate_tables.scripts import dealer_text as dt
# import verbatim_scoring as vs
from app.components.generate_tables.scripts import settings as ss

 
 
def start_automation():
    """
    Main function for audit automation
 
    """
    path = r'app/components/generate_tables/data/external/categorized_questions.xlsx'
    workbook = load_workbook(path,read_only=True)
    question_set = pd.read_excel(path,sheet_name="Sheet1",engine='openpyxl')
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
            # print(dealer_statistics_temp)
            dealer_statistics_temp['filename'] = report_name
            print(report_name)
            dealer_statistics = pd.concat([dealer_statistics,dealer_statistics_temp], ignore_index = True)
            dealer_statistics["dealer_name"] = ds.detect_stats_high_level("Dealer name","Dealer code",0, report_high_level)
            dealer_statistics["dealer_code"]  = ds.detect_stats_high_level("Dealer code","NV Renault Sales / year",0, report_high_level)
            dealer_statistics["address_full"] = ds.detect_stats_high_level("Location","RRG",1, report_high_level)
            dealer_statistics["auditor"] = ds.detect_stats_high_level("Auditor","",0, report_high_level,1)
            dealer_statistics["country"] = dealer_statistics["address_full"].str.split(",").str[-1].str.strip()
            dealer_statistics['value'] = dealer_statistics['value'].astype(str).str.replace('%', '', regex=False)
       
            report_qa = de.filter_answers_data(report_detailed,config, report_type)
 
            temp_value = dt.detect_quality_assessment_results(report_qa, partial_questions,config)
            dealers_answers_temp = temp_value
 
            if dealers_answers_temp.empty:
                logging.warning(f"Skipping assignment for report {report_name}: Filtered answers data is empty due to extraction failure.")
                continue
 
            dealers_answers_temp['filename'] = report_name
            dealers_answers = pd.concat([dealers_answers,dealers_answers_temp], ignore_index = True)
            dealers_answers["dealer_name"] = ds.detect_stats_high_level("Dealer name","Dealer code",0, report_high_level)
            dealers_answers["dealer_code"]  = ds.detect_stats_high_level("Dealer code","NV Renault Sales / year",0, report_high_level)
            dealers_answers["address_full"] = ds.detect_stats_high_level("Location","RRG",1, report_high_level)
            dealers_answers["auditor"] = ds.detect_stats_high_level("Auditor","",0, report_high_level,1)
            dealers_answers["country"] = dealers_answers["address_full"].str.split(",").str[-1].str.strip()
            # dealers_answers = dealers_answers.drop(columns=['question_number','pre-comment','post-comment','status'])
            dealers_answers = dealers_answers.drop(columns=['question_number','status'])
            dealers_answers['comment'] = dealers_answers['pre-comment'].astype(str) + '.' + dealers_answers['post-comment'].astype(str)
            dealers_answers['comment'] = dealers_answers['comment'].str.lstrip('.')
            dealers_answers = dealers_answers.drop(columns=['pre-comment','post-comment'])
 
            dealers_answers = pd.merge(left=dealers_answers,right=question_set,on='question',how='left')  
           
            print(dealer_statistics)
            print(dealers_answers)
 
 
        return dealer_statistics,dealers_answers
    except Exception as exception:
        # Re-raise the exception so the calling function knows something went wrong
        print(f"Error during table automation: {exception}")
        raise
 