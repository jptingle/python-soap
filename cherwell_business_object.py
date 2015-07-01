import xml.etree.ElementTree as ET
import time
import datetime

import cherwellconstants

class BusinessObject(object):
    """
    The BusinessObject class is the basis for any business object that comes from the Cherwell server.
    The base class is just a generic business object and can operate on any object given its record
    id and type. Fields can be set and retrieved with this class. Any changes made to the object will be uploaded to
    Cherwell to reflect changes. Any fields requested from the object that are not available locally will be downloaded
    from Cherwell and cached appropriately.
    """
    def __init__(self, type, id, cherwell_instance):
        self.type = type
        self.id = id
        self.has_pubid = False
        self.fields = dict()
        self.cherwell_connection = cherwell_instance

    def __eq__(self, other):
        try:
            return other['RecID'] == self.fields['RecID']
        except KeyError as e:
            print e.message

    def import_xml(self, business_object_xml):
        """
        Create a business object from the given xml

        :param type: the type of business object given
        :type type: str
        :param business_object_xml: xml data of the business object
        :type business_object_xml: str
        :return: parsed business object
        :rtype: BusinessObject
        """
        try:
            xml_root = ET.fromstring(business_object_xml.encode('ascii', 'ignore'))
            fields = xml_root.find("FieldList")
            for children in fields:
                field_name = children.get("Name")
                field_value = children.text
                self.fields[field_name] = field_value

        except ET.ParseError as e:
            print e.message

    def push_update_to_cherwell(self, field_dict):
        """
        Push the specified fields to Cherwell to be updated with the business object.

        :param field_dict: The fields to change
        :type field_dict: dict
        :return: None
        """
        update_xml = BusinessObjectFactory.generate_object_xml(self.type, field_dict)
        userecid = False if self.has_pubid else True
        self.cherwell_connection.update_business_object(self.id, self.type, update_xml, userecid)

    def set_fields(self, field_dict):
        try:
            for field, value in field_dict.iteritems():
                self.fields[field] = value

            self.push_update_to_cherwell(field_dict)
        except Exception as e:
            print e.message

    def set_field(self, field_name, value):
        try:
            self.fields[field_name] = value

            self.push_update_to_cherwell({field_name: value})
        except KeyError as e:
            print e.message

    def get_fields(self, field_names):
        field_values = []
        try:
            for field in field_names:
                field_values.append(self.__getitem__(field))
            return field_values
        except KeyError as e:
            print e.message

    def get_latest_from_server(self):
        """
        Gets the latest version of the business object from cherwell
        :return: None
        """
        bo_from_server = self.cherwell_connection.get_bus_obj_by_publicid(self.type, self.id) if self.has_pubid else \
            self.cherwell_connection.get_bus_obj_by_recid(self.type, self.id)
        self.import_xml(bo_from_server)

    def __getitem__(self, item):
        """
        Gets the specified field value of this object
        :param item: The field name to get a value for
        :type item: str
        :return: field value
        :rtype: str
        """
        try:
            return self.fields[item]
        except:
            try:
                self.get_latest_from_server()
                return self.fields[item]
            except:
                print "Error retrieving field - " + str(item)

    def __setitem__(self, key, value):
        self.set_field(key, value)

    def to_xml(self):
        """
        Returns the XML version of the business object

        :return: XML of business object
        :rtype: str
        """

        self.get_latest_from_server()

        bo_xml_root = ET.Element("BusinessObject")
        bo_xml_root.set("Name", self.type)
        field_list = ET.SubElement(bo_xml_root, "FieldList")

        # Add fields
        for field in self.fields:
            _field = ET.SubElement(field_list, "Field")
            _field.set("Name", field)
            _field.text = self.fields[field]

        bo_xml_string = ET.tostring(bo_xml_root)

        return bo_xml_string

    def get_related_bo_ids(self, relatedtype, wantpubid=True):
        """
        Get business objects related to this business object.

        :param relatedtype: Type to search for
        :type relatedtype: str
        :param wantpubid: whether you want the public ids of the related objects
        :type wantpubid: bool
        :return: the ids of objects related to this object
        :rtype: list
        """
        parent_rec_id = self['RecID']
        related_bo_ids = self.cherwell_connection.get_bo_ids_matching_fields(relatedtype,
                                                                    {"ParentRecID": parent_rec_id},
                                                                    wantpubid)
        return related_bo_ids

    def attach_file(self, filename, filepath):
        """
        Attach a file to the business object

        :param filename: name of attachment
        :type filename: str
        :param filepath: the path to the file
        :type filepath: str
        :return: None
        """
        fout = open(filepath, 'rb')
        data = fout.read()
        fout.close()

        data = data.encode("base64")
        return self.cherwell_connection.add_attachment_to_record(self.type, self['RecID'], filename, data)


