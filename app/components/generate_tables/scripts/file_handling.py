"""
File name: file_handling
Description: input output file and data handling
"""

from openpyxl import load_workbook
import os
import time
import pandas as pd
from app.components.generate_tables.scripts import settings as ss
from app.info import db_info



def get_output_data(file_workbook = ss.OUPUT_PATH):
    """
    The code handles multiple runs.
    Hence, it is important to exract the output workbook.
    If output workbook is absent, it has to be created.
    The data of the workbook should also be loaded, in case files have to be deleted or replaced.

    Args:
        file_workbook (String, optional): Output file path. Defaults to ss.OUPUT_PATH.

    Returns:
        dealer_stats (DataFrame): dealer statistics
        dealer_qa (DataFrame): dealer question and answer data
        file_info (DataFrame): report modified time
    """

    try:
        if os.path.isfile(file_workbook):

            # read all sheets in the workbook
            workbook = load_workbook(file_workbook, read_only=True) 
            dealer_stats = pd.read_excel(file_workbook, sheet_name="dealer_stats",engine='openpyxl')
            dealer_qa = pd.read_excel(file_workbook, sheet_name="dealer_qa",engine='openpyxl')


            file_info = pd.read_excel(file_workbook, sheet_name="file_info",engine='openpyxl')
            workbook.close()
        
        else:

            # create workbook as it does not exist
            workbook_new = pd.ExcelWriter(file_workbook, engine='xlsxwriter')
            workbook_new.close()

            # initilaze dataframes with the expected output structure
            dealer_stats = pd.DataFrame(columns = ['statistic', 'value','filename'])
            dealer_qa = pd.DataFrame(columns = ['question_number', 'question','answer','status','pre-comment','post-comment','filename'])
            file_info = pd.DataFrame(columns = ['last modified file time','filename'])
        
        return dealer_stats, dealer_qa, file_info
    except Exception as exception:
        print(exception)


def write_output(dealer_stats, dealer_qa, file_info, file_workbook = ss.OUPUT_PATH):
    """
    Write File output

    Args:
        dealer_stats (DataFrame): dealer statistics
        dealer_qa (DataFrame): dealer question and answer data
        file_info (DataFrame): report modified time
        file_workbook (String, optional): Output file path. Defaults to ss.OUPUT_PATH.
    """ 
    try:
        writer = pd.ExcelWriter(file_workbook, engine='xlsxwriter')
        dealer_stats.to_excel(writer, sheet_name='dealer_stats', index=False)
        # dealer_qa.to_excel(writer, sheet_name='dealer_qa', index=False)
        # file_info.to_excel(writer, sheet_name='file_info', index=False)
        writer.close()
    except Exception as exception:
        print(exception)



def get_existing_automated_files(files_time_data):
    """
    Get list of all automated files

    Args:
        files_time_data (DataFrame): report modified time

    Returns:
        file_names (List): list of existing files
    """ 
    try:   
        file_names = list(files_time_data['filename'])
        return file_names
    except Exception as exception:
        print(exception)


def get_input_files(reports_path = ss.INPUT_PATH):
    """
    Gets all file paths in the input folder, ignores directories(folders)

    Args:
        reports_path (String, optional): input folder path. Defaults to ss.INPUT_PATH.

    Returns:
       file_paths (List): list of files (with complete path) in the input folder
       file_names (List): list of files in the input folder
    """
    try:
        file_paths = [os.path.join(reports_path, file) for file in os.listdir(reports_path) if os.path.isfile(os.path.join(reports_path, file))]
        file_names = [ file for file in os.listdir(reports_path) if os.path.isfile(os.path.join(reports_path, file))]
        return file_paths, file_names
    except Exception as exception:
        print(exception)

# Example usage
# file_paths_to_country, file_names_to_country = get_input_files("/path/to/reports")
# print(file_paths_to_country)
# print(file_names_to_country)

def get_modified_time(path_file):
    """
    Get file modified time

    Args:
        path_file (String): input file path

    Returns:
        file_modified_time (String): date and time as string eg: '2023-02-23 16:51:36'
    """
    try:
        file_modified_time = time.strftime("%Y-%m-%d %H:%M:%S",time.strptime(time.ctime(os.path.getmtime(path_file))))
        return file_modified_time
    except Exception as exception:
        print(exception)


