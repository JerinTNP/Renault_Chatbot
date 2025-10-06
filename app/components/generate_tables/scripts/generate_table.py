"""
File name: init
Description: driver function
"""
import pandas as pd

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
    try:

        dealer_statistics, dealers_answers, report_timeline = fh.get_output_data()
        existing_reports = fh.get_existing_automated_files(report_timeline)
        report_paths, report_names = fh.get_input_files()
        partial_questions = fh.fetch_questions(ss.QUESTIONS_PATH)
              
  
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
            dealer_statistics_temp = ds.get_dealer_stats(report_high_level, report_detailed, digital_data, digital_table)
            
            dealer_statistics_temp['filename'] = report_name
            print(report_name)
            dealer_statistics = pd.concat([dealer_statistics,dealer_statistics_temp], ignore_index = True)
            # get quality assessment data
            report_qa = de.filter_answers_data(report_detailed)

            dealers_answers_temp = dt.detect_quality_assessment_results(report_qa, partial_questions)

            dealers_answers_temp['filename'] = report_name
            dealers_answers = pd.concat([dealers_answers,dealers_answers_temp], ignore_index = True)

        # fh.write_output(dealer_statistics, dealers_answers, report_timeline)
        return dealer_statistics  

    except Exception as exception:
        print(exception)


# def start_verbatim_scoring():
#     """
#     Main function to generate verbatim and deaer scoring files
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
    # start_verbatim_scoring()

