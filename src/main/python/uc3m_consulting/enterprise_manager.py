"""Module """
import re
import json

from datetime import datetime, timezone
from freezegun import freeze_time
from uc3m_consulting.enterprise_project import EnterpriseProject
from uc3m_consulting.enterprise_management_exception import EnterpriseManagementException
from uc3m_consulting.enterprise_manager_config import (PROJECTS_STORE_FILE,
                                                       TEST_DOCUMENTS_STORE_FILE,
                                                       TEST_NUMDOCS_STORE_FILE)
from uc3m_consulting.project_document import ProjectDocument


class EnterpriseManager:
    """Class for providing the methods for managing the orders"""
    def __init__(self):
        pass

    @staticmethod
    def validate_cif(cif: str):
        """validates a cif number """
        if not isinstance(cif, str):
            raise EnterpriseManagementException("CIF code must be a string")
        pattern = re.compile(r"^[ABCDEFGHJKNPQRSUVW]\d{7}[0-9A-J]$")
        if not pattern.fullmatch(cif):
            raise EnterpriseManagementException("Invalid CIF format")

        first_letter = cif[0]
        digits = cif[1:8]
        control_char = cif[8]

        odd_sum = 0
        even_sum = 0

        for index in range(len(digits)):
            if index % 2 == 0:
                doubled = int(digits[index]) * 2
                if doubled > 9:
                    odd_sum = odd_sum + (doubled // 10) + (doubled % 10)
                else:
                    odd_sum = odd_sum + doubled
            else:
                even_sum = even_sum + int(digits[index])

        total = odd_sum + even_sum
        remainder = total % 10
        control_num = 10 - remainder

        if control_num == 10:
            control_num = 0

        letter_map = "JABCDEFGHI"

        if first_letter in ('A', 'B', 'E', 'H'):
            if str(control_num) != control_char:
                raise EnterpriseManagementException("Invalid CIF character control number")
        elif first_letter in ('P', 'Q', 'S', 'K'):
            if letter_map[control_num] != control_char:
                raise EnterpriseManagementException("Invalid CIF character control letter")
        else:
            raise EnterpriseManagementException("CIF type not supported")
        return True

    def validate_starting_date(self, date_str):
        """validates the date format using regex"""
        date_pattern = re.compile(r"^(([0-2]\d|3[0-1])\/(0\d|1[0-2])\/\d\d\d\d)$")
        match = date_pattern.fullmatch(date_str)
        if not match:
            raise EnterpriseManagementException("Invalid date format")

        try:
            parsed_date = datetime.strptime(date_str, "%d/%m/%Y").date()
        except ValueError as ex:
            raise EnterpriseManagementException("Invalid date format") from ex

        if parsed_date < datetime.now(timezone.utc).date():
            raise EnterpriseManagementException("Project's date must be today or later.")

        if parsed_date.year < 2025 or parsed_date.year > 2050:
            raise EnterpriseManagementException("Invalid date format")
        return date_str

    # pylint: disable=too-many-arguments, too-many-positional-arguments
    def register_project(self,
                         company_cif: str,
                         project_acronym: str,
                         project_description: str,
                         department: str,
                         date: str,
                         budget: str):
        """registers a new project"""
        self.validate_cif(company_cif)

        acronym_pattern = re.compile(r"^[a-zA-Z0-9]{5,10}")
        acronym_match = acronym_pattern.fullmatch(project_acronym)
        if not acronym_match:
            raise EnterpriseManagementException("Invalid acronym")

        description_pattern = re.compile(r"^.{10,30}$")
        description_match = description_pattern.fullmatch(project_description)
        if not description_match:
            raise EnterpriseManagementException("Invalid description format")

        department_pattern = re.compile(r"(HR|FINANCE|LEGAL|LOGISTICS)")
        department_match = department_pattern.fullmatch(department)
        if not department_match:
            raise EnterpriseManagementException("Invalid department")

        self.validate_starting_date(date)

        try:
            budget_float = float(budget)
        except ValueError as exc:
            raise EnterpriseManagementException("Invalid budget amount") from exc

        budget_str = str(budget_float)
        if '.' in budget_str:
            decimal_places = len(budget_str.split('.')[1])
            if decimal_places > 2:
                raise EnterpriseManagementException("Invalid budget amount")

        if budget_float < 50000 or budget_float > 1000000:
            raise EnterpriseManagementException("Invalid budget amount")

        new_project = EnterpriseProject(company_cif=company_cif,
                                        project_acronym=project_acronym,
                                        project_description=project_description,
                                        department=department,
                                        starting_date=date,
                                        project_budget=budget)

        try:
            with open(PROJECTS_STORE_FILE, "r", encoding="utf-8", newline="") as file:
                projects_list = json.load(file)
        except FileNotFoundError:
            projects_list = []
        except json.JSONDecodeError as ex:
            raise EnterpriseManagementException("JSON Decode Error - Wrong JSON Format") from ex

        for existing_project in projects_list:
            if existing_project == new_project.to_json():
                raise EnterpriseManagementException("Duplicated project in projects list")

        projects_list.append(new_project.to_json())

        try:
            with open(PROJECTS_STORE_FILE, "w", encoding="utf-8", newline="") as file:
                json.dump(projects_list, file, indent=2)
        except FileNotFoundError as ex:
            raise EnterpriseManagementException("Wrong file  or file path") from ex
        except json.JSONDecodeError as ex:
            raise EnterpriseManagementException("JSON Decode Error - Wrong JSON Format") from ex
        return new_project.project_id

    def find_docs(self, date_str):
        """
        Generates a JSON report counting valid documents for a specific date.

        Checks cryptographic hashes and timestamps to ensure historical data integrity.
        Saves the output to 'resultado.json'.

        Args:
            date_str (str): date to query.

        Returns:
            number of documents found if report is successfully generated and saved.

        Raises:
            EnterpriseManagementException: On invalid date, file IO errors,
                missing data, or cryptographic integrity failure.
        """
        date_pattern = re.compile(r"^(([0-2]\d|3[0-1])\/(0\d|1[0-2])\/\d\d\d\d)$")
        match = date_pattern.fullmatch(date_str)
        if not match:
            raise EnterpriseManagementException("Invalid date format")

        try:
            parsed_date = datetime.strptime(date_str, "%d/%m/%Y").date()
        except ValueError as ex:
            raise EnterpriseManagementException("Invalid date format") from ex

        try:
            with open(TEST_DOCUMENTS_STORE_FILE, "r", encoding="utf-8", newline="") as file:
                documents_list = json.load(file)
        except FileNotFoundError as ex:
            raise EnterpriseManagementException("Wrong file  or file path") from ex

        doc_count = 0

        for document in documents_list:
            timestamp_val = document["register_date"]
            doc_date_str = datetime.fromtimestamp(timestamp_val).strftime("%d/%m/%Y")

            if doc_date_str == date_str:
                doc_datetime = datetime.fromtimestamp(timestamp_val, tz=timezone.utc)
                with freeze_time(doc_datetime):
                    doc_obj = ProjectDocument(document["project_id"], document["file_name"])
                    if doc_obj.document_signature == document["document_signature"]:
                        doc_count = doc_count + 1
                    else:
                        raise EnterpriseManagementException("Inconsistent document signature")

        if doc_count == 0:
            raise EnterpriseManagementException("No documents found")

        now_timestamp = datetime.now(timezone.utc).timestamp()
        report_entry = {"Querydate": date_str,
                        "ReportDate": now_timestamp,
                        "Numfiles": doc_count}

        try:
            with open(TEST_NUMDOCS_STORE_FILE, "r", encoding="utf-8", newline="") as file:
                reports_list = json.load(file)
        except FileNotFoundError:
            reports_list = []
        except json.JSONDecodeError as ex:
            raise EnterpriseManagementException("JSON Decode Error - Wrong JSON Format") from ex

        reports_list.append(report_entry)

        try:
            with open(TEST_NUMDOCS_STORE_FILE, "w", encoding="utf-8", newline="") as file:
                json.dump(reports_list, file, indent=2)
        except FileNotFoundError as ex:
            raise EnterpriseManagementException("Wrong file  or file path") from ex
        return doc_count