import os
import sys
import argparse
import subprocess
import json

from pathlib import Path
from typing import Optional, Dict, Any
from getpass import getpass
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

try:
    from openai import OpenAI
except ImportError:
    print("❌ OpenAI not installed. Run: pip install openai")
    sys.exit(1)

try:
    import requests
except ImportError:
    print("📦 Installing requests...")
    subprocess.run([sys.executable, "-m", "pip", "install", "requests"], check=True)
    import requests

class GitHubCLI:
    def __init__(self):
        self.config_dir = Path.home() / '.github-cli'
        self.config_file = self.config_dir / 'config.json'
        self.github = None
        self.descope_client = None
        self.openai_client = None
        self.config = {}
        self.ollama_url = "http://localhost:11434"
        
        self.descope_project_id = os.getenv('DESCOPE_PROJECT_ID', 'P31M5kW4iiyEZQEnVzT8wSOjviwy')
        self.descope_management_key = os.getenv('DESCOPE_MANAGEMENT_KEY', 'P2DA3QqyF3N3BlmIqn1nr0LMFhrw:K31M7dAsZ3ZPw7Ux0YvZgGNmHtL79dyfXvR6GJncQwQ83tDgIvMzZv9W24z2WmrskEYejLT')
        self.config_dir.mkdir(exist_ok=True)
        self.load_config()
        self.init_descope_client()
        self.init_openai_client()
    
    def load_config(self):
        
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    self.config = json.load(f)
        except Exception as e:
            print(f"Warning: Could not load config: {e}")
    
    def save_config(self):
        
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            print(f"Error saving config: {e}")
    
    def init_descope_client(self):
        
        try:
            self.descope_client = DescopeClient(
                project_id=self.descope_project_id,
                management_key=self.descope_management_key
            )
            print("Descope client initialized successfully!")
        except Exception as e:
            print(f"Warning: Could not initialize Descope client: {e}")
            self.descope_client = None
    
    def init_openai_client(self):
        """Initialize OpenAI client with API key management"""
        openai_api_key = os.getenv('OPENAI_API_KEY') or self.config.get('openai_api_key')
        
        if not openai_api_key:
            # Don't initialize if no key is available, but don't error out
            # The key will be requested when the auto feature is used
            self.openai_client = None
            return
        
        try:
            self.openai_client = OpenAI(api_key=openai_api_key)
            # Test the connection with a simple request
            # This will raise an exception if the API key is invalid
        except Exception as e:
            print(f"Warning: Could not initialize OpenAI client: {e}")
            self.openai_client = None
    
    def setup_openai_client(self) -> bool:
        """Set up OpenAI client with API key from user input"""
        if self.openai_client:
            return True
        
        openai_api_key = os.getenv('OPENAI_API_KEY') or self.config.get('openai_api_key')
        
        if not openai_api_key:
            print("\n🤖 OpenAI API Key Setup")
            print("You need an OpenAI API key for automatic commit message generation.")
            print("Get one at: https://platform.openai.com/account/api-keys")
            
            openai_api_key = getpass("Enter your OpenAI API key: ").strip()
            
            if not openai_api_key:
                print("❌ No OpenAI API key provided")
                return False
            
            # Save the API key to config
            self.config['openai_api_key'] = openai_api_key
            self.save_config()
        
        try:
            self.openai_client = OpenAI(api_key=openai_api_key)
            return True
        except Exception as e:
            print(f"❌ OpenAI API key validation failed: {e}")
            return False
    
    def get_git_diff(self) -> Optional[str]:
        """Get staged git changes for commit message generation"""
        try:
            # Check if there are staged changes
            result = subprocess.run(['git', 'diff', '--staged', '--quiet'], capture_output=True)
            if result.returncode == 0:
                # No staged changes, get all changes
                result = subprocess.run(['git', 'diff'], capture_output=True, text=True)
                if result.returncode == 0 and result.stdout.strip():
                    return result.stdout
                else:
                    # If no unstaged changes either, compare with last commit
                    result = subprocess.run(['git', 'diff', 'HEAD~1'], capture_output=True, text=True)
                    if result.returncode == 0 and result.stdout.strip():
                        return result.stdout
            else:
                # Get staged changes
                result = subprocess.run(['git', 'diff', '--staged'], capture_output=True, text=True)
                if result.returncode == 0 and result.stdout.strip():
                    return result.stdout
            
            return None
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to get git diff: {e}")
            return None
    
    def generate_commit_message(self, git_diff: str) -> Optional[str]:
        """Generate commit message using Hugging Face Inference API (FREE)"""
        try:
            print("🤗 Using Hugging Face Inference API...")
            result = self.generate_with_huggingface(git_diff)
            if result:
                return result
        except Exception as e:
            print(f"⚠️ Hugging Face failed: {e}")
        
        print("🔄 Using intelligent fallback analysis...")
        return self.generate_fallback_message(git_diff)
    
    def generate_with_huggingface(self, git_diff: str) -> Optional[str]:
        """Generate commit message using multiple AI APIs (FREE)"""
        try:
            import requests
            from time import sleep
            
            # Test connectivity first
            if not self.test_connectivity():
                print("📶 Network connectivity issues detected, using offline mode")
                return None
            
            # Create a focused prompt
            prompt = f"""Git commit message for:\n{git_diff[:800]}\n\nMessage:"""
            
            hf_token = os.getenv('HUGGINGFACE_API_TOKEN')
            if not hf_token:
                response = input("\n🤗 Enter HF token (or press Enter to skip): ").strip()
                if response:
                    hf_token = response
                    os.environ['HUGGINGFACE_API_TOKEN'] = hf_token
            
            # Try different API strategies
            strategies = [
                self.try_huggingface_serverless,
                self.try_alternative_apis,
                self.try_simple_text_generation
            ]
            
            for strategy in strategies:
                try:
                    result = strategy(prompt, hf_token)
                    if result:
                        return result
                except Exception as e:
                    print(f"⚠️ Strategy failed: {str(e)[:50]}")
                    continue
            
            return None
            
        except ImportError:
            print("📦 Installing requests...")
            subprocess.run([sys.executable, "-m", "pip", "install", "requests"], check=True)
            return self.generate_with_huggingface(git_diff)
        except Exception as e:
            print(f"❌ HF API error: {str(e)[:100]}")
            return None
    
    def test_connectivity(self) -> bool:
        """Test basic internet connectivity"""
        try:
            import requests
            # Test with a simple, fast endpoint
            response = requests.get("https://www.google.com", timeout=3)
            return response.status_code == 200
        except:
            try:
                # Try alternative endpoint
                import requests
                response = requests.get("https://httpbin.org/status/200", timeout=2)
                return response.status_code == 200
            except:
                # If both fail, assume no connectivity but don't block - let API calls handle their own timeouts
                return True  # Changed to True to allow API attempts
    
    def try_huggingface_serverless(self, prompt: str, hf_token: Optional[str]) -> Optional[str]:
        """Try Hugging Face Serverless Inference with better error handling"""
        import requests
        
        if not hf_token:
            print("⚠️ No HF token provided, trying without auth...")
            return None  # Skip HF if no token
        
        # Working models for text generation
        models = [
            "microsoft/DialoGPT-small",
            "gpt2",
            "distilgpt2"
        ]
        
        for model in models:
            try:
                headers = {
                    "Authorization": f"Bearer {hf_token}",
                    "Content-Type": "application/json"
                }
                
                # Simplified prompt for better results
                simple_prompt = f"Commit message:\n{prompt[:500]}\n\nGenerate a git commit message:"
                
                print(f"🔄 Trying {model}...")
                response = requests.post(
                    f"https://api-inference.huggingface.co/models/{model}",
                    headers=headers,
                    json={
                        "inputs": simple_prompt,
                        "parameters": {
                            "max_new_tokens": 50,
                            "temperature": 0.7,
                            "do_sample": True,
                            "return_full_text": False
                        }
                    },
                    timeout=10
                )
                
                print(f"📡 {model} response: {response.status_code}")
                
                if response.status_code == 200:
                    result = response.json()
                    print(f"📄 Response data: {str(result)[:200]}")
                    
                    if isinstance(result, list) and result:
                        generated = result[0].get("generated_text", "")
                        if generated:
                            commit_msg = self.extract_commit_message(generated, simple_prompt)
                            if commit_msg:
                                print(f"✅ Success with {model}: {commit_msg}")
                                return commit_msg
                    elif isinstance(result, dict) and "generated_text" in result:
                        generated = result["generated_text"]
                        commit_msg = self.extract_commit_message(generated, simple_prompt)
                        if commit_msg:
                            print(f"✅ Success with {model}: {commit_msg}")
                            return commit_msg
                
                elif response.status_code == 503:
                    print(f"⏳ {model} is loading, waiting 5 seconds...")
                    import time
                    time.sleep(5)
                    continue
                elif response.status_code == 401:
                    print(f"🔐 {model} auth failed - check your HF token")
                    continue
                elif response.status_code == 429:
                    print(f"⏱️ {model} rate limited")
                    continue
                else:
                    print(f"❌ {model} failed: {response.status_code} - {response.text[:100]}")
                    continue
                            
            except requests.exceptions.Timeout:
                print(f"⏱️ {model} timeout after 10s")
                continue
            except Exception as e:
                print(f"⚠️ {model} error: {str(e)[:50]}")
                continue
        
        return None
    
    def check_ollama_running(self) -> bool:
        """Check if Ollama is running"""
        try:
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def get_available_models(self) -> list:
        """Get list of available Ollama models"""
        try:
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=5)
            if response.status_code == 200:
                data = response.json()
                return [model['name'] for model in data.get('models', [])]
        except:
            pass
        return []
    
    def generate_with_ollama(self, git_diff: str) -> Optional[str]:
        """Generate commit message using local Ollama LLM"""
        try:
            if not self.check_ollama_running():
                print("⚠️ Ollama is not running. Start with 'ollama serve'")
                return None
            
            model = self.config.get('preferred_model', 'llama3.2:1b')
            
            # Check if model exists
            available_models = self.get_available_models()
            if not any(model.startswith(m.split(':')[0]) for m in available_models):
                print(f"⚠️ Model {model} not found. Available models: {', '.join(available_models[:3])}")
                if available_models:
                    model = available_models[0]
                    print(f"🔄 Using {model} instead")
                else:
                    print("❌ No models available. Run 'ollama pull llama3.2:1b' to install a model")
                    return None
            
            # Create a focused prompt for commit messages
            prompt = f"""Generate a concise git commit message for the following code changes. 
Use conventional commit format (type: description). 
Types: feat, fix, docs, style, refactor, test, chore.
Keep it under 50 characters.

Code changes:
{git_diff[:1500]}

Commit message:"""

            print(f"🤖 Generating commit message with {model}...")
            
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.3,
                        "top_p": 0.9,
                        "num_predict": 50
                    }
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                generated_text = result.get('response', '').strip()
                
                # Clean up the response
                if generated_text:
                    # Extract just the commit message
                    lines = generated_text.split('\n')
                    for line in lines:
                        line = line.strip()
                        if line and not line.startswith('Commit message:'):
                            # Remove quotes if present
                            line = line.strip('"\'')
                            # Ensure it follows conventional commit format
                            if ':' in line and len(line) <= 72:
                                return line
                            elif len(line) <= 50:
                                # Try to format it as conventional commit
                                if not any(line.lower().startswith(t + ':') for t in ['feat', 'fix', 'docs', 'style', 'refactor', 'test', 'chore']):
                                    return f"feat: {line.lower()}"
                                return line
                    
                    # If no good line found, use the first part
                    first_line = lines[0].strip().strip('"\'')
                    if len(first_line) <= 50:
                        return first_line
            
            return None
            
        except Exception as e:
            print(f"❌ Ollama generation failed: {e}")
            return None
    
    def try_alternative_apis(self, prompt: str, hf_token: Optional[str]) -> Optional[str]:
        """Try local LLM and other alternative APIs"""
        # Try local Ollama LLM first
        try:
            print("🔄 Trying local LLM (Ollama)...")
            result = self.generate_with_ollama(prompt)
            if result:
                return result
        except Exception as e:
            print(f"⚠️ Local LLM failed: {str(e)[:50]}")
        
        # Try OpenAI if available
        try:
            if self.openai_client or self.setup_openai_client():
                print("🔄 Trying OpenAI API...")
                
                response = self.openai_client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "You are a git expert. Generate concise, conventional commit messages following the format 'type: description'. Types include feat, fix, docs, style, refactor, test, chore."},
                        {"role": "user", "content": f"Generate a git commit message for these changes:\n{prompt[:800]}"}
                    ],
                    max_tokens=50,
                    temperature=0.5
                )
                
                if response.choices and response.choices[0].message:
                    commit_msg = response.choices[0].message.content.strip()
                    if commit_msg:
                        commit_msg = commit_msg.strip('"\'')
                        commit_msg = commit_msg[:72]
                        print(f"✅ OpenAI generated: {commit_msg}")
                        return commit_msg
        except Exception as e:
            print(f"⚠️ OpenAI failed: {str(e)[:50]}")
        
        return None
    
    def try_simple_text_generation(self, prompt: str, hf_token: Optional[str]) -> Optional[str]:
        """Try simple pattern-based generation as last resort before fallback"""
        try:
            print("🔄 Using pattern-based generation...")
            
            # Extract key information from git diff
            diff_lower = prompt.lower()
            
            # Look for specific patterns
            if '+def ' in diff_lower or '+class ' in diff_lower:
                return "feat: add new functionality"
            elif 'requirements' in diff_lower or 'package' in diff_lower:
                return "chore: update dependencies"
            elif '+import' in diff_lower:
                return "feat: add new imports and functionality"
            elif 'fix' in diff_lower or 'bug' in diff_lower:
                return "fix: resolve issues"
            elif 'test' in diff_lower:
                return "test: add or update tests"
            elif '.md' in diff_lower:
                return "docs: update documentation"
            else:
                return "chore: update code"
                
        except Exception:
            return None
    
    def extract_commit_message(self, generated_text: str, git_diff: str) -> Optional[str]:
        """Extract and clean commit message from generated text"""
        try:
            # Clean up the generated text
            text = generated_text.replace(git_diff[:500], "").strip()
            
            # Look for patterns that indicate a commit message
            lines = text.split('\n')
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                    
                # Check if line looks like a commit message
                if any(line.lower().startswith(t + ':') for t in ['feat', 'fix', 'docs', 'style', 'refactor', 'test', 'chore']):
                    return line[:72]  # Limit to 72 characters
                    
                # Check if line has commit-like structure
                if ':' in line and len(line) < 80 and not line.startswith('http'):
                    return line[:72]
            
            # If no good commit message found, create one from the first meaningful line
            for line in lines:
                line = line.strip()
                if len(line) > 10 and len(line) < 100 and not line.startswith('Generate'):
                    # Try to format it as a commit message
                    if not line.lower().startswith(('feat', 'fix', 'docs', 'style', 'refactor', 'test', 'chore')):
                        line = f"feat: {line.lower()}"
                    return line[:72]
            
            return None
            
        except Exception:
            return None
    
    def generate_fallback_message(self, git_diff: str) -> str:
        """Generate a basic commit message using simple analysis (NO AI REQUIRED)"""
        try:
            # Simple keyword-based analysis
            diff_lines = git_diff.lower().split('\n')
            
            # Count changes
            added_lines = sum(1 for line in diff_lines if line.startswith('+') and not line.startswith('+++'))
            removed_lines = sum(1 for line in diff_lines if line.startswith('-') and not line.startswith('---'))
            
            # Detect file types and changes
            change_types = set()
            
            for line in diff_lines:
                if ('def ' in line or 'class ' in line) and line.startswith('+'):
                    change_types.add('feat')
                elif 'fix' in line or 'bug' in line:
                    change_types.add('fix')
                elif 'import' in line and line.startswith('+'):
                    change_types.add('feat')
                elif 'test' in line:
                    change_types.add('test')
                elif '.md' in git_diff or 'readme' in git_diff.lower():
                    change_types.add('docs')
                elif 'requirements' in git_diff.lower() or 'package' in git_diff.lower():
                    change_types.add('chore')
            
            # Determine primary change type
            if 'feat' in change_types:
                commit_type = 'feat'
            elif 'fix' in change_types:
                commit_type = 'fix'
            elif 'test' in change_types:
                commit_type = 'test'
            elif 'docs' in change_types:
                commit_type = 'docs'
            elif 'chore' in change_types:
                commit_type = 'chore'
            else:
                commit_type = 'chore'
            
            # Generate message based on detected patterns
            if 'huggingface' in git_diff.lower() or 'hf' in git_diff.lower():
                return "feat: add Hugging Face integration for auto-commit messages"
            elif 'openai' in git_diff.lower():
                return "feat: add AI-powered commit message generation"
            elif 'requirements' in git_diff.lower():
                return "chore: update dependencies"
            elif 'main.py' in git_diff and added_lines > 50:
                return "feat: implement major functionality updates"
            elif added_lines > removed_lines * 2:
                return f"{commit_type}: add new features and functionality"
            elif removed_lines > added_lines * 2:
                return f"{commit_type}: remove deprecated code"
            else:
                return f"{commit_type}: update and improve codebase"
                
        except Exception:
            return "chore: update codebase"
    
    def authenticate_descope(self, email: Optional[str] = None, force: bool = False) -> bool:
        
        if not self.descope_client:
            print("Descope client not initialized")
            return False
        if not force and 'descope_session_token' in self.config and 'user_email' in self.config:
            print(f"Already authenticated as: {self.config['user_email']}")

            try:

                session_token = self.config['descope_session_token']
                return self.setup_github_connection()
            except Exception as e:
                print(f"Existing session invalid: {e}")
        if not email:
            email = input("\n📧 Enter your email address: ")
        
        print(f"\n Descope Authentication for {email}")
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
            current_branch_result = subprocess.run(['git', 'rev-parse', '--abbrev-ref', 'HEAD'], capture_output=True, text=True, check=True)
            current_branch = current_branch_result.stdout.strip()
            current_branch_result = subprocess.run(['git', 'rev-parse', '--abbrev-ref', 'HEAD'], capture_output=True, text=True, check=True)
            current_branch = current_branch_result.stdout.strip()
            subprocess.run(['git', 'push', 'origin', current_branch], check=True)
            branch = current_branch
            branch = current_branch
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
        
        # Ollama status
        if self.check_ollama_running():
            models = self.get_available_models()
            preferred = self.config.get('preferred_model', 'None')
            print(f"🤖 Ollama: Running ({len(models)} models available)")
            print(f"🎯 Preferred model: {preferred}")
        else:
            print("🤖 Ollama: Not running (install from https://ollama.ai)")
        
        # Git status
        try:
            result = subprocess.run(['git', 'status', '--porcelain'], capture_output=True, text=True)
            if result.returncode == 0:
                if result.stdout.strip():
                    print(f"📝 Git: {len(result.stdout.strip().split())} uncommitted files")
                else:
                    print("✅ Git: Working directory clean")
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
  %(prog)s commit --auto
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
    commit_parser.add_argument('message', nargs='?', help='Commit message (optional if using --auto)')
    commit_parser.add_argument('--auto', action='store_true', help='Generate commit message automatically using ChatGPT')
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
        
        message = args.message
        
        # Handle auto commit message generation
        if args.auto:
            print("🤖 Generating commit message automatically...")
            git_diff = cli.get_git_diff()
            if not git_diff:
                print("❌ No changes detected for commit message generation")
                sys.exit(1)
            
            generated_message = cli.generate_commit_message(git_diff)
            if not generated_message:
                print("❌ Failed to generate commit message")
                sys.exit(1)
            
            print(f"🎆 Generated commit message: {generated_message}")
            
            # Ask user to confirm the generated message
            confirm = input("\nUse this commit message? (y/n/edit): ").strip().lower()
            if confirm == 'n':
                print("❌ Commit cancelled")
                sys.exit(1)
            elif confirm == 'edit':
                message = input(f"Edit message [{generated_message}]: ").strip()
                if not message:
                    message = generated_message
            else:
                message = generated_message
        
        elif not message:
            print("❌ Commit message is required when not using --auto")
            sys.exit(1)
        
        if not cli.commit_and_push(message, args.branch):
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
