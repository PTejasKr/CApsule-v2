import sys
import os
import argparse
import asyncio
import httpx

API_BASE_URL = os.environ.get("CAPSULE_API_URL", "http://localhost:8000/api")

async def analyze_pr_cli(repo: str, pr_number: int):
    print(f"Triggering analysis for {repo} PR #{pr_number}...")
    async with httpx.AsyncClient() as client:
        try:
            res = await client.post(
                f"{API_BASE_URL}/webhook/github",
                json={
                    "action": "opened",
                    "number": pr_number,
                    "pull_request": {},
                    "repository": {"full_name": repo}
                },
                headers={"X-GitHub-Event": "pull_request"}
            )
            print(f"Response: {res.status_code}")
            print(res.text)
        except Exception as e:
            print(f"Error: {e}")

def main():
    parser = argparse.ArgumentParser(description="Capsule CLI Tooling")
    subparsers = parser.add_subparsers(dest="command")
    
    # analyze command
    analyze_parser = subparsers.add_parser("analyze", help="Trigger a PR analysis")
    analyze_parser.add_parser("repo", help="Repository full name (e.g., owner/repo)")
    analyze_parser.add_parser("pr_number", type=int, help="PR Number")
    
    args = parser.parse_args()
    
    if args.command == "analyze":
        # Hack to grab args dynamically since we just added subparser positional args roughly
        repo = sys.argv[2]
        pr = int(sys.argv[3])
        asyncio.run(analyze_pr_cli(repo, pr))
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
