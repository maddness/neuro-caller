### Quick Setup

#### 1. Open Terminal

Press `Cmd + Space`, type `Terminal`, press Enter.

#### 2. Go to home folder

```bash
cd
```

#### 3. Clone the repository

```bash
git clone https://github.com/maddness/neuro-caller.git
```

#### 4. Configure secrets

Create `.env` file:

```bash
cp neuro-caller/.env.example neuro-caller/.env
```

Open it in Finder:

```bash
open neuro-caller/.env
```

The file will open in TextEdit. Find and fill in these lines.
Text кому:aostrikov to get tokens.

```
TELEGRAM_BOT_TOKEN=your_botfather_token
TELEGRAM_CHAT_ID=your_chat_id
S3_ACCESS_KEY_ID=your_s3_key
S3_SECRET_ACCESS_KEY=your_s3_secret
S3_BUCKET_NAME=your_bucket_name
TRACKER_OAUTH_TOKEN=your_tracker_token
```

Save: `Cmd + S`, close the file.

#### 5. Run

Go back to Terminal and execute:

```bash
cd neuro-caller
./start.sh
```

Done! Connect a voice recorder — you'll get a Telegram notification to the chat.

---

**Stop**: `Ctrl + C` in Terminal

**Run again**: `cd ~/neuro-caller && ./start.sh`