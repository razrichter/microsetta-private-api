from unittest import TestCase

from werkzeug.exceptions import Unauthorized

from microsetta_private_api.model.account import Account
from microsetta_private_api.model.address import Address
from microsetta_private_api.repo.account_repo import AccountRepo
from microsetta_private_api.repo.admin_repo import AdminRepo
from microsetta_private_api.repo.transaction import Transaction
from microsetta_private_api.admin.admin_impl import validate_admin_access

STANDARD_ACCT_ID = "12345678-bbbb-cccc-dddd-eeeeffffffff"
ADMIN_ACCT_ID = "12345678-1234-1234-1234-123412341234"


class AdminTests(TestCase):
    def setUp(self):
        AdminTests.setup_test_data()

    def tearDown(self):
        AdminTests.teardown_test_data()

    @staticmethod
    def setup_test_data():
        AdminTests.teardown_test_data()

        with Transaction() as t:
            acct_repo = AccountRepo(t)

            acc = Account(STANDARD_ACCT_ID,
                          "foo@baz.com",
                          "standard",
                          "https://MOCKUNITTEST.com",
                          "1234ThisIsNotARealSub",
                          "NotDan",
                          "NotH",
                          Address(
                              "123 Dan Lane",
                              "NotDanville",
                              "CA",
                              12345,
                              "US"
                          ))
            acct_repo.create_account(acc)

            acc = Account(ADMIN_ACCT_ID,
                          "bar@baz.com",
                          "admin",
                          "https://MOCKUNITTEST.com",
                          "5678ThisIsNotARealAdminSub",
                          "Dan",
                          "H",
                          Address(
                              "456 Dan Lane",
                              "Danville",
                              "CA",
                              12345,
                              "US"
                          ))
            acct_repo.create_account(acc)
            t.commit()

    @staticmethod
    def teardown_test_data():
        with Transaction() as t:
            acct_repo = AccountRepo(t)
            acct_repo.delete_account(STANDARD_ACCT_ID)
            acct_repo.delete_account(ADMIN_ACCT_ID)
            t.commit()

    def test_validate_admin_access(self):
        token_info_std = {
            "iss": "https://MOCKUNITTEST.com",
            "sub": "1234ThisIsNotARealSub",
        }
        token_info_admin = {
            "iss": "https://MOCKUNITTEST.com",
            "sub": "5678ThisIsNotARealAdminSub",
        }
        token_info_no_such_issuer = {
            "iss": "qqNoZuchIzzuerpp",
            "sub": "NoZuchZub"
        }

        validate_admin_access(token_info_admin)
        try:
            validate_admin_access(token_info_std)
            self.fail("Should have thrown unauthorized")
        except Unauthorized:
            pass
        try:
            validate_admin_access(token_info_no_such_issuer)
            self.fail("Should have thrown unauthorized")
        except Unauthorized:
            pass

    def test_search_barcode(self):
        with Transaction() as t:
            # TODO FIXME HACK:  Need to build mock barcodes rather than using
            #  these fixed ones
            admin_repo = AdminRepo(t)
            diag = admin_repo.retrieve_diagnostics_by_barcode('000038448')
            self.assertIsNotNone(diag['barcode'])
            self.assertIsNone(diag['account'])
            self.assertIsNone(diag['source'])
            self.assertIsNotNone(diag['sample'])
            self.assertGreater(len(diag['barcode_info']), 0)

            diag = admin_repo.retrieve_diagnostics_by_barcode('000033903')
            self.assertIsNotNone(diag['barcode'])
            self.assertIsNone(diag['account'])
            self.assertIsNone(diag['source'])
            self.assertIsNone(diag['sample'])
            self.assertGreater(len(diag['barcode_info']), 0)

            # Uhh, should this return a 404 not found or just an empty
            # diagnostic object...?
            diag = admin_repo.retrieve_diagnostics_by_barcode('NotABarcode :D')
            self.assertIsNotNone(diag['barcode'])
            self.assertIsNone(diag['account'])
            self.assertIsNone(diag['source'])
            self.assertIsNone(diag['sample'])
            self.assertEqual(len(diag['barcode_info']), 0)

    def test_create_kits(self):
        with Transaction() as t:
            admin_repo = AdminRepo(t)

            with self.assertRaisesRegex(KeyError, "does not exist"):
                admin_repo.create_kits(5, 3, '', ['foo', 'bar'])

            non_tmi = admin_repo.create_kits(5, 3, '',
                                             ['Project - /J/xL_|Eãt'])
            self.assertEqual(['created', ], list(non_tmi.keys()))
            self.assertEqual(len(non_tmi['created']), 5)
            for obj in non_tmi['created']:
                self.assertEqual(len(obj['sample_barcodes']), 3)
                self.assertEqual({'kit_id', 'kit_uuid', 'sample_barcodes'},
                                 set(obj))

            # should not be present in the ag tables
            non_tmi_kits = [k['kit_id'] for k in non_tmi['created']]
            with t.cursor() as cur:
                cur.execute("SELECT supplied_kit_id "
                            "FROM ag.ag_kit "
                            "WHERE supplied_kit_id IN %s",
                            (tuple(non_tmi_kits), ))
                observed = cur.fetchall()
                self.assertEqual(len(observed), 0)

            tmi = admin_repo.create_kits(4, 2, 'foo',
                                         ['American Gut Project'])
            self.assertEqual(['created', ], list(tmi.keys()))
            self.assertEqual(len(tmi['created']), 4)
            for obj in tmi['created']:
                self.assertEqual(len(obj['sample_barcodes']), 2)
                self.assertEqual({'kit_id', 'kit_uuid', 'sample_barcodes'},
                                 set(obj))
                self.assertTrue(obj['kit_id'].startswith('foo_'))

            # should be present in the ag tables
            tmi_kits = [k['kit_id'] for k in tmi['created']]
            with t.cursor() as cur:
                cur.execute("SELECT supplied_kit_id "
                            "FROM ag.ag_kit "
                            "WHERE supplied_kit_id IN %s",
                            (tuple(tmi_kits), ))
                observed = cur.fetchall()
                self.assertEqual(len(observed), 4)
