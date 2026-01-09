# Google Home Notification Setup

## Overview

This guide shows how to get Google Home notifications when your EV charger is offline at 8 PM PST.

## Architecture

```
GitHub Actions (8 PM PST check)
    ↓
IFTTT Webhook
    ↓
Google Assistant Routine
    ↓
Google Home Broadcast
```

## Step 1: Create IFTTT Account

1. Go to https://ifttt.com
2. Sign up or log in with your Google account
3. This will connect to your Google Home devices

## Step 2: Get IFTTT Webhook Key

1. Go to https://ifttt.com/maker_webhooks
2. Click **Documentation**
3. Copy your webhook key (looks like: `dA9xJ7K2mN4pQ8rT6vY1`)

## Step 3: Create IFTTT Applet

### Create the Trigger:

1. Go to https://ifttt.com/create
2. Click **If This**
3. Search for "Webhooks" and select it
4. Choose **Receive a web request**
5. Event Name: `charger_offline`
6. Click **Create trigger**

### Create the Action:

1. Click **Then That**
2. Search for "Google Assistant" and select it
3. Choose **Say a phrase with a text ingredient**
4. Configure the action:
   - **What do you want to say?**: `{{Value1}}`
   - **Additional Text (Optional)**: `{{Value2}}. {{Value3}}`
   
   Or use a simpler format:
   - **What do you want to say?**: `Alert! Your electric vehicle charger is offline. Please check the charger connection.`

5. Click **Create action**
6. Click **Finish**

### Alternative: Use Broadcast Action

If available in your region:

1. Search for "Google Assistant" → **Broadcast a message**
2. Message: `Your EV charger is offline. Last seen {{Value2}}. {{Value3}}`
3. This will broadcast to ALL Google Home devices in your home

## Step 4: Add Webhook Key to GitHub Secrets

```bash
cd '/Users/scerruti/cph50 control'
gh secret set IFTTT_WEBHOOK_KEY --body "YOUR_WEBHOOK_KEY_HERE"
```

Or manually:
1. Go to https://github.com/scerruti/cph50-control/settings/secrets/actions
2. Click **New repository secret**
3. Name: `IFTTT_WEBHOOK_KEY`
4. Value: Your webhook key from Step 2
5. Click **Add secret**

## Step 5: Deploy and Test

### Push the workflow:

```bash
cd '/Users/scerruti/cph50 control'
git add .github/workflows/nightly-charger-check.yml GOOGLE_HOME_SETUP.md
git commit -m "Add nightly charger check with Google Home notifications"
git push
```

### Test immediately:

1. Go to https://github.com/scerruti/cph50-control/actions
2. Click **Nightly Charger Check (8 PM PST)**
3. Click **Run workflow** → **Run workflow**
4. Wait ~30 seconds
5. Your Google Home should announce the message!

### Manual webhook test:

```bash
curl -X POST https://maker.ifttt.com/trigger/charger_offline/with/key/YOUR_KEY_HERE \
  -H "Content-Type: application/json" \
  -d '{
    "value1": "Test message",
    "value2": "This is a test",
    "value3": "From your terminal"
  }'
```

You should hear the message on your Google Home devices immediately.

## How It Works

1. **GitHub Actions runs at 8 PM PST daily** (cron: `0 4,5 * * *` covers PST and PDT)
2. **Script checks the time** - only proceeds if it's exactly 8 PM Pacific time
3. **Authenticates to ChargePoint** and fetches charger status
4. **If charger is offline**:
   - Sends webhook to IFTTT with charger details
   - IFTTT triggers Google Assistant routine
   - Google Home broadcasts message to all devices
5. **If charger is online**: Exits silently (no notification)

## Customizing the Message

Edit the IFTTT applet to change what Google Home says:

### Friendly reminder:
> "Hey there! Just a heads up - your electric vehicle charger appears to be offline. You might want to check the connection before bedtime."

### Urgent alert:
> "Attention! Your EV charger is offline. This means your car won't charge overnight. Please check the charger immediately."

### With details:
> "EV charger alert. {{Value1}}. {{Value2}}. {{Value3}}."

## Troubleshooting

### Google Home doesn't broadcast:

1. **Check IFTTT Activity**: https://ifttt.com/activity
   - Verify the applet ran successfully
2. **Check Google Assistant permissions**: 
   - Open Google Home app
   - Settings → More settings → Your services → IFTTT
   - Make sure it's connected
3. **Try manual test webhook** (see above)
4. **Check Google Home isn't in Do Not Disturb mode**

### Webhook not triggering:

1. Check GitHub Actions logs for errors
2. Verify `IFTTT_WEBHOOK_KEY` secret is set correctly
3. Test webhook URL manually with curl
4. Check IFTTT applet is enabled (not paused)

### Wrong timezone:

The script automatically handles PST/PDT transitions. It only runs notifications when the local Pacific time is exactly 8 PM (hour == 20).

## Alternative: Native Google Home Integration

If you prefer not to use IFTTT, here are alternatives:

### Option 1: Home Assistant
- Install Home Assistant (self-hosted)
- Use GitHub webhook → Home Assistant → Google Home
- More complex but more control

### Option 2: ntfy.sh (free push, no account)
- Create a topic name, e.g., `cph50-alerts`
- Add repo secret: `NTFY_TOPIC` = your topic name (e.g., `cph50-alerts`)
- (Optional) `NTFY_URL` if self-hosting; otherwise defaults to https://ntfy.sh
- Install ntfy app on phone and subscribe to the topic; or open https://ntfy.sh/cph50-alerts in a browser to receive
- The nightly workflow will push “EV charger offline” when offline at 8 PM

### Option 3: Pushover
- Requires Pushover account; add secrets `PUSHOVER_TOKEN`, `PUSHOVER_USER`
- We can wire this in if you prefer

### Option 4: Email
- Already configured via `ALERT_EMAIL` secret
- Not as immediate as Google Home broadcast
- Can use email-to-SMS gateways (e.g., vtext.com, tmomail.net)

## Schedule Details

The workflow runs at:
- **4:00 AM UTC** = 8:00 PM PST (November - March, Standard Time)
- **5:00 AM UTC** = 8:00 PM PDT (March - November, Daylight Time)

Both times are scheduled, but the script only proceeds when Pacific local time is exactly 8 PM.

## Cost

- **IFTTT**: Free tier allows unlimited applet runs
- **GitHub Actions**: Well within free tier (< 2 minutes/day)
- **Total**: $0/month

## Privacy & Security

- Webhook key is stored securely in GitHub Secrets (encrypted)
- IFTTT only receives generic charger status info
- No personal data or location shared
- Google Assistant integration uses your existing Google account permissions
