# 🤖 OrchestrAI — Autonomous Career Agent

> Autonomously fetches AI & Data Science internships daily, stores them in a GitHub-hosted YAML database, and delivers a structured email report every morning at **9:30 AM IST**.

---

## 🔁 How It Works

```
Local Computer → GitHub (Code + YAML DB) → Render (Cloud Worker) → Gmail (Daily Email)
```

| Stage | What Happens |
|---|---|
| **Fetch** | Scrapes Internshala, LinkedIn, Unstop for AI/ML/Data internships |
| **Filter** | GPT-3.5 (or keyword fallback) filters relevant roles only |
| **Store** | Writes deduplicated jobs to `orchestrai-db` GitHub repo as YAML |
| **Email** | Sends a rich HTML report to your inbox at 9:30 AM IST daily |

---

## 📁 Project Structure

```
MultiAgent_Project/
├── main.py                  # Entry point — validates env, starts scheduler
├── Procfile                 # Render: runs `python main.py` as background worker
├── requirements.txt         # Python dependencies
├── .env.example             # Environment variable template (no secrets)
├── .gitignore               # Blocks .env from being committed
└── backend/
    ├── scheduler.py         # APScheduler — cron trigger at 9:30 AM IST
    ├── email_service.py     # SMTP / Gmail HTML email sender
    ├── github_db.py         # GitHub REST API — reads/writes jobs.json
    ├── github_yaml_db.py    # GitHub REST API — reads/writes YAML files
    └── agents/
        └── career_agent.py  # Core agent — fetch, filter, store, notify
```

---

## ⚙️ Setup

### 1. Clone the repo
```bash
git clone https://github.com/YOUR_USERNAME/orchestrai-agent.git
cd orchestrai-agent
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure environment variables
```bash
cp .env.example .env
# Edit .env with your actual credentials
```

| Variable | Description |
|---|---|
| `GITHUB_TOKEN` | Personal Access Token with `repo` scope → [generate here](https://github.com/settings/tokens) |
| `GITHUB_USERNAME` | Your GitHub username |
| `GITHUB_REPO` | `username/orchestrai-db` (the data repo) |
| `GITHUB_BRANCH` | `main` |
| `OPENAI_API_KEY` | Optional — GPT-based relevance filter |
| `EMAIL_USER` | Gmail address used to send reports |
| `EMAIL_PASS` | Gmail App Password → [generate here](https://myaccount.google.com/apppasswords) |
| `EMAIL_RECEIVER` | Email address to receive reports |
| `SMTP_HOST` | `smtp.gmail.com` |
| `SMTP_PORT` | `587` |

### 4. Test locally (runs immediately, no waiting for 9:30 AM)
```bash
python main.py --now
```

---

## ☁️ Deploy on Render

1. Go to [render.com](https://render.com) → **New + → Background Worker**
2. Connect this GitHub repo
3. Set:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python main.py`
4. Add all environment variables in **Render → Environment tab**
5. Deploy → the agent runs daily at 9:30 AM IST automatically

> **Tip:** Choose the **Singapore** region on Render for minimum timezone drift from IST.

---

## 🗄️ GitHub YAML Database

A separate repo (`orchestrai-db`) acts as a cloud database. The agent automatically creates and updates these files:

```
orchestrai-db/
├── jobs.yaml               # All fetched & filtered internships
├── agent_logs.yaml         # Agent activity and error logs
└── execution_history.yaml  # Daily run summaries
```

You only need to **create the empty repo** — the agent handles everything else.

---

## 📧 Sample Email Output

- **Subject:** `Daily AI & Data Science Internship Report`
- **Content:** HTML table with company, role, location, skills badges, and Apply button
- **Sent:** Every day at **9:30 AM IST**
- **Deduplication:** Same job is never emailed twice

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.11+ |
| Scheduling | APScheduler (cron) |
| Scraping | httpx + BeautifulSoup4 |
| AI Filter | OpenAI GPT-3.5-turbo |
| Database | GitHub REST API + YAML |
| Email | smtplib + Gmail SMTP |
| Hosting | Render Background Worker |

---

## 🔒 Security Notes

- `.env` is in `.gitignore` — **never committed**
- Secrets are stored in Render's encrypted environment variables
- GitHub token only needs `repo` scope (read/write to `orchestrai-db`)
- Gmail uses App Password, not your account password

---

## 📄 License

MIT — free to use and modify.
