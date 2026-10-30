# Public release demo data

`demo-password.txt` contains a deliberately public, synthetic credential for
the CLI screenshot campaign. It protects no real accounts. Never replace it
with a user password. The campaign copies this fixture to its temporary working
directory to exercise `--password-file`; temporary files are removed afterward.
This is not a historical binary vault fixture.
