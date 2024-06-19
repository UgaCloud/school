# Roles


SUPERVISOR = "Supervisor"
FIELD_MANAGER = "Field Manager"
FINANCE_OFFICER = "Finance Office"
PROJECT_MANAGER = "Project Manager"
GENERAL_MANAGER = "General Manager"
######## End of Roles ############

# Types
ISP = 'ISP'
OFC = 'OFC'
OSP = 'OSP'
FINANCIAL = 'Financial'
WAREHOUSE = 'Warehouse'
POWER = 'Power'
MAINTENANCE = 'Maintenance'
WORKSHOP = 'Workshop'
ADMINISTRATOR = 'Administrator'
SECURITY = 'Security'
TRANSPORT = 'Transport'
MISCELLANEOUS = 'Miscellaneous'

TYPE_CHOICES = [
    (ISP, ISP),
    (OFC, OFC),
    (OSP, OSP),
    (FINANCIAL, FINANCIAL),
    (WAREHOUSE, WAREHOUSE),
    (POWER, POWER),
    (MAINTENANCE, MAINTENANCE),
    (WORKSHOP, WORKSHOP),
    (ADMINISTRATOR, ADMINISTRATOR),
    (SECURITY, SECURITY),
    (TRANSPORT, TRANSPORT),
    (MISCELLANEOUS, MISCELLANEOUS)
]

GENDERS = [
    ("M", "Male"),
    ("F", "Female")
]

RELIGIONS = [
    ("Muslim", "Muslim"),
    ("Protestant", "Protestant"),
    ("Catholic", "Catholic"),
    ("Adventist", "Adventist"),
    ("Others", "Others"),
]

NATIONALITIES = [
    ("Ugandan", "Ugandan"),
    ("Kenyan", "Kenyan"),
    ("Tanzanian", "Tanzanian"),
    ("Rwanda", "Rwanda"),
    ("South Sudan", "South Sudan"),
    ("Burundi", "Burundi"),
]

SUCCESS_ADD_MESSAGE = "Record Saved!"

SUCCESS_EDIT_MESSAGE = "Changes Saved"

DELETE_MESSAGE = "Record Deleted"

FAILURE_MESSAGE = "Something Went Wrong!, Check your inputs and Try again"

INTEGRITY_ERROR_MESSAGE = "The record you tried to add is a duplicate or contains duplicate values" \
                          " for unique fields."

INVALID_FORM_MESSAGE = "The form values are invalid or duplicate for unique fields."

WAGE_BILL_PAYMENT_GENERATION_CONFIRM_MESSAGE \
    = "This operation can only be done once. All payables on unapproved " \
      "submitted wage sheets will not be included in the wage bill payments " \
      "for Wage bill week"

PALETTE = ['#465b65', '#184c9c', '#d33035', '#ffc107', '#28a745', '#6f7f8c', '#6610f2', '#6e9fa5', '#fd7e14',
           '#e83e8c', '#17a2b8', '#6f42c1']
