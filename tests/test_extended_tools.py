from coding_tablet.email_client import DraftEmail
from coding_tablet.os_profiles import get_profile
from coding_tablet.toolkit import CodingTablet


def test_os_profile_lookup_supports_windows_shells():
    assert get_profile("windows-powershell").shell == "powershell"
    assert get_profile("windows-cmd").shell == "cmd"


def test_email_client_creates_preview_without_sending():
    result = DraftEmail(["user@example.com"], "Hello", "Body").preview()
    assert result.ok is True
    assert result.data["to"] == ["user@example.com"]
    assert "Subject: Hello" in result.data["rfc822"]


def test_toolkit_facade_defaults_to_safe_shell(tmp_path):
    tablet = CodingTablet(workspace=tmp_path)
    assert tablet.os_profile.name == "linux"
    assert tablet.shell.run("echo nope").ok is False
    assert tablet.notepad.write("a.txt", "hello").ok is True