def is_new_file(file_name, file_path, file_info,existing_files):
    """
    The function checks if the file is new or replacement.
    It ignores file formats other than PDF.
    In case a file is replacement, it is considered new.
    Correct the last modified time in case of file replacement.

    Args:
        file_name (String): input file name
        file_path (String): input file path
        file_info (DataFrame): report modified time
        existing_files (List): list of existing (automated) audit reports

    Returns:
        is_new_flag (Bool): flag to denote new file
        is_modified_flag (Bool): flag to denote replaced file
        file_info (DataFrame): report modified time
    """
    try:
        is_new_flag = False
        is_modified_flag = False
        
        # do not consider for automation if file is not in pdf format
        if not file_name.endswith('.pdf'):
            return is_new_flag, is_modified_flag, file_info
        
        new_modified_time = get_modified_time(file_path)

        # detect new files
        if file_name not in existing_files:
            file_info.loc[len(file_info.index)] = [new_modified_time, file_name]
            is_new_flag = True
            return is_new_flag, is_modified_flag, file_info
        
        last_modified_time = file_info.loc[file_info['filename'] == file_name, 'last modified file time'].iloc[0]

        # detect replacement files
        if new_modified_time > last_modified_time:
            file_info.loc[file_info['filename'] == file_name, 'last modified file time'] = new_modified_time
            is_new_flag = True
            is_modified_flag = True
            return is_new_flag, is_modified_flag, file_info
        
        return is_new_flag, is_modified_flag, file_info
    
    except Exception as exception:
        print(exception)


def get_deleted_files(existing_files, file_names):
    """
    Gets the list of deleted files

    Args:
        existing_files (List): list of existing (automated) audit reports
        file_names (List): list of files in the input folder

    Returns:
        deleted_files (List): list of deleted files.
    """   
    try: 
        deleted_files = list(set(existing_files) - set(file_names))
        return deleted_files
    except Exception as exception:
        print(exception)


def delete_records(dealer_stats, dealer_qa,file_info, file_names, delete_timeline_flag = False):
    """
    Deletes record by filtering out filtering by file name

    Args:
        dealer_stats (DataFrame): dealer statistics
        dealer_qa (DataFrame): dealer question and answer data
        file_info (DataFrame): report modified time
        file_names (List): list of files to be deleted files
        delete_timeline_flag (Bool, optional): _description_. Defaults to False.

    Returns:
        dealer_stats (DataFrame): dealer statistics
        dealer_qa (DataFrame): dealer question and answer data
        file_info (DataFrame): report modified time    
    """
    try:
        dealer_stats = dealer_stats.drop(dealer_stats.loc[dealer_stats['filename'].isin(file_names)].index)
        dealer_stats = dealer_stats.reset_index(drop = True)

        dealer_qa = dealer_qa.drop(dealer_qa.loc[dealer_qa['filename'].isin(file_names)].index)
        dealer_qa = dealer_qa.reset_index(drop = True)
        
        if delete_timeline_flag:
            # delete from  file_info only in cases the flag is set(actual file deletion)
            file_info = file_info.drop(file_info.loc[file_info['filename'].isin(file_names)].index)
            file_info = file_info.reset_index(drop = True)

        return dealer_stats, dealer_qa, file_info
    except Exception as exception:
        print(exception)


def fetch_questions(question_file):
        """
        Fetch first line of all questions.

        Args:
            question_file (String, optional): questions file path. Defaults to ss.QUESTIONS_PATH.

        Returns:
            questions_partial(List): question (first line) list
        """
        questions_partial = list(pd.read_excel(question_file)['QUESTION'])
        questions_partial = [question.replace("\n","").strip() for question in questions_partial]
        return questions_partial


def fetch_scoring_reference(scoring_file=ss.SCORING_PATH):
        """
        Fetch scoring reference.

        Args:
            scoring_file (String, optional): scoring reference file path. Defaults to ss.QUESTIONS_PATH.

        Returns:
            scoring_reference (DataFrame): scoring reference
        """
        scoring_reference = pd.read_excel(scoring_file, index_col=('index'))
        return scoring_reference


# def write_scoring_file(dealer_scoring, scoring_output = ss.OUTPUT_SCORING_PATH):
#     """
#     write dealer scoring output to a file

#     Args:
#         dealer_scoring (DataFrame): dealer scoring output
#         scoring_output (String, optional): output file path. Defaults to ss.OUTPUT_SCORING_PATH.
#     """
#     dealer_scoring.to_excel(scoring_output, index = False, header = None)


# def write_verbatim_file(verbatim_data, verbatim_output = ss.OUTPUT_VERBATIM_PATH):
#     """
#     write verbatim output to a file

#     Args:
#         verbatim_data (DataFrame): verbatim output
#         verbatim_output (String, optional): output file path. Defaults to ss.OUTPUT_VERBATIM_PATH.
#     """
#     verbatim_data.to_excel(verbatim_output, index = False)