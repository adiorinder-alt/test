import os
import sys
import argparse
import subprocess
import json
import webbrowser
import base64
from pathlib import Path
from typing import Optional, Dict, Any
from getpass import getpass
import time
from descope import DeliveryMethod
try:
    from github import Github, GithubException
except ImportError:
    print("❌ PyGithub not installed. Run: pip install PyGithub")
    sys.exit(1)

try:
    from descope import DescopeClient
except ImportError:
    print("❌ Descope not installed. Run: pip install descope")
    sys.exit(1)

class GitHubCLI:
    def __init__(self):
        self.config_dir = Path.home() / '.github-cli'
        self.config_file = self.config_dir / 'config.json'
        self.github = None
        self.descope_client = None
        self.config = {}
        
        self.descope_project_id = os.getenv('DESCOPE_PROJECT_ID', 'P31M5kW4iiyEZQEnVzT8wSOjviwy')
        self.descope_management_key = os.getenv('DESCOPE_MANAGEMENT_KEY', 'P2DA3QqyF3N3BlmIqn1nr0LMFhrw:K31M7dAsZ3ZPw7Ux0YvZgGNmHtL79dyfXvR6GJncQwQ83tDgIvMzZv9W24z2WmrskEYejLT')
        self.config_dir.mkdir(exist_ok=True)
        self.load_config()
        self.init_descope_client()
    
    def load_config(self):
        
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    self.config = json.load(f)
        except Exception as e:
            print(f"⚠️  Warning: Could not load config: {e}")
    
    def save_config(self):
        
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            print(f"❌ Error saving config: {e}")
    
    def init_descope_client(self):
        
        try:
            self.descope_client = DescopeClient(
                project_id=self.descope_project_id,
                management_key=self.descope_management_key
            )
            print("✅ Descope client initialized successfully!")
        except Exception as e:
            print(f"⚠️  Warning: Could not initialize Descope client: {e}")
            self.descope_client = None
    
    def authenticate_descope(self, email: Optional[str] = None, force: bool = False) -> bool:
        
        if not self.descope_client:
            print("❌ Descope client not initialized")
            return False
        if not force and 'descope_session_token' in self.config and 'user_email' in self.config:
            print(f"🔑 Already authenticated as: {self.config['user_email']}")

            try:

                session_token = self.config['descope_session_token']
                return self.setup_github_connection()
            except Exception as e:
                print(f"⚠️  Existing session invalid: {e}")
        if not email:
            email = input("\n📧 Enter your email address: ")
        
        print(f"\n🔑 Descope Authentication for {email}")
        print("Choose authentication method:")
        print("1. Magic Link (email)")
        print("2. OTP (email)")
        
        choice = input("Enter choice (1 or 2): ").strip()
        
        try:
            if choice == "1":
                return self.authenticate_magic_link(email)
            elif choice == "2":
                return self.authenticate_otp(email)
            else:
                print("❌ Invalid choice")
                return False
        except Exception as e:
            print(f"❌ Authentication failed: {e}")
            return False
    
    def authenticate_magic_link(self, email: str) -> bool:
        
        try:
            print("\n📧 Sending magic link...")
            response = self.descope_client.magiclink.sign_in(
                method=DeliveryMethod.EMAIL,
                login_id=email,
                uri="http://localhost:3000/auth/callback"
            )
            
            print(f"✅ Magic link sent to {email}")
            print("Please check your email and click the magic link.")
            print("After clicking the link, you'll be redirected to a page with authentication details.")
            print("\nAfter completing authentication in browser:")
            session_token = input("Paste the session token (or verification code): ").strip()
            
            if session_token:
                return self.complete_authentication(email, session_token)
            else:
                print("❌ No session token provided")
                return False
                
        except Exception as e:
            print(f"❌ Magic link authentication failed: {e}")
            return False
    
    def authenticate_otp(self, email: str) -> bool:
        
        try:
            print("\n📱 Sending OTP...")
            response = self.descope_client.otp.sign_in(
                login_id=email,
                method=DeliveryMethod.EMAIL

            )
            
            print(f"✅ OTP sent to {email}")
            otp_code = input("Enter the OTP code: ").strip()
            
            if not otp_code:
                print("❌ No OTP code provided")
                return False
            verify_response = self.descope_client.otp.verify_code(
                method=DeliveryMethod.EMAIL,
                login_id=email,
                code=otp_code
            )
            
            print(f"✅ OTP verification successful!")
            print(f"📋 Full response: {verify_response}")
            if hasattr(verify_response, 'session_jwt') and verify_response.session_jwt:
                session_token = verify_response.session_jwt
                user_info = verify_response.user if hasattr(verify_response, 'user') else None
                return self.complete_authentication_with_session(email, session_token, user_info, verify_response)
            else:
                print("❌ Failed to get session token from response")
                return False
                
        except Exception as e:
            print(f"❌ OTP authentication failed: {e}")
            return False
    
    def complete_authentication_with_session(self, email: str, session_token: str, user_info: Any, full_response: Any) -> bool:
        
        try:
            print("\n✅ Descope authentication successful!")
            self.config['descope_session_token'] = session_token
            self.config['user_email'] = email
            github_token = self.extract_github_token_from_session(full_response, user_info)
            
            if github_token:
                print("✅ GitHub token found in Descope session!")
                return self.setup_github_with_token(github_token)
            else:
                print("⚠️  No GitHub token found in session. You may need to configure the GitHub OAuth integration in Descope.")
                print("Falling back to manual GitHub token input...")
                return self.setup_github_connection()
            
        except Exception as e:
            print(f"❌ Failed to complete authentication: {e}")
            return False
    
    def extract_github_token_from_session(self, full_response: Any, user_info: Any) -> Optional[str]:
        
        try:

            github_token = None
            if user_info:
                print(f"📋 User info: {user_info}")
                if hasattr(user_info, 'custom_attributes') and user_info.custom_attributes:
                    custom_attrs = user_info.custom_attributes
                    print(f"📋 Custom attributes: {custom_attrs}")
                    if 'github_token' in custom_attrs:
                        github_token = custom_attrs['github_token']
                    elif 'oauth_tokens' in custom_attrs:
                        oauth_tokens = custom_attrs['oauth_tokens']
                        if isinstance(oauth_tokens, dict) and 'github' in oauth_tokens:
                            github_token = oauth_tokens['github'].get('access_token')
                if hasattr(user_info, 'oauth') and user_info.oauth:
                    print(f"📋 OAuth info: {user_info.oauth}")
                    for provider_name, provider_data in user_info.oauth.items():
                        if provider_name.lower() == 'github':
                            if isinstance(provider_data, dict) and 'access_token' in provider_data:
                                github_token = provider_data['access_token']
            if not github_token and full_response:
                print(f"📋 Checking full response for GitHub token...")
                if hasattr(full_response, 'oauth_tokens') and full_response.oauth_tokens:
                    oauth_tokens = full_response.oauth_tokens
                    print(f"📋 OAuth tokens: {oauth_tokens}")
                    if isinstance(oauth_tokens, dict) and 'github' in oauth_tokens:
                        github_data = oauth_tokens['github']
                        if isinstance(github_data, dict) and 'access_token' in github_data:
                            github_token = github_data['access_token']
                if not github_token and hasattr(full_response, 'user') and full_response.user:
                    user = full_response.user
                    if hasattr(user, 'oauth') and user.oauth:
                        for provider_name, provider_data in user.oauth.items():
                            if provider_name.lower() == 'github':
                                if isinstance(provider_data, dict) and 'access_token' in provider_data:
                                    github_token = provider_data['access_token']
            
            if github_token:
                print(f"✅ Found GitHub token in Descope session!")
                return github_token
            else:
                print("⚠️  No GitHub token found in session data")
                return None
                
        except Exception as e:
            print(f"⚠️  Error extracting GitHub token from session: {e}")
            return None
    
    def setup_github_with_token(self, github_token: str) -> bool:
        
        try:
            self.github = Github(github_token)
            user = self.github.get_user()
            self.config['github_token'] = github_token
            self.config['github_username'] = user.login
            self.save_config()
            
            print(f"✅ GitHub automatically connected as: {user.login}")
            return True
            
        except GithubException as e:
            print(f"❌ Failed to connect to GitHub with extracted token: {e}")
            print("Falling back to manual token input...")
            return self.setup_github_connection()
        except Exception as e:
            print(f"❌ Unexpected error connecting to GitHub: {e}")
            return False
    
    def complete_authentication(self, email: str, session_token: str) -> bool:
        
        try:
            print("\n✅ Descope authentication successful!")
            self.config['descope_session_token'] = session_token
            self.config['user_email'] = email
            print("⚠️  Magic link authentication completed, but no session data available for GitHub token extraction.")
            print("Please provide your GitHub token manually...")
            return self.setup_github_connection()
            
        except Exception as e:
            print(f"❌ Failed to complete authentication: {e}")
            return False
    
    def setup_github_connection(self) -> bool:
        if 'github_token' in self.config and 'github_username' in self.config:
            try:
                self.github = Github(self.config['github_token'])
                user = self.github.get_user()
                print(f"🐙 GitHub connected as: {user.login}")
                return True
            except GithubException:
                print("⚠️  Existing GitHub token invalid, requesting new one")
        
        print("\n🐙 GitHub Token Setup")
        print("You need a GitHub Personal Access Token for repository operations.")
        print("Create one at: https://github.com/settings/tokens")
        print("Required scopes: repo, user")
        
        github_token = getpass("Enter your GitHub token: ").strip()
        
        if not github_token:
            print("❌ No GitHub token provided")
            return False
        
        try:
            self.github = Github(github_token)
            user = self.github.get_user()
            self.config['github_token'] = github_token
            self.config['github_username'] = user.login
            self.save_config()
            
            print(f"✅ GitHub connected as: {user.login}")
            return True
            
        except GithubException as e:
            print(f"❌ GitHub authentication failed: {e}")
            return False
    
    def authenticate(self, email: Optional[str] = None, force: bool = False) -> bool:
        
        return self.authenticate_descope(email, force)
    
    def get_or_create_repo(self, repo_name: str, description: str = "", private: bool = False) -> Optional[Any]:
        
        try:

            user = self.github.get_user()
            repo = user.get_repo(repo_name)
            print(f"📁 Found existing repository: {repo.full_name}")
            return repo
            
        except GithubException:

            try:
                user = self.github.get_user()
                repo = user.create_repo(
                    name=repo_name,
                    description=description,
                    private=private,
                    auto_init=True
                )
                print(f"🆕 Created new repository: {repo.full_name}")
                return repo
                
            except GithubException as e:
                print(f"❌ Failed to create repository: {e}")
                return None
    
    def init_local_repo(self, repo_url: str) -> bool:
        
        try:

            result = subprocess.run(['git', 'status'], capture_output=True, text=True)
            if result.returncode == 0:
                print("📁 Directory is already a git repository")
                result = subprocess.run(['git', 'remote', 'get-url', 'origin'], capture_output=True, text=True)
                if result.returncode != 0:

                    subprocess.run(['git', 'remote', 'add', 'origin', repo_url], check=True)
                    print(f"🔗 Added remote origin: {repo_url}")
            else:

                subprocess.run(['git', 'init'], check=True)
                subprocess.run(['git', 'remote', 'add', 'origin', repo_url], check=True)
                print(f"🆕 Initialized git repository with origin: {repo_url}")
            
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Git operation failed: {e}")
            return False
    
    def commit_and_push(self, message: str, branch: str = 'main') -> bool:
        
        try:

            subprocess.run(['git', 'add', '.'], check=True)
            result = subprocess.run(['git', 'diff', '--staged', '--quiet'], capture_output=True)
            if result.returncode == 0:
                print("ℹ️  No changes to commit")
                return True
            subprocess.run(['git', 'commit', '-m', message], check=True)
            print(f"✅ Committed changes: {message}")
            subprocess.run(['git', 'push', 'origin', branch], check=True)
            print(f"🚀 Pushed to {branch} branch")
            
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Git operation failed: {e}")
            return False
    
    def show_issues(self, limit: int, repo: str, label: list) -> None:
        
        try:
            issues = self.github.get_repo(repo).get_issues(labels=label)
            count = 0
            for issue in issues:
                if count >= limit:
                    break
                print(f"#{issue.number}: {issue.title}")
                print(f"  - Opened by: {issue.user.login}")
                print(f"  - URL: {issue.html_url}\n")
                count += 1
        except GithubException as e:
            print(f"❌ An error occurred: {e}")
            print("Please check your GITHUB_TOKEN and REPO_NAME.")
        except Exception as e:
            print(f"❌ An unexpected error occurred: {e}")
    def show_status(self):
        
        print("\n📊 Status:")
        if 'user_email' in self.config:
            print(f"🔐 Descope: Authenticated as {self.config['user_email']}")
        else:
            print("🔐 Descope: Not authenticated")
        if 'github_username' in self.config:
            print(f"🐙 GitHub: Connected as {self.config['github_username']}")
        else:
            print("🐙 GitHub: Not connected")
        try:
            result = subprocess.run(['git', 'status', '--porcelain'], capture_output=True, text=True)
            if result.returncode == 0:
                if result.stdout.strip():
                    print(f"📝 Uncommitted changes: {len(result.stdout.strip().split())} files")
                else:
                    print("✅ Working directory clean")
        except subprocess.CalledProcessError:
            print("📁 Not in a git repository")
        try:
            result = subprocess.run(['git', 'remote', 'get-url', 'origin'], capture_output=True, text=True)
            if result.returncode == 0:
                print(f"🔗 Remote origin: {result.stdout.strip()}")
        except subprocess.CalledProcessError:
            print("🔗 No remote origin set")

