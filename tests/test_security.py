"""Checks for credential configuration and private-page authentication."""

import os
import io
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest.mock import patch

import security
from security import (
    authenticate,
    credentials_configured,
    get_admin_credentials,
    hash_password,
    login_allowed,
    verify_password,
)


class PasswordHashTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.password = "fixture-only-padel-123"
        cls.stored_hash = hash_password(cls.password)

    def test_correct_password_and_wrong_password(self):
        self.assertTrue(verify_password(self.password, self.stored_hash))
        self.assertFalse(verify_password("wrong-fixture-password", self.stored_hash))

    def test_random_salts_and_expected_format(self):
        second_hash = hash_password(self.password)
        self.assertNotEqual(second_hash, self.stored_hash)
        self.assertRegex(
            second_hash, r"^pbkdf2_sha256\$600000\$[0-9a-f]{32}\$[0-9a-f]{64}$"
        )
        self.assertTrue(verify_password(self.password, second_hash))

    def test_unicode_password(self):
        password = "raquette-démo-🎾-密码"
        self.assertTrue(verify_password(password, hash_password(password)))

    def test_invalid_hashes_fail_without_errors(self):
        algorithm, iterations, salt, digest = self.stored_hash.split("$")
        invalid_hashes = [
            None,
            42,
            "",
            "not-a-password-hash",
            self.stored_hash + "$extra",
            f"unknown${iterations}${salt}${digest}",
            f"{algorithm}$999999999999999999999${salt}${digest}",
            f"{algorithm}$0${salt}${digest}",
            f"{algorithm}$600000${salt[:-1]}${digest}",
            f"{algorithm}$600000${'z' * 32}${digest}",
            f"{algorithm}$600000${salt}${digest[:-1]}",
            f"{algorithm}$600000${salt}${'x' * 64}",
        ]
        for value in invalid_hashes:
            with self.subTest(value=value):
                self.assertFalse(verify_password(self.password, value))

    def test_invalid_password_inputs_fail_closed(self):
        self.assertFalse(verify_password(None, self.stored_hash))
        self.assertFalse(verify_password("\ud800", self.stored_hash))


class CredentialTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.password = "fixture-only-padel-123"
        cls.stored_hash = hash_password(cls.password)

    def setUp(self):
        self.environ = patch.dict(os.environ, {}, clear=True)
        self.environ.start()
        self.addCleanup(self.environ.stop)

    def test_no_credentials_means_no_access(self):
        self.assertEqual(get_admin_credentials(), (None, None))
        self.assertFalse(credentials_configured())
        self.assertFalse(authenticate(""))
        self.assertFalse(authenticate("anything"))

    def test_environment_credentials_override_secret_values(self):
        with patch.dict(
            os.environ,
            {
                "RACKET_GO_ADMIN_PASSWORD_HASH": "env-hash",
                "RACKET_GO_ADMIN_PASSWORD": "env-password",
            },
        ):
            credentials = get_admin_credentials(
                {
                    "RACKET_GO_ADMIN_PASSWORD_HASH": "secret-hash",
                    "RACKET_GO_ADMIN_PASSWORD": "secret-password",
                }
            )
            self.assertEqual(credentials, ("env-hash", "env-password"))

    def test_secrets_can_supply_credentials(self):
        configuration = {"RACKET_GO_ADMIN_PASSWORD": "fixture-password-🎾"}
        self.assertTrue(credentials_configured(configuration))
        self.assertTrue(authenticate("fixture-password-🎾", configuration))
        self.assertFalse(authenticate("wrong-password", configuration))

    def test_environment_password_authentication(self):
        with patch.dict(os.environ, {"RACKET_GO_ADMIN_PASSWORD": "fixture-password"}):
            self.assertTrue(authenticate("fixture-password"))
            self.assertFalse(authenticate("wrong-password"))

    def test_hash_takes_precedence_over_plaintext_password(self):
        configuration = {
            "RACKET_GO_ADMIN_PASSWORD_HASH": self.stored_hash,
            "RACKET_GO_ADMIN_PASSWORD": "another-fixture-password",
        }
        self.assertTrue(authenticate(self.password, configuration))
        self.assertFalse(authenticate("another-fixture-password", configuration))

    def test_malformed_hash_never_falls_back_to_plaintext(self):
        configuration = {
            "RACKET_GO_ADMIN_PASSWORD_HASH": "malformed",
            "RACKET_GO_ADMIN_PASSWORD": "fixture-password",
        }
        self.assertFalse(authenticate("fixture-password", configuration))

    def test_empty_or_nonstring_values_are_not_credentials(self):
        self.assertEqual(
            get_admin_credentials(
                {"RACKET_GO_ADMIN_PASSWORD_HASH": 42, "RACKET_GO_ADMIN_PASSWORD": ""}
            ),
            (None, None),
        )
        self.assertFalse(authenticate(None))


class LoginRateLimitTests(unittest.TestCase):
    def test_five_recent_attempts_block_login(self):
        attempts = [960.0, 970.0, 980.0, 990.0, 999.0]
        self.assertFalse(login_allowed(attempts, now=1000.0))
        self.assertTrue(login_allowed(attempts[:-1], now=1000.0))

    def test_expired_attempts_stop_counting(self):
        self.assertTrue(login_allowed([690.0, 700.0, 710.0, 720.0, 730.0], now=1000.0))
        self.assertTrue(login_allowed([], now=1000.0))

    def test_default_clock(self):
        with patch("security.time.time", return_value=1000.0):
            self.assertFalse(login_allowed([999.0] * 5))

    def test_invalid_limits_are_rejected(self):
        with self.assertRaises(ValueError):
            login_allowed([], max_attempts=0)
        with self.assertRaises(ValueError):
            login_allowed([], window_seconds=0)


class PasswordHashCommandTests(unittest.TestCase):
    def test_command_prints_only_the_hash_to_stdout(self):
        output = io.StringIO()
        password = "fixture-command-password"
        with patch("getpass.getpass", side_effect=[password, password]):
            with redirect_stdout(output):
                result = security._main()
        self.assertEqual(result, 0)
        self.assertNotIn(password, output.getvalue())
        self.assertTrue(verify_password(password, output.getvalue().strip()))

    def test_command_rejects_short_and_mismatched_passwords(self):
        for values in (["short"], ["fixture-password", "different-password"]):
            with self.subTest(values=values):
                output = io.StringIO()
                with patch("getpass.getpass", side_effect=values):
                    with redirect_stdout(output), redirect_stderr(io.StringIO()):
                        result = security._main()
                self.assertEqual(result, 1)
                self.assertEqual(output.getvalue(), "")


if __name__ == "__main__":
    unittest.main()
