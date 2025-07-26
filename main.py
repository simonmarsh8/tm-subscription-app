import os
import stripe  # Make sure this is at the top if not already
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

from flask import Flask, redirect, request, session, url_for
import requests
from requests.auth import HTTPBasicAuth
import os

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET", "change-this-secret")  # Must set in prod!

CLIENT_ID = "1395730172250034257"
CLIENT_SECRET = "uxPEpXUOU27uir2oSxfT75CDjuuaKY6f"
REDIRECT_URI = "https://tm-subscription-app.onrender.com/callback"

MONTHLY_LINK = "https://buy.stripe.com/bJe5kC4cK22O1Bm1G78k800"
QUARTERLY_LINK = "https://buy.stripe.com/bJe9AS38G4aW4NygB18k801"

def build_oauth_url(plan):
    state = plan
    return (
        f"https://discord.com/api/oauth2/authorize"
        f"?client_id={CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URI}"
        f"&response_type=code"
        f"&scope=identify"
        f"&state={state}"
    )

@app.route("/monthly")
def login_monthly():
    return f'<a href="{build_oauth_url("monthly")}">Login with Discord for Monthly Plan</a>'

@app.route("/quarterly")
def login_quarterly():
    return f'<a href="{build_oauth_url("quarterly")}">Login with Discord for Quarterly Plan</a>'

@app.route("/callback")
def callback():
    code = request.args.get("code")
    state = request.args.get("state")
    if not code or state not in ("monthly", "quarterly"):
        return "Error: authentication failed or missing plan.", 400

    # Exchange code for token
    token_resp = requests.post(
        "https://discord.com/api/oauth2/token",
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": REDIRECT_URI,
        },
        auth=HTTPBasicAuth(CLIENT_ID, CLIENT_SECRET),
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    token_resp.raise_for_status()
    access_token = token_resp.json()["access_token"]

    # Fetch Discord user identity
    user_resp = requests.get(
        "https://discord.com/api/users/@me",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    user_resp.raise_for_status()
    discord_id = user_resp.json()["id"]

    # Choose the right Stripe link
    stripe_base = MONTHLY_LINK if state == "monthly" else QUARTERLY_LINK
    stripe_url = f"{stripe_base}?client_reference_id={discord_id}"

    return redirect(stripe_url)
def assign_discord_role(discord_id):
    print(f"Assigning Discord role to user {discord_id}")
    # You'll replace this with actual bot logic later

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

@app.route("/webhook", methods=["POST"])
def stripe_webhook():
    payload = request.data
    sig_header = request.headers.get("Stripe-Signature")
    endpoint_secret = os.getenv("STRIPE_WEBHOOK_SECRET")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
    except stripe.error.SignatureVerificationError as e:
        print(f"Webhook signature error: {str(e)}")
        return "Invalid signature", 400

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        discord_id = session.get("client_reference_id")
        if discord_id:
            assign_discord_role(discord_id)  # You’ll define this next

    return "Success", 200
def assign_discord_role(discord_id):
    print(f"Assigning Discord role to user {discord_id}")
    # You'll later replace this with actual Discord bot logic