# AWS EC2 Production Deployment Guide

This document outlines the end-to-end process for taking the Capsule local Docker stack and deploying it to a production-ready AWS EC2 instance. Because Capsule relies on multiple containers (PostgreSQL, Redis, Celery, FastAPI, and Nginx), a dedicated virtual machine (EC2) is the most robust and cost-effective approach.

---

## 1. AWS EC2 Provisioning

1. **Log in to the AWS Management Console** and navigate to **EC2**.
2. Click **Launch Instance**.
3. **Name:** `capsule-production-server`
4. **AMI (Amazon Machine Image):** Select **Ubuntu Server 24.04 LTS** (or 22.04 LTS).
5. **Instance Type:** `t3.small` or `t3.medium` (Recommended: At least 2GB of RAM is required to run the OS, Database, Redis, and AI processing smoothly).
6. **Key Pair:** Create a new RSA key pair (e.g., `capsule-key.pem`) and download it. You will need this to SSH into the server.
7. **Network Settings (Security Groups):** 
   Create a new Security Group with the following Inbound Rules:
   - **SSH (Port 22):** Source: Anywhere (or restrict to your IP for better security).
   - **HTTP (Port 80):** Source: Anywhere (`0.0.0.0/0`)
   - **HTTPS (Port 443):** Source: Anywhere (`0.0.0.0/0`)
8. **Storage:** Increase the Root Volume to at least **20 GB** (gp3).
9. Click **Launch Instance**.

---

## 2. Server Initialization

Once the instance is running, copy its **Public IPv4 address**.

### Connect via SSH
Open your terminal and SSH into the server using the downloaded key:
```bash
chmod 400 capsule-key.pem
ssh -i "capsule-key.pem" ubuntu@<YOUR_EC2_PUBLIC_IP>
```

### Install Docker and Docker Compose
Run the following commands on the EC2 instance to install the required dependencies:
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y apt-transport-https ca-certificates curl software-properties-common git nginx certbot python3-certbot-nginx

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add ubuntu user to the docker group so you don't need sudo for docker commands
sudo usermod -aG docker ubuntu
```
*Note: After running the `usermod` command, log out (`exit`) and log back in to apply the group changes.*

---

## 3. Application Deployment

### Clone the Repository
```bash
git clone https://github.com/PTejasKr/Capsule.git
cd Capsule
```

### Configure Environment Variables
Copy the example environment file and edit it with your production secrets:
```bash
cp .env.example .env
nano .env
```

**Crucial Updates in `.env`:**
- `HOST_URL=https://capsule.yourdomain.com` (Ensure it uses `https://` once SSL is configured).
- Set strong, random strings for `API_KEY`, `JWT_SECRET_KEY`, and `GITHUB_WEBHOOK_SECRET`.
- Fill in your `GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET`, and `GITHUB_APP_PRIVATE_KEY` (formatted securely).
- Ensure `DATABASE_URL` is configured to use the internal Docker PostgreSQL (e.g., `postgresql+asyncpg://postgres:postgres@postgres:5432/capsule`).

### Launch the Stack
```bash
docker compose up -d --build
```
Verify everything is running successfully:
```bash
docker compose ps
```

---

## 4. Domain & SSL Configuration (HTTPS)

GitHub requires HTTPS for Webhooks and OAuth callbacks. You must point a custom domain to your EC2 instance.

1. Go to your Domain Registrar (e.g., Route53, Namecheap, GoDaddy).
2. Create an **A Record** for your domain (e.g., `capsule.yourdomain.com`) pointing to the EC2 **Public IPv4 address**.

### Configure Nginx on the Host
We will use the EC2 host's Nginx to reverse-proxy traffic to the Docker stack and handle SSL certificates via Let's Encrypt.

1. Stop the local Nginx container from docker-compose if it conflicts with the host port 80, or simply map the Docker Nginx to port `8080` in `docker-compose.yml`:
   ```yaml
   nginx:
     ports:
       - "8080:80"
   ```
   *Run `docker compose up -d` again to apply the port change.*

2. Create an Nginx config on the EC2 host:
   ```bash
   sudo nano /etc/nginx/sites-available/capsule
   ```

   **Add the following configuration:**
   ```nginx
   server {
       server_name capsule.yourdomain.com;

       location / {
           proxy_pass http://localhost:8080;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
           proxy_set_header X-Forwarded-Proto $scheme;
       }
   }
   ```

3. Enable the site and restart Nginx:
   ```bash
   sudo ln -s /etc/nginx/sites-available/capsule /etc/nginx/sites-enabled/
   sudo systemctl restart nginx
   ```

### Provision Let's Encrypt SSL
```bash
sudo certbot --nginx -d capsule.yourdomain.com
```
Follow the prompts. Certbot will automatically modify your Nginx configuration to enforce HTTPS.

---

## 5. Update GitHub App Settings

Once your server is live at `https://capsule.yourdomain.com`, update your GitHub App configuration:

1. **Homepage URL:** `https://capsule.yourdomain.com`
2. **Callback URL:** `https://capsule.yourdomain.com/api/auth/github/callback`
3. **Webhook URL:** `https://capsule.yourdomain.com/api/webhook/github`
4. **Webhook Secret:** Ensure it perfectly matches the `GITHUB_WEBHOOK_SECRET` in your EC2 `.env` file.

---

## 6. Maintenance Commands

- **View Backend Logs:** `docker logs capsule-api-server -f`
- **View Celery Worker Logs:** `docker logs capsule-celery-worker -f`
- **Restart the Stack:** `docker compose restart`
- **Update with Latest Code:**
  ```bash
  git pull
  docker compose up -d --build
  ```
