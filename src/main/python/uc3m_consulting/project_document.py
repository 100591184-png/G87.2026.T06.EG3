"""Contains the class ProjectDocument"""
import hashlib
from uc3m_consulting.enterprise_project import get_current_timestamp


class ProjectDocument():
    """Class representing a project document"""

    def __init__(self, project_id: str, file_name):
        self.__alg = "SHA-256"
        self.__type = "PDF"
        self.__project_id = project_id
        self.__file_name = file_name
        self.__register_date = get_current_timestamp()

    def to_json(self):
        """returns the object data in json format"""
        return {"alg": self.__alg,
                "type": self.__type,
                "project_id": self.__project_id,
                "file_name": self.__file_name,
                "register_date": self.__register_date,
                "document_signature": self.document_signature}

    def __signature_string(self):
        """Composes the string to be used for generating the document signature"""
        return "{alg:" + str(self.__alg) + ",typ:" + str(self.__type) + ",project_id:" + \
               str(self.__project_id) + ",file_name:" + str(self.__file_name) + \
               ",register_date:" + str(self.__register_date) + "}"

    @property
    def project_id(self):
        """Property representing the project id"""
        return self.__project_id

    @project_id.setter
    def project_id(self, value):
        self.__project_id = value

    @property
    def file_name(self):
        """Property representing the file name"""
        return self.__file_name

    @file_name.setter
    def file_name(self, value):
        self.__file_name = value

    @property
    def register_date(self):
        """Property representing the registration date"""
        return self.__register_date

    @register_date.setter
    def register_date(self, value):
        self.__register_date = value

    @property
    def document_signature(self):
        """Returns the sha256 signature of the document"""
        return hashlib.sha256(self.__signature_string().encode()).hexdigest()