"""
File name: dealer_text
Description: get dealer quality assessment text
Approach: Rule based, can expect changes in future versions due to partial format changes in audit reports.
"""
from re import search
import pandas as pd

from app.components.generate_tables.scripts import settings as ss

def is_question(line, questions_partial):
    """
    Checks if the question is available in questions list.

    Args:
        line (String): line in report
        questions_partial (List): list of 1st lines of questions

    Returns:
        (Bool): True if it is a question else False
    """
    if line.strip() in questions_partial:
        return True
    return False


def detect_questions_detailed(dealer_qa, questions_partial, multi_line = ss.MULTI_LINE_QUESTION_NUMBERS):
    """
    Detects questions from the report
    Args:
        dealer_qa (DataFrame): qa data in report
        questions_partial (List): list of 1st lines of questions
        multi_line (Dict, optional): Dictionary of questions spanning multi-line. Defaults to ss.MULTI_LINE_QUESTION_NUMBERS.

    Returns:
        questions (List): list of questions
        question_numbers (List): list of question numbers
        question_indices (List): list of indices of questions
        multi_line_indices (Dict): dictionary of indicides of multi-line questions along with additional line count
    """
    questions = [] # to save all questions
    multi_line_indices = {} # to save index of multi-line question and number of additional lines
    question_indices = [] # to save index of all questions
    question_numbers = []
    for qa_index, qa_line in enumerate(list(dealer_qa['Detailed Report'])):
        if is_question(qa_line, questions_partial):
            line_split = qa_line.split('-',1)
            question_line = line_split[1] # removing question number and hyphen at the question start.
            if line_split[0].strip() in multi_line.keys():
                extra_lines = multi_line[line_split[0].strip()]
                multi_line_indices[qa_index] = extra_lines
                question_line = " ".join(list(dealer_qa['Detailed Report'])[qa_index: (qa_index + extra_lines + 1)])
                question_line = question_line.split('-',1)[1] # removing question number
            questions.append(question_line.strip())
            question_numbers.append(line_split[0].strip())
            question_indices.append(qa_index)
    question_indices.append(len(dealer_qa)) # end point to be used later to detect answer
    return questions, question_numbers, question_indices, multi_line_indices


def get_answer_idices(question_indices, multi_line_indices):
    """
    Fetches answer start and end indices of answers

    Args:
        question_indices (List): list of indices of questions
        multi_line_indices (Dict): dictionary of indicides of multi-line questions along with additional line count

    Returns:
        answer_indices_modified (List): list of tuples. each tuple indicating start and end of an answer.
    """

    answer_indices = [*zip(question_indices[::1],question_indices[1::1])] # create a tuple out of list to create start and end of answer
    answer_indices_modified = []
    for answer_index in answer_indices:
        temp_answer_index = list(answer_index)
        if temp_answer_index[0] in multi_line_indices.keys(): # in case of multi-line, start of the answer has to be modified
            temp_answer_index[0] = temp_answer_index[0] + multi_line_indices[temp_answer_index[0]]
        temp_answer_index[0] = temp_answer_index[0] + 1 # answer starts 1 level after question
        temp_answer_index = tuple(temp_answer_index)
        answer_indices_modified.append(temp_answer_index)
    return answer_indices_modified


def get_sub_answers(answer):
    """
    Fetch status, pre-comment, post-comment

    Args:
        answer (String): extracted answer

    Returns:
        (String): status in answer
        (String): pre-comment in answer
        (String): post-comment in answer
    """
    
    if search("KO -", answer):
        return "KO", answer.split('KO -',1)[0], answer.split('KO -',1)[1] 
    elif search("OK -", answer):
        return "OK", answer.split('OK -',1)[0], answer.split('OK -',1)[1]
    elif search("PA -", answer):
        return "PA", answer.split('PA -',1)[0], answer.split('PA -',1)[1]
    elif search("NE -", answer):
        return "NE", answer.split('NE -',1)[0], answer.split('NE -',1)[1]
    elif search("NA -", answer):
        return "NA", answer.split('NA -',1)[0], answer.split('NA -',1)[1]
    elif search("KO –", answer): # hiphen is present in 2 forms in the report.
        return "KO", answer.split('KO –',1)[0], answer.split('KO –',1)[1]
    elif search("OK –", answer):
        return "OK", answer.split('OK –',1)[0], answer.split('OK –',1)[1]
    elif search("PA –", answer):
        return "PA", answer.split('PA –',1)[0], answer.split('PA –',1)[1]
    elif search("NE –", answer):
        return "NE", answer.split('NE –',1)[0], answer.split('NE –',1)[1]
    elif search("NA –", answer):
        return "NA", answer.split('NA –',1)[0], answer.split('NA –',1)[1]
    else:
        return "", answer, ""



def detect_answers(dealer_qa, answer_indices):
    """
    Detect Answers from the report

    Args:
        dealer_qa (DataFrme): qa data in report
        answer_indices (List): list of tuples. each tuple indicating start and end of an answer.

    Returns:
        answers (String): complete detected answer
        statuses (String): status in answer
        pre_comments (String): pre-comment in answer
        post_comments (String): post-comment in answer

    """
    answers = []
    statuses = []
    pre_comments = []
    post_comments = []
    for answer_index in answer_indices:

        answer = list(dealer_qa['Detailed Report'])[answer_index[0]:answer_index[1]] # get the answer rows in data
        answer = "\n".join(answer)
        

        status, pre_comment, post_comment = get_sub_answers(answer)

        answers.append(answer)
        statuses.append(status)
        pre_comments.append(pre_comment)
        post_comments.append(post_comment.strip())

    return answers, statuses, pre_comments, post_comments


def detect_quality_assessment_results(dealer_qa, questions_partial):
    """
    Fetch quality assessment data from report.

    Args:
        dealer_qa (DataFrame): qa data in report
        questions_partial (List): list of 1st lines of questions

    Returns:
        qa_results (DataFrame): quality assessment results
    """
    questions, question_numbers, question_indices, multi_line_indices = detect_questions_detailed(dealer_qa, questions_partial)
    answer_indices = get_answer_idices(question_indices, multi_line_indices)
    answers, status, pre_comment, post_comment = detect_answers(dealer_qa, answer_indices)
    
    qa_results = pd.DataFrame({'question_number': question_numbers,
                               'question': questions,
                               'answer': answers,
                               'status': status,
                               'pre-comment': pre_comment,
                               'post-comment': post_comment
                               })
    return qa_results

    










