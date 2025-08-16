from descope import DescopeClient
from github import GitHub
DESCOPE_PROJECT_ID = "P31M5kW4iiyEZQEnVzT8wSOjviwy"
DESCOPE_MANAGEMENT_KEY = "P2DA3QqyF3N3BlmIqn1nr0LMFhrw:K31M7dAsZ3ZPw7Ux0YvZgGNmHtL79dyfXvR6GJncQwQ83tDgIvMzZv9W24z2WmrskEYejLT"

try:
    # Initialize the client with both the ID and the secret key
    descope_client = DescopeClient(
        project_id=DESCOPE_PROJECT_ID,
        management_key=DESCOPE_MANAGEMENT_KEY
    )
    print("✅ Descope client initialized successfully!")

except Exception as e:
    print(f"❌ Error initializing Descope client: {e}")