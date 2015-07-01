import xml.etree.ElementTree as ET

from suds.client import Client

# This comment should be...? Not on the current branch


class Cherwell_Soap:
    def __init__(self, username, password, apilink):
        self.client = Client(apilink)
        self.username = username
        self.password = password
        if self.login():
            print "Logged in"
        else:
            print self.get_last_error()

    def login(self):
        return self.client.service.Login(self.username, self.password)

    def logout(self):
        return self.client.service.Logout()

    def get_last_error(self):
        return self.client.service.GetLastError()

    def is_login_error(self):
        if self.get_last_error():
            if 'not logged in' in self.get_last_error():
                return True
        return False

    def run_soap_cmd(self, cmd, *params):
        result = cmd(*params)
        if self.is_login_error():
            result = cmd(*params)
        else:
            if self.get_last_error() is not None and "Please login" not in self.get_last_error():
                print self.get_last_error()
        return result

    def get_business_object_by_public_id(self, business_object_type, object_id):
        return self.run_soap_cmd(self.client.service.GetBusinessObjectByPublicId, business_object_type, object_id)

    def get_business_object(self, business_object_type, object_id):
        return self.run_soap_cmd(self.client.service.GetBusinessObject, business_object_type, object_id)

    def query_by_field_value(self, business_object_type, field, value):
        return self.run_soap_cmd(self.client.service.QueryByFieldValue, business_object_type, field, value)

    def query_by_stored_query(self, business_object_type, query_name, scope='Global'):
        return self.run_soap_cmd(self.client.service.QueryByStoredQueryWithScope, business_object_type, query_name, scope, self.username)

    def update_business_object(self, object_type, object_id, update_xml):
        return self.run_soap_cmd(self.client.service.UpdateBusinessObject, object_type, object_id, update_xml)

    def update_business_object_by_pubid(self, object_type, object_id, update_xml):
        return self.run_soap_cmd(self.client.service.UpdateBusinessObjectByPublicId, object_type, object_id, update_xml)

    def create_business_object(self, business_object_type, business_object_xml):
        return self.run_soap_cmd(self.client.service.CreateBusinessObject, business_object_type, business_object_xml)

    def add_attachment_to_record(self, business_object_type, object_record_id, attachment_name, attachment_data):
        return self.run_soap_cmd(self.client.service.AddAttachmentToRecord, business_object_type, object_record_id,
                                                         attachment_name, attachment_data.encode("base64"))
    def get_business_object_def(self, business_object_type):
        return self.run_soap_cmd(self.client.service.GetBusinessObjectDefinition, business_object_type)

    def get_action_params(self, business_object_type, recid, action):
        return self.run_soap_cmd(self.client.service.GetParametersForAction, business_object_type, recid, action)

