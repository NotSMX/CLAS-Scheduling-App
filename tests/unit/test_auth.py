"""
Unit tests for website/auth.py
Tests pure functions in isolation with mocked dependencies.
"""
import pytest
from website.auth import get_role_from_email


class TestGetRoleFromEmail:
    """Unit tests for get_role_from_email() helper function"""

    def test_admin_email_from_config(self, monkeypatch):
        """Test that emails in ADMIN_EMAILS config return 'admin' role"""
        class MockApp:
            config = {
                "ADMIN_EMAILS": ["boss@colby.edu", "ceo@colby.edu"],
                "FACULTY_EMAILS": []
            }
        
        monkeypatch.setattr("website.auth.current_app", MockApp)
        
        assert get_role_from_email("boss@colby.edu") == "admin"
        assert get_role_from_email("ceo@colby.edu") == "admin"
        assert get_role_from_email("BOSS@colby.edu") == "admin"  # Case insensitive

    def test_faculty_email_from_config(self, monkeypatch):
        """Test that emails in FACULTY_EMAILS config return 'faculty' role"""
        class MockApp:
            config = {
                "ADMIN_EMAILS": [],
                "FACULTY_EMAILS": ["prof@colby.edu", "teacher@colby.edu"]
            }
        
        monkeypatch.setattr("website.auth.current_app", MockApp)
        
        assert get_role_from_email("prof@colby.edu") == "faculty"
        assert get_role_from_email("teacher@colby.edu") == "faculty"
        assert get_role_from_email("PROF@colby.edu") == "faculty"  # Case insensitive

    def test_colby_email_without_numbers_returns_faculty(self, monkeypatch):
        """Test that @colby.edu emails without numbers default to 'faculty'"""
        class MockApp:
            config = {"ADMIN_EMAILS": [], "FACULTY_EMAILS": []}
        
        monkeypatch.setattr("website.auth.current_app", MockApp)
        
        assert get_role_from_email("john@colby.edu") == "faculty"
        assert get_role_from_email("jane.doe@colby.edu") == "faculty"
        assert get_role_from_email("professor@colby.edu") == "faculty"

    def test_colby_email_with_numbers_returns_none(self, monkeypatch):
        """Test that @colby.edu emails with numbers (students) return None"""
        class MockApp:
            config = {"ADMIN_EMAILS": [], "FACULTY_EMAILS": []}
        
        monkeypatch.setattr("website.auth.current_app", MockApp)
        
        assert get_role_from_email("john123@colby.edu") is None
        assert get_role_from_email("jane4@colby.edu") is None
        assert get_role_from_email("1234@colby.edu") is None
        assert get_role_from_email("abc1def@colby.edu") is None

    def test_non_colby_email_returns_none(self, monkeypatch):
        """Test that non-@colby.edu emails return None"""
        class MockApp:
            config = {"ADMIN_EMAILS": [], "FACULTY_EMAILS": []}
        
        monkeypatch.setattr("website.auth.current_app", MockApp)
        
        assert get_role_from_email("user@gmail.com") is None
        assert get_role_from_email("prof@harvard.edu") is None
        assert get_role_from_email("admin@company.com") is None

    def test_empty_and_none_emails(self, monkeypatch):
        """Test edge cases: None, empty string, whitespace"""
        class MockApp:
            config = {"ADMIN_EMAILS": [], "FACULTY_EMAILS": []}
        
        monkeypatch.setattr("website.auth.current_app", MockApp)
        
        assert get_role_from_email(None) is None
        assert get_role_from_email("") is None
        assert get_role_from_email("   ") is None

    def test_email_normalization(self, monkeypatch):
        """Test that emails are normalized (lowercase, stripped)"""
        class MockApp:
            config = {
                "ADMIN_EMAILS": ["admin@colby.edu"],
                "FACULTY_EMAILS": []
            }
        
        monkeypatch.setattr("website.auth.current_app", MockApp)
        
        assert get_role_from_email("  ADMIN@COLBY.EDU  ") == "admin"
        assert get_role_from_email("Admin@Colby.Edu") == "admin"
        assert get_role_from_email("\tADMIN@colby.edu\n") == "admin"

    def test_admin_priority_over_faculty(self, monkeypatch):
        """Test that admin emails take precedence over faculty"""
        class MockApp:
            config = {
                "ADMIN_EMAILS": ["boss@colby.edu"],
                "FACULTY_EMAILS": ["boss@colby.edu"]  # Same email in both
            }
        
        monkeypatch.setattr("website.auth.current_app", MockApp)
        
        # Admin check happens first, so should return 'admin'
        assert get_role_from_email("boss@colby.edu") == "admin"

    def test_faculty_priority_over_default_colby(self, monkeypatch):
        """Test that FACULTY_EMAILS config takes precedence over default Colby rule"""
        class MockApp:
            config = {
                "ADMIN_EMAILS": [],
                "FACULTY_EMAILS": ["special123@colby.edu"]  # Has number but in config
            }
        
        monkeypatch.setattr("website.auth.current_app", MockApp)
        
        # Should return 'faculty' even though email has number
        assert get_role_from_email("special123@colby.edu") == "faculty"

    def test_local_part_extraction_and_digit_check(self, monkeypatch):
        """Test the regex digit detection in local part"""
        class MockApp:
            config = {"ADMIN_EMAILS": [], "FACULTY_EMAILS": []}
        
        monkeypatch.setattr("website.auth.current_app", MockApp)
        
        # No digits - should be faculty
        assert get_role_from_email("abc@colby.edu") == "faculty"
        assert get_role_from_email("a.b.c@colby.edu") == "faculty"
        
        # Has digits - should be None
        assert get_role_from_email("a1@colby.edu") is None
        assert get_role_from_email("1a@colby.edu") is None
        assert get_role_from_email("a.1.b@colby.edu") is None

    def test_config_list_normalization(self, monkeypatch):
        """Test that config lists are normalized (stripped, lowercase)"""
        class MockApp:
            config = {
                "ADMIN_EMAILS": ["  ADMIN@colby.edu  ", "Boss@Colby.Edu"],
                "FACULTY_EMAILS": []
            }
        
        monkeypatch.setattr("website.auth.current_app", MockApp)
        
        # Should match even with different casing/spacing
        assert get_role_from_email("admin@colby.edu") == "admin"
        assert get_role_from_email("boss@colby.edu") == "admin"

    def test_missing_config_keys(self, monkeypatch):
        """Test behavior when config keys are missing"""
        class MockApp:
            config = {}  # No ADMIN_EMAILS or FACULTY_EMAILS
        
        monkeypatch.setattr("website.auth.current_app", MockApp)
        
        # Should fall back to default Colby logic
        assert get_role_from_email("prof@colby.edu") == "faculty"
        assert get_role_from_email("student123@colby.edu") is None