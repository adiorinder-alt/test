def main():
    print("🚀 GitHub CLI Tool Demo with Descope Authentication")
    print("=" * 50)
    
    print("\n1. This is a sample Python file that could be committed to GitHub")
    print("2. To use the GitHub CLI tool with Descope authentication:")
    print("   - First authenticate with Descope: uv run python main.py auth")
    print("     (This will ask for email and use OTP or Magic Link)")
    print("   - Then connect to GitHub with a Personal Access Token")
    print("   - Initialize a repo: uv run python main.py init my-demo-repo")
    print("   - Commit changes: uv run python main.py commit 'Add demo script'")
    print("   - Check status: uv run python main.py status")
    print("\n🔐 Authentication Flow:")
    print("   1. Enter email for Descope authentication")
    print("   2. Choose OTP (email code) or Magic Link (email link)")
    print("   3. Complete Descope authentication")
    print("   4. Enter GitHub Personal Access Token")
    numbers = [1, 2, 3, 4, 5]
    squares = [x**2 for x in numbers]
    print(f"\n📊 Demo calculation: Squares of {numbers} = {squares}")
    
    return "Demo completed successfully! ✅"

if __name__ == "__main__":
    result = main()
    print(f"\n{result}")
