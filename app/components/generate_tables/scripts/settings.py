"""
File name: path_constants
Description: set file paths and other constants here
"""

INPUT_PATH = "app/components/generate_tables/data/input"
OUPUT_PATH = "app/components/generate_tables/data/output/audits_concatenated.xlsx" # PowerBI
OUTPUT_SCORING_PATH = "app/components/generate_tables/data/final/dealer_scoring.xlsx"
OUTPUT_VERBATIM_PATH = "app/components/generate_tables/data/final/verbatim.xlsx"


# QUESTIONS_PATH = "./data/external/questions_renault.xlsx" 
# QUESTIONS_PATH = "./data/external/questions_renault_v2.xlsx" 
QUESTIONS_PATH = "app/components/generate_tables/data/external/questions_dacia.xlsx" 
# QUESTIONS_PATH = "./data/external/questions_dacia_v2.xlsx"
# if questions are multi-line, only the first line is present in the file.
# questions can be copied from an excel reference given by the audit team.
# certains questions may have to be copied from report itself because of ascii difference in space and hyphen.

# MULTI_LINE_QUESTION_NUMBERS = {"54": 1, "55":1, "41b":1, "58": 1, "60": 1, "102": 1,"109":
                                # 1,"119":1,"148c":1,"151":1,"211":1,"203":1,"209":1}# without dacia
MULTI_LINE_QUESTION_NUMBERS = {"9":1, "54":1, "55":1,"41b":1, "58":1, "60":1, "102":1, "109":1, "119":1,"148c":1, "151":1, 
                               "211":1, "203":1, "209":1,"223":1,"215":1,"221":1} # with dacia multi line questions
# this is created after manually checking PDF extract output and reports.
# the dictionary is of the format {"question number": extra line count }

# ACTIVITIES = ["% PRODUCT PRESENTATION","% PREPARATION / DELIVERY","% ORDER MANAGEMENT","% MANAGEMENT","% AFTERSALES ACTIVITY"
# ,"% APPOINTMENT BOOKING / PREPARATION","% RECEPTION","% PRODUCTION","% RESTITUTION","% MANAGEMENT"
# ,"% Website Conformity"]
ACTIVITIES = ["% PRODUCT PRESENTATION","% PREPARATION / DELIVERY","% ORDER MANAGEMENT","% MANAGEMENT","% AFTERSALES ACTIVITY"
,"% APPOINTMENT BOOKING / PREPARATION","% RECEPTION","% PRODUCTION","% RESTITUTION","% MANAGEMENT"
,"% Website Conformity","% DIGITAL DACIA","% JOURNEY EXPERIENCE", "% Website Conformity"]
# list of all activities in quality assessment

# COUNTRY_MAPPER = {"India":"India", "Argentina":"Argentina","Brazil":"Brazil","Mexico":"Mexico","Colombia":"Colombia"} 
COUNTRY_MAPPER = {"Belgium":"Belgium","Italy":"Italy","Poland":"Poland","United Kingdom":"UK","Turkey":"Turkey","Morocco":"Morocco","Czech Republic":"Czech Republic","Slovakia":"Slovakia"}
# countries to be presented in Dealer scoring excel
# format to be followed: {key to look in data: country label to return}


SCORING_PATH = "app/components/generate_tables/data/external/scoring_reference_dacia.xlsx"
# SCORING_PATH = "./data/external/scoring_reference_dacia_v2.xlsx"
# SCORING_PATH = "./data/external/scoring_reference_renault.xlsx"
# SCORING_PATH = "./data/external/scoring_reference_renault_v2.xlsx"
# reference format for Dealer scoring excel


