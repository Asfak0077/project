# 🚀 Complete AWS Deployment & Hosting Guide for VersusAI

This guide provides step-by-step instructions to host the complete **VersusAI** application on **Amazon Web Services (AWS)** using **AWS EC2 + AWS RDS (MySQL) + Docker + Nginx + SSL**.

---

## 🏗️ Architecture Overview

```
                          [ Internet Users ]
                                  │
                                  ▼
                  [ HTTPS (Port 443) / HTTP (Port 80) ]
                                  │
                      ┌──────────────────────┐
                      │    Nginx Proxy       │
                      │  (Docker Container)  │
                      └──────────┬───────────┘
                                 │
                 ┌───────────────┴───────────────┐
                 │                               │
                 ▼                               ▼
      ┌─────────────────────┐         ┌─────────────────────┐
      │  Next.js Frontend   │         │   FastAPI Backend   │
      │  (Port 3000 Node)   │         │ (Port 8000 Python)  │
      └─────────────────────┘         └──────────┬──────────┘
                                                 │
                                                 ▼
                                      ┌─────────────────────┐
                                      │    AWS RDS MySQL    │
                                      │     (Port 3306)     │
                                      └─────────────────────┘
```

---

## 📋 Recommended AWS Hardware & Specs

| Component | AWS Resource | Recommended Spec | Free Tier Eligible? |
| :--- | :--- | :--- | :--- |
| **Compute / Host** | EC2 Instance | `t3.medium` (2 vCPU, 4GB RAM) or `t3.large` | `t2.micro` works for basic testing; `t3.medium` recommended for RAG embeddings |
| **Database** | RDS for MySQL | `db.t3.micro` or `db.t3.small` (MySQL 8.0) | Yes (`db.t3.micro` 750 hrs/month free for 12 months) |
| **Storage** | EBS Volume | 30 GB gp3 SSD | Yes (30 GB free) |
| **IP Address** | Elastic IP (EIP) | 1 Static IPv4 | Yes (free while attached to EC2) |

---

## 🛠️ STEP 1: Create AWS RDS MySQL Database

1. Log in to the **AWS Management Console** and navigate to **RDS**.
2. Click **Create database**.
3. Choose **Standard create** $\rightarrow$ **MySQL** (version 8.0.35 or higher).
4. Template: Select **Free Tier** or **Production**.
5. **Settings:**
   - **DB instance identifier:** `versus-ai-mysql`
   - **Master username:** `admin`
   - **Master password:** `SetAStrongPassword123!` (save this!)
6. **Instance configuration:** `db.t3.micro` (or `db.t3.small`).
7. **Storage:** 20 GB gp3 with storage autoscaling enabled.
8. **Connectivity:**
   - **Public access:** Choose **Yes** (or connect via VPC security group).
   - **VPC security group:** Select **Create new** $\rightarrow$ Name: `versus-ai-rds-sg`.
9. **Additional configuration:**
   - **Initial database name:** `my_project`
10. Click **Create database**.
11. Once the status changes to **Available**, copy the **Endpoint** (e.g., `versus-ai-mysql.c123456789.us-east-1.rds.amazonaws.com`).

> **Security Group Inbound Rule:**
> In EC2 Security Groups, select `versus-ai-rds-sg` $\rightarrow$ Edit Inbound Rules $\rightarrow$ Add Type: **MySQL/Aurora (Port 3306)** $\rightarrow$ Source: `0.0.0.0/0` (or your EC2 Security Group ID).

---

## 🖥️ STEP 2: Launch AWS EC2 Instance

1. Navigate to **EC2** $\rightarrow$ Click **Launch Instance**.
2. **Name:** `VersusAI-Production-Server`.
3. **OS Image (AMI):** **Ubuntu Server 24.04 LTS (HVM)**, 64-bit (x86).
4. **Instance Type:** `t3.medium` (recommended) or `t3.small`.
5. **Key pair (login):** Select or create a new key pair (e.g. `versus-ai-key.pem`).
6. **Network Settings (Security Group):**
   - Allow **SSH traffic** from `Anywhere` (or My IP) - Port `22`
   - Allow **HTTP traffic from the internet** - Port `80`
   - Allow **HTTPS traffic from the internet** - Port `443`
7. **Storage:** Change size from 8 GB to **30 GB gp3**.
8. Click **Launch Instance**.
9. **Allocate Elastic IP (Static IP):**
   - Go to **EC2 $\rightarrow$ Elastic IPs** $\rightarrow$ **Allocate Elastic IP address**.
   - Select the allocated IP $\rightarrow$ **Actions $\rightarrow$ Associate Elastic IP address** $\rightarrow$ Select your `VersusAI-Production-Server` instance.

---

## 💻 STEP 3: Connect to EC2 & Deploy

