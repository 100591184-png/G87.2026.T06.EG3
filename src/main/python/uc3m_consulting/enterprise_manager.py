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
        """validates a cif number"""
        if not isinstance(cif, str):
            raise EnterpriseManagementException("CIF code must be a string")
        pattern = re.compile(r"^[ABCDEFGHJKNPQRSUVW]\d{7}[0-9A-J]$")
        if not pattern.fullmatch(cif):
            raise EnterpriseManagementException("Invalid CIF format")
        control_num = EnterpriseManager._calculate_cif_control_number(cif)
        EnterpriseManager._validate_cif_control_char(cif[0], cif[8], control_num)
        return True

    @staticmethod
    def _calculate_cif_control_number(cif: str):
        """calculates the control number for a CIF"""
        digits = cif[1:8]
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
        return control_num

    @staticmethod
    def _validate_cif_control_char(first_letter: str, control_char: str, control_num: int):
        """validates the control character of a CIF"""
        letter_map = "JABCDEFGHI"
        if first_letter in ('A', 'B', 'E', 'H'):
            if str(control_num) != control_char:
                raise EnterpriseManagementException("Invalid CIF character control number")
        elif first_letter in ('P', 'Q', 'S', 'K'):
            if letter_map[control_num] != control_char:
                raise EnterpriseManagementException("Invalid CIF character control letter")
        else:
            raise EnterpriseManagementException("CIF type not supported")

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

    def _load_projects(self):
        """loads the projects list from the store file"""
        try:
            with open(PROJECTS_STORE_FILE, "r", encoding="utf-8", newline="") as file:
                return json.load(file)
        except FileNotFoundError:
            return []
        except json.JSONDecodeError as ex:
            raise EnterpriseManagementException("JSON Decode Error - Wrong JSON Format") from ex

    def _save_projects(self, projects_list):
        """saves the projects list to the store file"""
        try:
            with open(PROJECTS_STORE_FILE, "w", encoding="utf-8", newline="") as file:
                json.dump(projects_list, file, indent=2)
        except FileNotFoundError as ex:
            raise EnterpriseManagementException("Wrong file  or file path") from ex
        except json.JSONDecodeError as ex:
            raise EnterpriseManagementException("JSON Decode Error - Wrong JSON Format") from ex

    @staticmethod
    def _validate_budget(budget):
        """validates the budget value and format"""
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
        return budget_float

    @staticmethod
    def _validate_project_fields(project_acronym, project_description, department):
        """validates acronym, description and department fields"""
        if not re.compile(r"^[a-zA-Z0-9]{5,10}").fullmatch(project_acronym):
            raise EnterpriseManagementException("Invalid acronym")
        if not re.compile(r"^.{10,30}$").fullmatch(project_description):
            raise EnterpriseManagementException("Invalid description format")
        if not re.compile(r"(HR|FINANCE|LEGAL|LOGISTICS)").fullmatch(department):
            raise EnterpriseManagementException("Invalid department")

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
        self._validate_project_fields(project_acronym, project_description, department)
        self.validate_starting_date(date)
        self._validate_budget(budget)
        new_project = EnterpriseProject(company_cif=company_cif,
                                        project_acronym=project_acronym,
                                        project_description=project_description,
                                        department=department,
                                        starting_date=date,
                                        project_budget=budget)
        projects_list = self._load_projects()
        for existing_project in projects_list:
            if existing_project == new_project.to_json():
                raise EnterpriseManagementException("Duplicated project in projects list")
        projects_list.append(new_project.to_json())
        self._save_projects(projects_list)
        return new_project.project_id

    def _verify_document_signature(self, document):
        """verifies the cryptographic signature of a document"""
        timestamp_val = document["register_date"]
        doc_datetime = datetime.fromtimestamp(timestamp_val, tz=timezone.utc)
        with freeze_time(doc_datetime):
            doc_obj = ProjectDocument(document["project_id"], document["file_name"])
            if doc_obj.document_signature != document["document_signature"]:
                raise EnterpriseManagementException("Inconsistent document signature")

    def _count_documents_for_date(self, documents_list, date_str):
        """counts valid documents matching a given date"""
        doc_count = 0
        for document in documents_list:
            timestamp_val = document["register_date"]
            doc_date_str = datetime.fromtimestamp(timestamp_val).strftime("%d/%m/%Y")
            if doc_date_str == date_str:
                self._verify_document_signature(document)
                doc_count = doc_count + 1
        return doc_count

    def find_docs(self, date_str):
        """returns the number of valid documents registered on a given date"""
        date_pattern = re.compile(r"^(([0-2]\d|3[0-1])\/(0\d|1[0-2])\/\d\d\d\d)$")
        if not date_pattern.fullmatch(date_str):
            raise EnterpriseManagementException("Invalid date format")
        try:
            datetime.strptime(date_str, "%d/%m/%Y").date()
        except ValueError as ex:
            raise EnterpriseManagementException("Invalid date format") from ex
        try:
            with open(TEST_DOCUMENTS_STORE_FILE, "r", encoding="utf-8", newline="") as file:
                documents_list = json.load(file)
        except FileNotFoundError as ex:
            raise EnterpriseManagementException("Wrong file  or file path") from ex
        doc_count = self._count_documents_for_date(documents_list, date_str)
        if doc_count == 0:
            raise EnterpriseManagementException("No documents found")
        report_entry = {"Querydate": date_str,
                        "ReportDate": datetime.now(timezone.utc).timestamp(),
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