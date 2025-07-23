from flask import Flask, redirect, request, session, url_for
import requests
from requests.auth import HTTPBasicAuth
import os

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET", "change-this-secret")  # Must set in prod!

CLIENT_ID = "1395730172250034257"
CLIENT_SECRET = "uxPEpXUOU27uir2oSxfT75CDjuuaKY6f"
REDIRECT_URI = "http://127.0.0.1:5000/callback"

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

if __name__ == "__main__":
    app.run(debug=True)