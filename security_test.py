#!/usr/bin/env python3
"""Security testing script for SLMS application."""

import requests
import sys
from urllib.parse import urljoin


class SecurityTester:
    """Basic security testing for web applications."""

    def __init__(self, base_url):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.issues = []

    def test_security_headers(self):
        """Test for presence of security headers."""
        print("🔍 Testing Security Headers...")

        try:
            response = self.session.get(self.base_url)
            headers = response.headers

            required_headers = {
                'X-Content-Type-Options': 'nosniff',
                'X-Frame-Options': 'DENY',
                'Referrer-Policy': 'no-referrer-when-downgrade',
                'Content-Security-Policy': None,  # Just check presence
                'X-XSS-Protection': '1; mode=block'
            }

            for header, expected_value in required_headers.items():
                if header not in headers:
                    self.issues.append(f"Missing security header: {header}")
                    print(f"  ❌ Missing: {header}")
                elif expected_value and headers[header] != expected_value:
                    self.issues.append(f"Incorrect {header}: {headers[header]}")
                    print(f"  ⚠️  Incorrect: {header} = {headers[header]}")
                else:
                    print(f"  ✅ Present: {header}")

        except requests.RequestException as e:
            self.issues.append(f"Failed to test headers: {e}")
            print(f"  ❌ Request failed: {e}")

    def test_csrf_protection(self):
        """Test CSRF protection on forms."""
        print("\n🛡️  Testing CSRF Protection...")

        try:
            # Test login form
            login_url = urljoin(self.base_url, '/auth/login')
            response = self.session.get(login_url)

            if 'csrf_token' in response.text or 'X-CSRFToken' in response.text:
                print("  ✅ CSRF tokens found in login form")
            else:
                self.issues.append("CSRF tokens not found in forms")
                print("  ❌ No CSRF tokens found")

            # Test POST without CSRF token
            try:
                post_response = self.session.post(login_url, data={
                    'email': 'test@example.com',
                    'password': 'password'
                })

                if post_response.status_code == 400:
                    print("  ✅ POST requests rejected without CSRF token")
                else:
                    print("  ⚠️  POST request accepted without CSRF token")
            except:
                print("  ✅ CSRF protection appears to be working")

        except requests.RequestException as e:
            print(f"  ❌ CSRF test failed: {e}")

    def test_rate_limiting(self):
        """Test rate limiting on authentication endpoints."""
        print("\n⏱️  Testing Rate Limiting...")

        try:
            login_url = urljoin(self.base_url, '/auth/login')

            # Make multiple rapid requests
            for i in range(7):  # Should hit 5/min limit
                response = self.session.post(login_url, data={
                    'email': 'test@example.com',
                    'password': 'wrongpassword'
                })

                if response.status_code == 429:
                    print(f"  ✅ Rate limiting triggered after {i+1} requests")
                    return

            print("  ⚠️  Rate limiting not triggered after 7 requests")

        except requests.RequestException as e:
            print(f"  ❌ Rate limiting test failed: {e}")

    def test_ssl_configuration(self):
        """Test SSL/TLS configuration."""
        print("\n🔒 Testing SSL Configuration...")

        if self.base_url.startswith('https'):
            try:
                response = self.session.get(self.base_url)

                if 'Strict-Transport-Security' in response.headers:
                    print("  ✅ HSTS header present")
                else:
                    print("  ⚠️  HSTS header missing (expected for HTTPS)")

            except requests.SSLError:
                self.issues.append("SSL certificate issues detected")
                print("  ❌ SSL certificate problems")
            except requests.RequestException as e:
                print(f"  ❌ SSL test failed: {e}")
        else:
            print("  ⚠️  Application not using HTTPS")

    def test_information_disclosure(self):
        """Test for information disclosure vulnerabilities."""
        print("\n📋 Testing Information Disclosure...")

        test_paths = [
            '/.env',
            '/config.py',
            '/.git/',
            '/admin',
            '/debug',
            '/server-status',
            '/server-info'
        ]

        for path in test_paths:
            try:
                url = urljoin(self.base_url, path)
                response = self.session.get(url)

                if response.status_code == 200:
                    print(f"  ⚠️  Accessible: {path} (Status: {response.status_code})")
                    if len(response.text) > 0:
                        self.issues.append(f"Sensitive path accessible: {path}")
                else:
                    print(f"  ✅ Protected: {path} (Status: {response.status_code})")

            except requests.RequestException:
                continue

    def test_input_validation(self):
        """Test basic input validation."""
        print("\n📝 Testing Input Validation...")

        # Test for basic XSS in URL parameters
        xss_payloads = [
            '<script>alert(1)</script>',
            '"><script>alert(1)</script>',
            'javascript:alert(1)'
        ]

        for payload in xss_payloads:
            try:
                url = f"{self.base_url}/?test={payload}"
                response = self.session.get(url)

                if payload in response.text:
                    self.issues.append(f"Potential XSS vulnerability with payload: {payload}")
                    print(f"  ⚠️  Potential XSS: {payload}")
                else:
                    print(f"  ✅ XSS payload filtered: {payload}")

            except requests.RequestException:
                continue

    def run_all_tests(self):
        """Run all security tests."""
        print(f"🚀 Starting Security Tests for: {self.base_url}")
        print("=" * 60)

        self.test_security_headers()
        self.test_csrf_protection()
        self.test_rate_limiting()
        self.test_ssl_configuration()
        self.test_information_disclosure()
        self.test_input_validation()

        print("\n" + "=" * 60)
        print("📊 SECURITY TEST SUMMARY")
        print("=" * 60)

        if not self.issues:
            print("🎉 No security issues detected!")
            print("✅ All basic security tests passed.")
        else:
            print(f"⚠️  {len(self.issues)} potential security issues found:")
            for i, issue in enumerate(self.issues, 1):
                print(f"  {i}. {issue}")

        print("\n📋 RECOMMENDATIONS:")
        print("- Run a full OWASP ZAP scan for comprehensive testing")
        print("- Enable HTTPS in production with proper SSL certificates")
        print("- Configure Redis for rate limiting in production")
        print("- Review Content Security Policy for your specific needs")
        print("- Implement proper logging and monitoring")
        print("- Regular security updates and dependency scanning")

        return len(self.issues)


def main():
    """Main function."""
    if len(sys.argv) != 2:
        print("Usage: python security_test.py <base_url>")
        print("Example: python security_test.py http://localhost:5000")
        sys.exit(1)

    base_url = sys.argv[1]
    tester = SecurityTester(base_url)

    try:
        issues_count = tester.run_all_tests()
        sys.exit(issues_count)  # Exit with number of issues as code
    except KeyboardInterrupt:
        print("\n\n🛑 Testing interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Testing failed with error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()