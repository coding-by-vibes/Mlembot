# 🤖 Mlembot — AI-Powered Discord Summarizer Bot

A Discord bot that summarizes articles, YouTube videos, and answers questions using DeepSeek and OpenAI.

It utilizes a DeepSeek API for summarization due to its lower token cost and OpenAI for questions, however you can change these to whatever models you'd like :)

Note: This bot was made mostly with ChatGPT and Cursor as a test to see if it could produce working code

[Like this project? Buy me a coffee!](https://buymeacoffee.com/vibecoding)

---

## 🚀 Features

- `/summarize` — Summarize any article or YouTube link with DeepSeek
- `/ask` — Chat with the bot using OpenAI (remembers your conversation)
- `/recipe` — Detect and return structured recipes from text or URLs (WIP)
- `/wipeconvo` — Clear your conversation history

---

## 🛠 Setup Instructions

### 1. Clone the repo and install dependencies

```bash
git clone https://github.com/coding-by-vibes/Mlembot.git  # Replace <repo-url> with the actual repository URL once on GitHub
cd mlembot          # Replace mlembot with your project's root directory name if different
python -m venv mlembot-env # Using a more distinct venv name like mlembot-env is often clearer
mlembot-env\Scripts\activate  # On Windows PowerShell/cmd
# source mlembot-env/bin/activate # On Linux/macOS/Git Bash
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Copy the `.env.example` file to `.env`:

```bash
# On Windows cmd:
copy .env.example .env
# On Windows PowerShell or Linux/macOS:
cp .env.example .env
```

Edit the `.env` file and add your specific API keys and tokens:

```dotenv
DISCORD_TOKEN=YOUR_DISCORD_BOT_TOKEN
OPENAI_API_KEY=YOUR_OPENAI_API_KEY
DEEPSEEK_API_KEY=YOUR_DEEPSEEK_API_KEY
# Add any other required variables based on .env.example
```

### 3. Run the Bot

Execute the startup script:

```bash
./start_bot.bat
```

---
