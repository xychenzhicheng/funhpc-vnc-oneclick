"""Offline checks only: no installation, no network, no server modification.
Run from Git Bash: python -I test_installer.py
"""
import pathlib
import re
import subprocess
import unittest

SCRIPT = pathlib.Path(__file__).with_name('install-vnc.sh').read_text(encoding='utf-8')
VALIDATION = SCRIPT.split('[[ "$EUID" -eq 0 ]]', 1)[0] + '\nprintf "VALIDATION_OK\\n"\n'
RUNNER = SCRIPT.split("<<'RUNNER'\n", 1)[1].split('\nRUNNER\n', 1)[0]


def bash(code, args=(), syntax=False):
    command = ['bash', '-n'] if syntax else ['bash', '-c', code, 'validation', *args]
    return subprocess.run(command, input=code if syntax else None,
                          text=True, capture_output=True, timeout=10)


class InstallerChecks(unittest.TestCase):
    def test_installer_syntax(self):
        result = bash(SCRIPT, syntax=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_runner_syntax(self):
        result = bash(RUNNER, syntax=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_embedded_python_syntax(self):
        snippets = re.findall(r"<<'PY'\n(.*?)\nPY", SCRIPT, re.S)
        self.assertEqual(len(snippets), 4)
        for number, code in enumerate(snippets):
            compile(code, f'embedded-python-{number}', 'exec')

    def test_valid_options(self):
        for args in [[], ['--port', '6080'], ['--port', '65535'],
                     ['--display', '1'], ['--display', '99'],
                     ['--geometry', '640x480'], ['--geometry', '7680x4320'],
                     ['--reset-password'], ['--password-file', '/private/password'],
                     ['--port', '6082', '--display', '3', '--geometry', '1920x1080']]:
            with self.subTest(args=args):
                result = bash(VALIDATION, args)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn('VALIDATION_OK', result.stdout)

    def test_invalid_options(self):
        cases = [
            ['--port'], ['--port', ''], ['--port', '0'], ['--port', '22'],
            ['--port', '8080'], ['--port', '65536'], ['--port', '06080'],
            ['--port', '-1'], ['--port', 'abc'], ['--port', '$(exit 0)'],
            ['--display', '0'], ['--display', '100'], ['--display', '01'],
            ['--display', ':1'], ['--geometry', '639x480'],
            ['--geometry', '1280x479'], ['--geometry', '8000x480'],
            ['--geometry', '1280x5000'], ['--geometry', '1280X960'],
            ['--geometry', '01280x960'], ['--password-file', ''], ['--unknown'],
        ]
        for args in cases:
            with self.subTest(args=args):
                result = bash(VALIDATION, args)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('ERROR:', result.stderr)
                self.assertNotIn('VALIDATION_OK', result.stdout)

    def test_help(self):
        result = bash(VALIDATION, ['--help'])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('Usage:', result.stdout)
        self.assertNotIn('VALIDATION_OK', result.stdout)

    def test_password_validation(self):
        code = '''set -e
export LC_ALL=C
password=$1
[[ ${#password} -ge 6 && ${#password} -le 8 && "$password" != *$'\\n'* ]]
printf '%s\\n' "$password" | grep -q '^[ -~]\\{6,8\\}$'
'''
        for password, valid in [('abc123', True), ('a B!2345', True),
                                ('short', False), ('toolong99', False),
                                ('abc\n123', False), ('abc\t123', False),
                                ('', False), ('中文密码', False)]:
            with self.subTest(valid=valid, length=len(password)):
                result = bash(code, [password])
                self.assertEqual(result.returncode == 0, valid)


if __name__ == '__main__':
    unittest.main(verbosity=2)
