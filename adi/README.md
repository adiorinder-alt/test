# GitHub CLI Authentication and Commit Tool with Descope

A powerful command-line interface for GitHub authentication and repository management using Descope for secure user authentication. This CLI tool simplifies the process of authenticating users via Descope (OTP/Magic Link), connecting to GitHub, creating repositories, and managing commits.

## Features

- 🔐 **Descope Authentication**: Secure user authentication using OTP or Magic Link
- 🐙 **GitHub Integration**: Connect to GitHub with Personal Access Tokens after Descope auth
- 📁 **Repository Management**: Create new repositories or connect to existing ones
- 🚀 **Automated Commits**: Add, commit, and push changes with a single command
- 📊 **Status Monitoring**: View current Descope and GitHub authentication status
- 🔧 **Configuration Management**: Persistent configuration storage

## Installation

1. **Clone or download this repository**
2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   # or if using uv:
   uv sync
   ```

3. **Make the script executable** (optional):
   ```bash
   chmod +x main.py
   ```

## Quick Start

1. **Authenticate with Descope and GitHub**:
   ```bash
   python main.py auth
   ```
   This process involves two steps:
   - First: Authenticate with Descope using your email (via OTP or Magic Link)
   - Second: Connect to GitHub with a Personal Access Token (repo, user scopes)
   
   Create GitHub token at: https://github.com/settings/tokens

2. **Initialize a repository**:
   ```bash
   python main.py init my-awesome-project
   ```

3. **Commit and push changes**:
   ```bash
   python main.py commit "Initial commit"
   ```

4. **Check status**:
   ```bash
   python main.py status
   ```

## Commands

### Authentication
```bash
# Authenticate with Descope and GitHub (interactive)
python main.py auth

# Authenticate with a specific email address
python main.py auth --email user@example.com

# Force re-authentication (both Descope and GitHub)
python main.py auth --force
```

**Authentication Flow:**
1. Enter email address for Descope authentication
2. Choose between Magic Link (email) or OTP (email) authentication
3. Complete Descope authentication via email
4. **Automatic GitHub Token Extraction**: The app attempts to extract your GitHub token from the Descope session (if you have configured GitHub OAuth in your Descope project)
5. **Fallback**: If no GitHub token is found in the session, you'll be prompted to enter a GitHub Personal Access Token manually

### Repository Initialization
```bash
# Create/connect to a repository
python main.py init repo-name

# Create a private repository with description
python main.py init my-repo --description "My awesome project" --private
```

### Committing Changes
```bash
# Commit and push all changes
python main.py commit "Your commit message"

# Push to a specific branch
python main.py commit "Feature update" --branch feature-branch
```

### Status Check
```bash
# View current status
python main.py status
```

## Configuration

### Descope Setup

For the automatic GitHub token extraction to work, you need to configure GitHub OAuth in your Descope project:

1. **Create a GitHub OAuth App**:
   - Go to GitHub Settings > Developer settings > OAuth Apps
   - Create a new OAuth App
   - Note the Client ID and Client Secret

2. **Configure Descope**:
   - In your Descope console, go to Authentication Methods
   - Add GitHub as a social login provider
   - Enter your GitHub OAuth App credentials
   - Configure the scopes to include `repo` and `user`

3. **Test the Integration**:
   - Users should be able to sign in with GitHub through Descope
   - The GitHub token should be available in the user's session data

### Local Configuration

The tool stores configuration in `~/.github-cli/config.json`. This includes:
- Descope session tokens
- GitHub authentication token (extracted or manually entered)
- Username and email
- Other preferences

## Security Notes

⚠️ **Important Security Considerations**:
- Your GitHub token is stored locally in plain text
- For production use, consider implementing encrypted storage
- Never commit your token to version control
- Use tokens with minimal required permissions
- Regularly rotate your tokens

## Error Handling

The tool provides clear error messages for common issues:
- Invalid authentication tokens
- Network connectivity problems
- Git repository issues
- Permission errors

## Examples

### Complete Workflow Example
```bash
# 1. First-time setup
python main.py auth

# 2. Create a new project
mkdir my-project && cd my-project
echo "# My Project" > README.md

# 3. Initialize repository
python main.py init my-project --description "My awesome new project"

# 4. Make some changes
echo "print('Hello, World!')" > hello.py

# 5. Commit and push
python main.py commit "Add hello world script"

# 6. Check status
python main.py status
```

### Working with Existing Repository
```bash
# If you already have a local git repo
cd existing-project
python main.py auth  # Authenticate first
python main.py commit "Latest changes"
```

## Troubleshooting

### Common Issues

**Authentication Failed**
- Verify your token has correct permissions (`repo`, `user`)
- Check if the token has expired
- Ensure you're using the correct token

**Repository Creation Failed**
- Check if repository name already exists
- Verify you have permission to create repositories
- Ensure repository name follows GitHub naming conventions

**Push Failed**
- Check if you have write access to the repository
- Verify the branch exists on the remote
- Ensure you're authenticated properly

**Not in a Git Repository**
- Make sure you're in a directory with a git repository
- Use `python main.py init` to initialize if needed

## Development

To contribute to this project:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

MIT License - feel free to use this tool in your projects!

## Support

If you encounter any issues or have suggestions, please open an issue on GitHub.