### 1. SSH into your EC2 Instance
From your local terminal:
```bash
chmod 400 versus-ai-key.pem
ssh -i "versus-ai-key.pem" ubuntu@<YOUR-EC2-PUBLIC-IP>
```

### 2. Clone the Project
```bash
git clone https://github.com/your-username/your-repo.git versus-ai
cd versus-ai
```
*(Or upload your project files directly using `scp -i versus-ai-key.pem -r . ubuntu@<YOUR-EC2-PUBLIC-IP>:~/versus-ai`)*

### 3. Configure Environment Variables
Create your production `.env` file:
```bash
cp .env.production.example .env
nano .env
```

Fill in your actual AWS RDS endpoint and credentials:
```env
# AWS RDS MySQL Database
DB_HOST=versus-ai-mysql.xxxxxx.us-east-1.rds.amazonaws.com
DB_PORT=3306
DB_USER=admin
DB_PASSWORD=SetAStrongPassword123!
DB_NAME=my_project

# Full SQLAlchemy Connection URL
DATABASE_URL=mysql+pymysql://admin:SetAStrongPassword123!@versus-ai-mysql.xxxxxx.us-east-1.rds.amazonaws.com:3306/my_project?charset=utf8mb4

# Security & Keys
JWT_SECRET=production_secret_jwt_key_987654321
ACCESS_TOKEN_EXPIRE_MINUTES=10080
LLM_API_KEY=your_gemini_api_key_here

# Domain / Public URL
DOMAIN=your-domain.com
NEXT_PUBLIC_API_URL=/api
```

### 4. Run the Automated 1-Click Deployment Script
```bash
chmod +x deploy-aws-ec2.sh
./deploy-aws-ec2.sh
```

The script will automatically:
- Install Docker and Docker Compose plugin.
- Configure Linux firewall (UFW) for ports 22, 80, and 443.
- Build production multi-stage Docker images for Next.js and FastAPI.
- Start all containers in the background with auto-restart.

---

## 🔒 STEP 4: Attach Domain & Enable Free SSL (HTTPS)

### 1. Point Your Domain DNS
Go to your DNS provider (AWS Route 53, Cloudflare, GoDaddy, Namecheap):
- Add an **A Record**:
  - **Host / Name:** `@` (or `versus`)
  - **Value / Target:** `<YOUR-EC2-ELASTIC-IP>`
- Add a **CNAME Record**:
  - **Host / Name:** `www`
  - **Value / Target:** `yourdomain.com`

### 2. Install Let's Encrypt SSL with Certbot
On your EC2 terminal:
```bash
sudo apt-get install -y certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com
```
Follow the prompt, enter your email, and accept terms. Certbot will configure SSL certificates and auto-renewal.

---

## 📊 STEP 5: Useful Production Commands

| Action | Command |
| :--- | :--- |
| **Check running containers** | `docker compose ps` |
| **View real-time logs** | `docker compose logs -f` |
| **View backend logs only** | `docker compose logs -f backend` |
| **View frontend logs only** | `docker compose logs -f frontend` |
| **Restart application** | `docker compose restart` |
| **Rebuild & update code** | `git pull && docker compose up -d --build` |
| **Stop application** | `docker compose down` |

---

## ☁️ Alternative: AWS App Runner / ECS (Serverless Containers)

If you prefer a fully managed container service without managing an EC2 virtual machine:

1. **Build & Push Docker Images to Amazon ECR (Elastic Container Registry):**
   ```bash
   aws ecr create-repository --repository-name versusai-backend
   docker tag versusai-backend:latest <AWS_ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/versusai-backend:latest
   docker push <AWS_ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/versusai-backend:latest
   ```
2. **Deploy Backend to AWS App Runner:**
   - Select ECR image `<AWS_ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/versusai-backend:latest`.
   - Set Port `8000`, Environment variables (`DATABASE_URL`, `LLM_API_KEY`, etc.).
   - App Runner provides automatic HTTPS, load balancing, and auto-scaling.
3. **Deploy Frontend to AWS Amplify or Vercel:**
   - Connect repository `frontend/my-app`.
   - Set environment variable `NEXT_PUBLIC_API_URL=https://<your-app-runner-url>/api`.

---

## 🩺 Verifying Deployment

Once deployed, visit your domain or EC2 Public IP:
- **Web Application:** `http://<YOUR-EC2-PUBLIC-IP>` (or `https://yourdomain.com`)
- **FastAPI OpenAPI Documentation:** `http://<YOUR-EC2-PUBLIC-IP>/docs`
- **System Health Check:** `http://<YOUR-EC2-PUBLIC-IP>/api/health`
- **RAG Engine Status:** `http://<YOUR-EC2-PUBLIC-IP>/api/rag/health`