class Cherwell:
    def __init__(self, username, password, apilink):
        self.cherwell = Cherwell_Soap(username, password, apilink)

    def logout(self):
        self.cherwell.logout()

    def login(self):
        self.cherwell.login()

    def get_bus_obj_by_publicid(self, business_object_type, object_id):
        """
        Gets a business object by its public id

        :param business_object_type: The type of business object to get
        :type business_object_type: str
        :param object_id: The public id of the object
        :type object_id: str
        :return: business object
        :rtype: str
        """
        try:
            business_object_xml = self.cherwell.get_business_object_by_public_id(business_object_type, object_id)
            return business_object_xml
        except Exception as e:
            print e.message


    def get_bus_obj_by_recid(self, business_object_type, object_id):
        """
        Gets a business object by its record id

        :param business_object_type: the type of business object to get
        :type business_object_type: str
        :param object_id: The record id of the object
        :type object_id: str
        :return: business object
        :rtype: str
        """
        try:
            business_object_xml = self.cherwell.get_business_object(business_object_type,
                                                                        object_id)
            return business_object_xml

        except Exception as e:
            print e.message

    def query_by_field_value(self, business_object_type, field, value, wantpubid=True):
        """
        Query for business objects that match a specific field

        :param business_object_type: Type of business object to query for
        :type business_object_type: str
        :param field: Field to match
        :type field: str
        :param value: Value of field to match
        :type value: str
        :param wantpubid: Whether or not you want a public id as a result
        :type wantpubid: bool
        :return: query results
        :rtype: list
        """
        try:
            query_result = self.cherwell.query_by_field_value(business_object_type, field, value)
            parsed_query_result = self.parse_query(query_result, wantpubid)

            return parsed_query_result
        except:
            print "Query failed"
            return []

    def query_by_stored_query(self, business_object_type, query_name, scope='Global', wantpubid=True):
        """
        Query for business objects that match a specific stored query

        :param business_object_type: Type of business object to query for
        :param query_name: The name of the query in the system
        :param scope: Where the query is stored in the system
        :param wantpubid: Whether or not you want a public id as a result
        :return: query results
        :rtype: list
        """
        try:
            query_result = self.cherwell.query_by_stored_query(business_object_type, query_name, scope)
            parsed_query_result = self.parse_query(query_result, wantpubid)

            return parsed_query_result
        except:
            print "Query Failed"
            return []

    def parse_query(self, query_result, wantpubid=False):
        parsed_result_list = []
        root = ET.fromstring(query_result)
        try:
            for Record in root.iter("Record"):
                business_object_id = Record.get('RecId') if not wantpubid else Record.text
                parsed_result_list.append(business_object_id)
        except:
            for Record in root.getiterator("Record"):
                business_object_id = Record.get('RecId') if not wantpubid else Record.text
                parsed_result_list.append(business_object_id)

        return parsed_result_list

    def update_business_object(self, object_id, object_type, update_xml, givenrecid=True):
        """
        Update a business object's fields

        :param object_id: The id of the object to update
        :type object_id: str
        :param update_object: The object with the updated fields
        :type update_object: BusinessObject
        :param givenrecid: Whether or not object_id is a rec id or not
        :type givenrecid: bool
        :return: result of the update
        :rtype: str
        """
        try:
            if givenrecid:
                update_result = self.cherwell.update_business_object(object_type,
                                                                         object_id,
                                                                         update_xml)
            else:
                update_result = self.cherwell.update_business_object_by_pubid(object_type,
                                                                                   object_id,
                                                                                   update_xml)
            if update_result is False:
                print "Object " + str(object_id) + " failed to update"
            return update_result
        except Exception as e:
            print e.message

    def create_business_object(self, business_object_type, business_object_xml):
        """
        Create a business object on Cherwell according to the business object given

        :param business_object: The business object to make
        :type business_object: BusinessObject
        :return: record id of the created object
        """
        try:

            object_recid = self.cherwell.create_business_object(business_object_type,
                                                                    business_object_xml)
            return object_recid
        except Exception as e:
            print e.message

    def add_attachment_to_record(self, business_object_type, object_record_id,
                                 attachment_name, attachment_data):
        """
        Attach a file to a business object

        :param business_object_type: Type of business object
        :type business_object_type: str
        :param object_record_id: record id of the object to attach to
        :type object_record_id: str
        :param attachment_name: Name of the attachment
        :type attachment_name: str
        :param attachment_data: Data of the attachment
        :type attachment_data: str
        :return: result of attachment
        :rtype: str
        """
        try:
            attachment_result = self.cherwell.add_attachment_to_record(
                business_object_type, object_record_id,
                attachment_name, attachment_data.encode("base64")
            )
            return attachment_result
        except Exception as e:
            print e.message

    def get_bo_ids_matching_fields(self, bo_type, fields, wantPubId=True):
        """
        Get a list of business objects matching the specified fields.

        :param bo_type: The type of business object to search for
        :type bo_type: str
        :param fields: The fields that are desired to match
        :type fields: dict
        :param wantPubId: Whether or not you want a public id as a result
        :type wantPubId: bool
        :return: list of business objects matching the specified fields
        :rtype: list
        """
        results = list()

        for field, value in fields.iteritems():
            results.append(set(self.query_by_field_value(bo_type, field, value, wantPubId)))

        matched_bo = set.intersection(*results)

        return list(matched_bo)

    def get_incidents_of_team(self, team_name):
        """
        Gets the list of incidents that a specified team owns

        :param team_name: The name of the team to find incidents of
        :type team_name: str
        :return: A list of publicIDs for each task that belongs to *team_name*
        :rtype: list

        **Example**:
            Assuming you have already instantiated the Cherwell_Connection class::

                list_of_incidents = cherwell_server.get_incidents_of_team
                                        ("Information Security")

            *list_of_incidents* would be ::

                {112512,124523,653123,123151,110123,110122,...}

            *list_of_incidents* contains the publicIDs of all incidents owned by *team_name* regardless
            of status.

        """

        return self.get_bo_ids_matching_fields("Incident", {'OwnedByTeam': team_name}, wantPubId=True)

    def get_student_by_id(self, student_id, wantpubid=True):
        """
        Gets a student object based on their id

        :param student_id: The ID of the student
        :type student_id: str
        :return: the publicID of the customerObject that represents the student (Their name)
        :rtype: str

        **Example**::

            Cherwell_Connection.get_student_by_id("419472226")

        This would return Nadel, Erik I. (The public ID of their respective customer Object)

        """
        student = self.get_bo_ids_matching_fields("CustomerInternal", {"ID_Number": student_id}, wantpubid)[0]
        return student

    def get_customer_id(self, user_email, wantpubid=True):
        """
        Gets the record or public id of a customer given their email.

        :param user_email: The email of the customer
        :type user_email: str
        :param recid: Whether or not you want the record id of the customer or public ID
        :type recid: bool
        :return: id of the customer object in question
        :rtype: str
        """
        user = self.query_by_field_value("CustomerInternal", "Email", user_email, wantpubid)[0]
        return user