class Incident(BusinessObject):
    """
    Incident Object
    :
    """
    def __init__(self, incident_id, cherwell_connection):
        super(Incident, self).__init__('Incident', incident_id, cherwell_connection)
        self.has_pubid = True

    def get_task_ids(self):
        """
        Retrieve the ids of tasks attached to the incident.

        :return: list of tasks attached
        :rtype: list
        """
        return self.get_related_bo_ids('Task')

    def set_pending(self, reason):
        """
        Set an incident to pending with a reason

        :param reason: reason for pending
        :type reason: str
        :return: None
        """
        pending_fields = {'Status': 'Pending',
                          'PendingReason': reason,
                          'PendingPreviousStatus': 'In Progress'}
        self.set_fields(pending_fields)

    def set_deadline(self, day_delta):
        """
        Set the deadline of an incident by the difference in today's date

        :param day_delta: Number of days from now to set the deadline to
        :type day_delta: int
        :return: None
        """
        basedate = time.strftime("%Y-%m-%d")
        date = datetime.datetime.strptime(basedate, "%Y-%m-%d")
        deadline = date + datetime.timedelta(days=day_delta)

        self['ReviewByDeadline'] = str(deadline.__format__('%Y-%m-%d'))

    def set_customer(self, email):
        """
        Set the customer of an incident based on the customer's email in the system

        :param email: email of the customer
        :type email: str
        :return: None
        """
        customer_recid = self.cherwell_connection.get_customer_id(email, wantpubid=False)
        customer_display_name = self.cherwell_connection.get_customer_id(email)
        customer_fields = {'CustomerRecID': customer_recid,
                           'CustomerDisplayName': customer_display_name,
                           'CustomerTypeID': '93405caa107c376a2bd15c4c8885a900be316f3a72'}
        self.set_fields(customer_fields)

    def assign(self, assigned_team):
        """
        Assign an incident to a specified team

        :param assigned_team: the team to assign the incident to
         :type assigned_team: str
        :return: None
        """
        assign_fields = {'Status': 'Assigned',
                         'OwnedByTeam': assigned_team,
                         'TempDefaultTeam': assigned_team}

        # Fields are set twice because sometimes cherwell does not process the first request
        for x in range(0, 2):
            self.set_fields(assign_fields)


    def is_status(self, status):
        """
        Whether or not the incident matches the given status

        :param status: status to check for
        :type status: str
        :return: Whether or not the status matched
        :rtype: bool
        """
        return self['Status'] in status

    def get_infosecspecifics_form(self):
        """
        Get the information security specifics form for the incident

        :return: the business object for the specifics form
        :rtype: SpecificsInformationSecurity
        """
        related_bo = self.get_related_bo_ids('SpecificsInformationSecurity', wantpubid=False)
        form_id = related_bo[0]
        return SpecificsInformationSecurity(form_id, self.cherwell_connection)


class SpecificsInformationSecurity(BusinessObject):
    """

    """
    def __init__(self, id, cherwell_connection):
        super(SpecificsInformationSecurity, self).__init__('SpecificsInformationSecurity', id, cherwell_connection)


class Task(BusinessObject):
    """

    """
    def __init__(self, id, cherwell_connection):
        super(Task, self).__init__('Task', id, cherwell_connection)
        self.has_pubid = True


class JournalHistory(BusinessObject):
    """

    """
    def __init__(self, recid, cherwell_connection):
        super(JournalHistory, self).__init__('JournalHistory', recid, cherwell_connection)


class JournalTeamNote(BusinessObject):
    """

    """
    def __init__(self, recid, cherwell_connection):
        super(JournalTeamNote, self).__init__('JournalTeamNote', recid, cherwell_connection)


class Customer(BusinessObject):
    """

    """
    def __init__(self, customerid, cherwell_connection, givenrecid=False):
        if not givenrecid:
            self.customer_id = self.cherwell_connection.get_customer_id(customerid)
            super(Customer, self).__init__('CustomerInternal', self.customer_id, cherwell_connection)
            self.has_pubid = True
            self.email = customerid
        else:
            super(Customer, self).__init__('CustomerInternal', customerid, cherwell_connection)
            self.has_pubid = False
            self.email = self['Email']

class ConfigComputer(BusinessObject):
    def __init__(self, assettag, cherwell_connection):
        self.has_pubid = True
        super(ConfigComputer, self).__init__('ConfigComputer', assettag, cherwell_connection)

