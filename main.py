import os
import stripe
import requests
from flask import Flask, redirect, request, session
from requests.auth import HTTPBasicAuth

# Stripe setup
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

# Flask setup
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET", "supersecret")

# Discord OAuth & Bot config
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI")
MONTHLY_LINK = os.getenv("MONTHLY_LINK")
QUARTERLY_LINK = os.getenv("QUARTERLY_LINK")

BOT_TOKEN = os.getenv("BOT_TOKEN")
GUILD_ID = os.getenv("GUILD_ID")
ROLE_ID = os.getenv("ROLE_ID")


def build_oauth_url(plan):
    return (
        f"https://discord.com/api/oauth2/authorize"
        f"?client_id={CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URI}"
        f"&response_type=code"
        f"&scope=identify"
        f"&state={plan}"
    )


@app.route("/monthly")
def login_monthly():
    return f'<a href="{build_oauth_url("monthly")}">Login with Discord for Monthly Plan</a>'


@app.route("/quarterly")
def login_quarterly():
    return f'<a href="{build_oauth_url("quarterly")}">Login with Discord for Quarterly Plan</a>'


@app.route("/callback")
def discord_callback():
    code = request.args.get("code")
    state = request.args.get("state")

    if not code or state not in ("monthly", "quarterly"):
        return "Error: missing Discord auth or invalid plan", 400

    # Step 1: Exchange code for access token
    token_resp = requests.post(
        "https://discord.com/api/oauth2/token",
        data={
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": REDIRECT_URI,
        },
        auth=HTTPBasicAuth(CLIENT_ID, CLIENT_SECRET),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )

    token_resp.raise_for_status()
    access_token = token_resp.json()["access_token"]

    # Step 2: Fetch user info
    user_resp = requests.get(
        "https://discord.com/api/users/@me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    user_resp.raise_for_status()
    discord_id = user_resp.json()["id"]

    # Step 3: Add user to server
    add_resp = requests.put(
        f"https://discord.com/api/guilds/{GUILD_ID}/members/{discord_id}",
        headers={
            "Authorization": f"Bot {BOT_TOKEN}",
            "Content-Type": "application/json",
        },
        json={"access_token": access_token},
    )

    if add_resp.status_code not in (201, 204):
        return f"❌ Failed to add user to server: {add_resp.status_code} - {add_resp.text}"

    # Step 4: Redirect to Stripe checkout
    stripe_url = MONTHLY_LINK if state == "monthly" else QUARTERLY_LINK
    return redirect(f"{stripe_url}?client_reference_id={discord_id}")


@app.route("/webhook", methods=["POST"])
def stripe_webhook():
    payload = request.data
    sig_header = request.headers.get("Stripe-Signature")
    endpoint_secret = os.getenv("STRIPE_WEBHOOK_SECRET")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
    except stripe.error.SignatureVerificationError as e:
        print(f"⚠️ Webhook signature verification failed: {e}")
        return "Invalid signature", 400

    if event["type"] == "checkout.session.completed":
        session_data = event["data"]["object"]
        discord_id = session_data.get("client_reference_id")
        if discord_id:
            assign_discord_role(discord_id)

    return "ok", 200


def assign_discord_role(discord_id):
    print(f"Assigning role to user {discord_id}")

    if not all([BOT_TOKEN, GUILD_ID, ROLE_ID]):
        print("❌ Missing environment variables for role assignment.")
        return

    url = f"https://discord.com/api/v10/guilds/{GUILD_ID}/members/{discord_id}/roles/{ROLE_ID}"
    headers = {
        "Authorization": f"Bot {BOT_TOKEN}",
        "Content-Type": "application/json",
    }

    response = requests.put(url, headers=headers)

    if response.status_code in (204, 201):
        print(f"✅ Successfully assigned role to {discord_id}")
    else:
        print(f"❌ Failed to assign role: {response.status_code} — {response.text}")


@app.route("/")
def index():
    return "TM Discord Subscription App is Running!"


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)