def main():
    parser = argparse.ArgumentParser(
        description='GitHub CLI Authentication and Commit Tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s auth
  %(prog)s init my-repo
  %(prog)s commit "Initial commit"
  %(prog)s status
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    auth_parser = subparsers.add_parser('auth', help='Authenticate with Descope and GitHub')
    auth_parser.add_argument('--email', help='Email address for Descope authentication')
    auth_parser.add_argument('--force', action='store_true', help='Force re-authentication')

    issue_parser = subparsers.add_parser('issue', help='Show repository issues')
    issue_parser.add_argument('--limit', type=int, default=10, help='Number of issues to show (default: 10)')
    issue_parser.add_argument('repo_name', help='Repository name')
    issue_parser.add_argument('--label', action='append', help='Filter by label (can be used multiple times)')
    init_parser = subparsers.add_parser('init', help='Initialize repository')
    init_parser.add_argument('repo_name', help='Repository name')
    init_parser.add_argument('--description', default='', help='Repository description')
    init_parser.add_argument('--private', action='store_true', help='Create private repository')
    commit_parser = subparsers.add_parser('commit', help='Commit and push changes')
    commit_parser.add_argument('message', help='Commit message')
    commit_parser.add_argument('--branch', default='main', help='Branch to push to (default: main)')
    status_parser = subparsers.add_parser('status', help='Show current status')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    cli = GitHubCLI()
    
    if args.command == 'auth':
        success = cli.authenticate(args.email, args.force)
        if not success:
            sys.exit(1)
    
    elif args.command == 'init':

        if not cli.authenticate():
            print("❌ Authentication required for repository operations")
            sys.exit(1)
        repo = cli.get_or_create_repo(args.repo_name, args.description, args.private)
        if not repo:
            sys.exit(1)
        if not cli.init_local_repo(repo.clone_url):
            sys.exit(1)
    
    elif args.command == 'commit':

        if not cli.authenticate():
            print("❌ Authentication required for git operations")
            sys.exit(1)
        if not cli.commit_and_push(args.message, args.branch):
            sys.exit(1)
    
    elif args.command == 'status':
        cli.show_status()
    
    elif args.command == 'issue':

        if not cli.authenticate():
            print("❌ Authentication required for repository operations")
            sys.exit(1)
        labels = args.label if args.label else []
        cli.show_issues(args.limit, args.repo_name, labels)
if __name__ == '__main__':
    main()