class DriveInfo(BusinessObject):
    def __init__(self, recid, cherwell_connection):
        self.has_pubid = False
        super(DriveInfo, self).__init__('DriveInfo', recid, cherwell_connection)

class BusinessObjectFactory:
    """
    This is where business objects are created. You can create any business object with the create_business_object method,
    but the predefined object creations are there for convienence of the api user.
    """
    def __init__(self, cherwell_connection):
        self.cherwell_connection = cherwell_connection

    @staticmethod
    def generate_object_xml(botype, field_dict):
        """
        Generate the XML for the creation/update of a business object

        :param botype: Type of object to generate
        :type botype: str
        :param field_dict: dictionary of fields for the update/creation
        :type field_dict: dict
        :return: the XML string of the object
        :rtype: dict
        """
        bo_xml_root = ET.Element("BusinessObject")
        bo_xml_root.set("Name", botype)
        field_list = ET.SubElement(bo_xml_root, "FieldList")

        # Add fields
        for field in field_dict:
            _field = ET.SubElement(field_list, "Field")
            _field.set("Name", field)
            _field.text = field_dict[field]

        bo_xml_string = ET.tostring(bo_xml_root)

        return bo_xml_string


    def create_business_object(self, type, field_dict):
        """
        Creates a business object and publishes it to cherwell. This is for creating a business object
        that does not have a specific implementation in this library. Otherwise, I recommend using the
        create_bo_of_type function to get better functionality with the object you are working with.

        :param type: The type of business object
        :type type: str
        :param field_dict: The fields to set for the business object
        :type field_dict: dict
        :return: the business object created
        :rtype: BusinessObject
        """
        creation_xml = BusinessObjectFactory.generate_object_xml(type, field_dict)
        recid = self.cherwell_connection.create_business_object(type, creation_xml)
        business_object = BusinessObject(type, recid, self.cherwell_connection)
        business_object.set_fields(field_dict)

        return business_object


    def populate_customer_field(self, customer_email, fields):
        try:
            fields['CustomerDisplayName'] = self.cherwell_connection.get_customer_id(customer_email)
            fields['CustomerTypeID'] = cherwellconstants.CUSTOMER_TYPE_ID
            fields['CustomerRecID'] = self.cherwell_connection.get_customer_id(customer_email, wantpubid=False)
        except:
            fields['CustomerDisplayName'] = customer_email
            fields['CustomerTypeID'] = cherwellconstants.CUSTOMER_TYPE_ID
            fields['CustomerRecID'] = cherwellconstants.DEFAULT_CUSTRECID


    def create_incident(self, customer_email, summary, description,
                        service, category, subcategory, team_owner_name):
        """
        Create an incident with the given parameters.

        :param customer_email: Email of the associated customer
        :type customer_email: str
        :param summary: Summary of the incident
        :type summary: str
        :param description: Description of the incident
        :type description: str
        :param service: The service of the incident <must be one available on the server>
        :type service: str
        :param category: The category of the incident <must be one available on the server>
        :type category: str
        :param subcategory: The subcategory of the incident <must be one available on the server>
        :type subcategory: str
        :param team_owner_name: Owner of the incident
        :type team_owner_name: str
        :return: created incident object
        :rtype: Incident
        """

        fields = {'Summary': summary,
                  'Description': description,
                  'Service': service,
                  'Category': category,
                  'SubCategory': subcategory,
                  'OwnedByTeam': team_owner_name,
                  'Review': 'FALSE',
                  'IncidentReview': 'FALSE',
                  'ReviewByDeadline': '0001-01-01'}

        print "Populating customer field"
        self.populate_customer_field(customer_email, fields)

        print "Calling the business object factory"
        incident = self.create_bo_of_type(Incident, fields, haspubid=True)

        print "Assigning team"
        incident.assign(team_owner_name)

        print "Setting the status"
        incident['Status'] = 'New'
        return incident


    def create_task(self, parent_pubid, team_owner_name, owner_name, task_order, subject, notes, time_to_execute_by="default"):
        """
        Create a task with the given parameters


        :param parent_pubid: The parent public ID to be attached to (Usually the incident ID)
        :type parent_pubid: str
        :param team_owner_name: The team that owns this task
        :type team_owner_name: str
        :param owner_name: The owner of this task
        :type owner_name: str
        :param task_order: The order in which the task is to be done
        :type task_order: integer string
        :param subject: The subject of the task
        :type subject: str
        :param notes: Any notes that are needed to complete the task
        :type notes: str
        :param time_to_execute_by: The date that this task needs to be done by. (YYYY-DD-MM) string
        :type time_to_execute_by: str
        :return: Task BusinessObject
        :rtype: Task
        """
        parent_recid = Incident(parent_pubid, self.cherwell_connection)['RecID']

        params = {"ParentRecID": parent_recid,
                  "OwnedByTeam": team_owner_name,
                  "OwnedBy": owner_name,
                  "TaskOrder": task_order,
                  "Subject": subject,
                  "Notes": notes,
                  "EndDateTime": time_to_execute_by}

        return self.create_bo_of_type(Task, params, haspubid=True)


    def create_journal_entry(self, parent_pubid, changes_made):
        """
        Create a Journal Entry Object

        :param parent_pubid:
        :param changes_made:
        :return: a journal entry object
        """
        parent_recid = Incident(parent_pubid, self.cherwell_connection)['RecID']

        params = {'ParentRecID': parent_recid,
                  'ParentTypeID': cherwellconstants.PARENT_TYPE_ID_INCIDENT,
                  'OwnedBy': 'API Account',
                  'JournalTypeName': cherwellconstants.JOURNAL_HISTORY,
                  'JournalTypeID': cherwellconstants.JOURNAL_HISTORY_TYPE_ID,
                  'MarkedAsRead': 'FALSE',
                  'Details': changes_made}

        return self.create_bo_of_type(JournalHistory, params)


    def create_bo_of_type(self, type, params, haspubid=False, altpub=None):
        """
        Method for creating a BusinessObject that is defined in the *cherwell_business_object* class

        :param type: The BusinessObject derivation (this is NOT a string, it is the ACTUAL type)
        :type type: BusinessObject
        :param params: The parameters for the object
        :type params: dict
        :param haspubid: Whether or not the business object has a public id
        :type haspubid: bool
        :param altpub: The field name for the public id if it is NOT "<BOname>ID"
        :type altpub: str
        :return: the specified BusinessObject derivative requested
        :rtype: BusinessObject
        """
        if type.__name__ is 'BusinessObject':
            print 'BusinessObject is not a type of business object'
            return
        if altpub is None:
            pubid_fieldname = type.__name__ + 'ID'
        else:
            pubid_fieldname = altpub
        created_bo = self.create_business_object(type.__name__, params)
        bo = type(created_bo.id, self.cherwell_connection) if not haspubid else type(created_bo[pubid_fieldname], self.cherwell_connection)
        bo.import_xml(created_bo.to_xml())
        return bo


    def create_team_note(self, parent_pubid, notes):
        """
        Method for creating a TeamNote.

        :param parent_pubid:
        :param notes:
        :return: the team note requested
        """
        parent_recid = Incident(parent_pubid, self.cherwell_connection)['RecID']

        params = {'ParentRecID': parent_recid,
                  'ParentTypeID': cherwellconstants.PARENT_TYPE_ID_INCIDENT,
                  'OwnedBy': "API Account",
                  'JournalTypeName': cherwellconstants.JOURNAL_TEAM_NOTE,
                  'JournalTypeID': cherwellconstants.JOURNAL_TEAM_NOTE_TYPEID,
                  'MarkedAsRead': 'FALSE',
                  'Details': 'private',
                  'TeamNotes': notes}

        return self.create_bo_of_type(JournalTeamNote, params)



    def create_business_object_from_xmlstring(self, type, bo_xml_string):
        """
        Create a business object for internal use given an xml string

        :param type: The type of business object
        :param bo_xml_string: The xml string for the business object
        :return: the business object created
        :rtype: BusinessObject
        """
        business_object = BusinessObject(type, None, self.cherwell_connection)
        business_object.import_xml(bo_xml_string)
        return business_object


# if __name__ == '__main__':
#     # Used for  generating a unit test ticket
#     BusinessObjectFactory = BusinessObjectFactory(None)
#     fields = {'Summary': 'Unit Test',
#               'Description': 'Unit Test Do not remove',
#               'Service': 'Internal Operations',
#               'Category': 'Information Security',
#               'SubCategory': 'Reported Problems',
#               'OwnedByTeam': 'Information Security',
#               'Review': 'FALSE',
#               'IncidentReview': 'FALSE',
#               'ReviewByDeadline': '0001-01-01',
#               'TempDefaultTeam': 'Information Security',
#               'Status': 'Assigned',
#               'CustomerDisplayName': 'test@test.com',
#               'CustomerTypeID': "93405caa107c376a2bd15c4c8885a900be316f3a72",
#               'CustomerRecID': "93df741079f5003c7dfab84816b8d00de6eef64fa8"}
#     print BusinessObjectFactory.generate_object_xml('Incident',fields)