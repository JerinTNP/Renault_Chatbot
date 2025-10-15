"""
File name: path_constants
Description: set file paths and other constants here
"""

INPUT_PATH = "app/components/generate_tables/data/input"
# OUPUT_PATH = "app/components/generate_tables/data/output/audits_concatenated.xlsx" # PowerBI
OUTPUT_SCORING_PATH = "app/components/generate_tables/data/final/dealer_scoring.xlsx"
OUTPUT_VERBATIM_PATH = "app/components/generate_tables/data/final/verbatim.xlsx"


# --- Dynamic Constants ---
# These are initialized to None/empty and must be assigned in the main script
# AFTER the report type is determined.
QUESTIONS_PATH = None
MULTI_LINE_QUESTION_NUMBERS = {}
ACTIVITIES = []
COUNTRY_MAPPER = {}
SCORING_PATH = None
 
# --- Report Type Specific Configurations (As data for the main script) ---
 
CONFIGURATIONS = {
    "dacia-v1": {
        "QUESTIONS_PATH": "app/components/generate_tables/data/external/questions_dacia.xlsx",
        "MULTI_LINE_QUESTION_NUMBERS": {"9":1, "54":1, "55":1,"41b":1, "58":1, "60":1, "102":1, "109":1, "119":1,"148c":1, "151":1,
                                        "211":1, "203":1, "209":1,"223":1,"215":1,"221":1},
        "ACTIVITIES": ["% PRODUCT PRESENTATION","% PREPARATION / DELIVERY","% ORDER MANAGEMENT","% MANAGEMENT","% AFTERSALES ACTIVITY"
                       ,"% APPOINTMENT BOOKING / PREPARATION","% RECEPTION","% PRODUCTION","% RESTITUTION","% MANAGEMENT"
                       ,"% Website Conformity","% DIGITAL DACIA","% JOURNEY EXPERIENCE", "% Website Conformity"],
        "COUNTRY_MAPPER": {"Belgium":"Belgium","Italy":"Italy","Poland":"Poland","United Kingdom":"UK","Turkey":"Turkey","Morocco":"Morocco","Czech Republic":"Czech Republic","Slovakia":"Slovakia"},
        "SCORING_PATH": "app/components/generate_tables/data/external/scoring_reference_dacia.xlsx",
    },
    "dacia-v2": {
        "QUESTIONS_PATH": "app/components/generate_tables/data/external/questions_dacia_v2.xlsx",
        "MULTI_LINE_QUESTION_NUMBERS": {"9":1, "54":1, "55":1,"41b":1, "58":1, "60":1, "102":1, "109":1, "119":1,"148c":1, "151":1,
                                        "211":1, "203":1, "209":1,"223":1,"215":1,"221":1},
        "ACTIVITIES": ["% PRODUCT PRESENTATION","% PREPARATION / DELIVERY","% ORDER MANAGEMENT","% MANAGEMENT","% AFTERSALES ACTIVITY"
                       ,"% APPOINTMENT BOOKING / PREPARATION","% RECEPTION","% PRODUCTION","% RESTITUTION","% MANAGEMENT"
                       ,"% Website Conformity","% DIGITAL DACIA","% JOURNEY EXPERIENCE", "% Website Conformity"],
        "COUNTRY_MAPPER": {"Belgium":"Belgium","Italy":"Italy","Poland":"Poland","United Kingdom":"UK","Turkey":"Turkey","Morocco":"Morocco","Czech Republic":"Czech Republic","Slovakia":"Slovakia"},
        "SCORING_PATH": "app/components/generate_tables/data/external/scoring_reference_dacia_v2.xlsx",
    },
    "renault-v1": {
        "QUESTIONS_PATH": "app/components/generate_tables/data/external/questions_renault.xlsx",
        "MULTI_LINE_QUESTION_NUMBERS": {"54": 1, "55":1, "41b":1, "58": 1, "60": 1, "102": 1,"109": 1,"119":1,"148c":1,"151":1,"211":1,"203":1,"209":1},
        "ACTIVITIES": ["% PRODUCT PRESENTATION","% PREPARATION / DELIVERY","% ORDER MANAGEMENT","% MANAGEMENT","% AFTERSALES ACTIVITY"
                       ,"% APPOINTMENT BOOKING / PREPARATION","% RECEPTION","% PRODUCTION","% RESTITUTION","% MANAGEMENT"
                       ,"% Website Conformity"],
        "COUNTRY_MAPPER": {"India":"India", "Argentina":"Argentina","Brazil":"Brazil","Mexico":"Mexico","Colombia":"Colombia"},
        "SCORING_PATH": "app/components/generate_tables/data/external/scoring_reference_renault.xlsx",
    },
    "renault-v2": {
        "QUESTIONS_PATH": "app/components/generate_tables/data/external/questions_renault_v2.xlsx",
        "MULTI_LINE_QUESTION_NUMBERS": {"54": 1, "55":1, "41b":1, "58": 1, "60": 1, "102": 1,"109": 1,"119":1,"148c":1,"151":1,"211":1,"203":1,"209":1},
        "ACTIVITIES": ["% PRODUCT PRESENTATION","% PREPARATION / DELIVERY","% ORDER MANAGEMENT","% MANAGEMENT","% AFTERSALES ACTIVITY"
                       ,"% APPOINTMENT BOOKING / PREPARATION","% RECEPTION","% PRODUCTION","% RESTITUTION","% MANAGEMENT"
                       ,"% Website Conformity"],
        "COUNTRY_MAPPER": {"India":"India", "Argentina":"Argentina","Brazil":"Brazil","Mexico":"Mexico","Colombia":"Colombia"},
        "SCORING_PATH": "app/components/generate_tables/data/external/scoring_reference_renault_v2.xlsx",
    }
}
 
