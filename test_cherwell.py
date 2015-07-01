from unittest import TestCase
from cherwell import Cherwell


__author__ = 'jptingle'

cherwell_object = Cherwell('', '', '')

test_object_xml = '<BusinessObject Name="Incident"><FieldList><Field Name="Category">Information Security</Field><Field Name="SubCategory">Reported Problems</Field><Field Name="Service">Internal Operations</Field><Field Name="Review">FALSE</Field><Field Name="Summary">Unit Test</Field><Field Name="ReviewByDeadline">0001-01-01</Field><Field Name="Status">Assigned</Field><Field Name="CustomerTypeID">93405caa107c376a2bd15c4c8885a900be316f3a72</Field><Field Name="CustomerDisplayName">unitTest</Field><Field Name="Description">Unit Test Do not remove</Field><Field Name="OwnedByTeam">Information Security</Field><Field Name="TempDefaultTeam">Information Security</Field><Field Name="CustomerRecID">93df741079f5003c7dfab84816b8d00de6eef64fa8</Field><Field Name="IncidentReview">FALSE</Field></FieldList></BusinessObject>'
test_object_updatexml = '<BusinessObject Name="Incident"><FieldList><Field Name="Description">Unit Test Do not remove (UPDATE FLAG)</Field></FieldList></BusinessObject>'

test_object_recid = cherwell_object.create_business_object('Incident', test_object_xml)

found_xml = cherwell_object.get_bus_obj_by_recid('Incident', test_object_recid)
test_object_pubid = found_xml[found_xml.find('IncidentID')+12:found_xml.find('IncidentID')+18]
print test_object_pubid

query_result = cherwell_object.query_by_field_value('Incident', 'Category', 'Information Security', wantpubid=True)
queryPassed = True if query_result is not None else False


class TestCherwell(TestCase):

    def test_login(self):
        #obviously we logged in if we made a business object...
        self.assertIsNotNone(test_object_recid)

    # THIS TEST MUST BE RUN SECOND
    def test_create_business_object(self):
        self.assertIsNotNone(test_object_recid)

    def test_get_bus_obj_by_recid(self):
        self.assertIsNotNone(found_xml)

    def test_get_bus_obj_by_publicid(self):
        retrieved_object = cherwell_object.get_bus_obj_by_publicid('Incident', test_object_pubid)
        self.assertIsNotNone(retrieved_object)

    def test_query_by_field_value(self):
        self.assertIn(test_object_pubid, query_result)

    def test_query_by_stored_query(self):
        self.assertTrue(queryPassed)

    def test_parse_query(self):
        self.assertTrue(queryPassed)

    def test_update_business_object(self):
        result = cherwell_object.update_business_object(test_object_pubid, 'Incident', test_object_updatexml, givenrecid=False)
        self.assertTrue(result)

    def test_add_attachment_to_record(self):
        result = cherwell_object.add_attachment_to_record('Incident',test_object_recid,'test.txt','blahblahblahblahblah')
        self.assertIsNotNone(result)
