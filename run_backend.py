import os
import subprocess

def main():
    # Set the working directory to where docker-compose.yml lives
    target_dir = r"c:\Users\punya\Desktop\capsule"
    try:
        os.chdir(target_dir)
        print(f"Changed directory to {target_dir}")
        print("Starting Capsule Backend (Docker Compose)...")
        # Run docker-compose
        subprocess.run(["docker", "compose", "up", "-d", "--build"], check=True)
        print("\nBackend successfully started!")
        input("Press Enter to exit...")
    except Exception as e:
        print(f"Error starting the backend: {e}")
        input("Press Enter to exit...")

if __name__ == "__main__":
    main()
