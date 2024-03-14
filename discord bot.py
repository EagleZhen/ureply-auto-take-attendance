import discord
from discord import ButtonStyle, app_commands
from discord.ext import commands
from discord.ui import Button, View
from firebase_admin import credentials, db, initialize_app
import json
from datetime import datetime

# Initialize Firebase Admin SDK
cred = credentials.Certificate("./info/service_account_key.json")
with open("./info/info.json") as f:
    info = json.load(f)
    database_url = info["Database URL"]
    discord_bot_token = info["Discord Bot Token"]
    initialize_app(cred, {"databaseURL": database_url})

bot = commands.Bot(command_prefix="!", intents=discord.Intents.default())

# set up firebase realtime database
ref = db.reference("/")
last_updated_time_ref = ref.child("Last Updated Time")


def publish_answer(current_time, session_id, question_type, ureply_answer):
    ref.child(
        current_time
    ).set(  # push new ureply info to the database with current time as key
        {
            "Session ID": session_id,
            "Question Type": question_type,
            "Ureply Answer": ureply_answer,
        }
    )

    last_updated_time_ref.update(  # update last updated time to current time
        {"Last Updated Time": current_time}
    )


@bot.event
async def on_ready():
    print(f'Logged in as "{bot.user}" ({bot.user.id})')
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} slash commands")
    except Exception as e:
        print(f"Failed to sync slash commands: {e}")


@bot.tree.command(name="ureply")
@app_commands.describe(
    session_id="uReply Session ID - case insensitive",
    question_type='Question Type - "mc" or "typing"',
    ureply_answer="uReply Answers - a/b/c.../z for mc",
)
# restrict the question type to "mc" or "typing" only to prevent invalid input
@app_commands.choices(
    question_type=[
        app_commands.Choice(name="mc", value="mc"),
        app_commands.Choice(name="typing", value="typing"),
    ]
)
async def ureply(
    interaction: discord.Interaction,
    session_id: str,
    question_type: str,
    ureply_answer: str,
):
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    publish_answer(
        current_time=current_time,
        session_id=session_id,
        question_type=question_type,
        ureply_answer=ureply_answer,
    )

    # add a button to the message to allow users to open the uReply link with the session ID quickly
    view = View()
    button = Button(
        label="uReply Link",
        url=f"https://server4.ureply.mobi/student/cads/mobile_login_check.php?sessionid={session_id}",
        style=ButtonStyle.link,
    )
    view.add_item(button)
    
    if (question_type=="typing"): # if the question type is "typing", send the uReply answer in a separate message
        await interaction.response.send_message(
            f"@everyone\n"
            f"- Time: {current_time}\n"
            f"- Session ID: {session_id}\n"
            f"- Question Type: {question_type}\n",
            allowed_mentions=discord.AllowedMentions(everyone=True),
            view=view,
        )

        # send the uReply answer as a separate message so that it can be copied easily
        await interaction.followup.send(f"{ureply_answer}")

    elif (question_type=="mc"): # if the question type is "mc", send the uReply answer in the same message
        await interaction.response.send_message(
            f"@everyone\n"
            f"- Time: {current_time}\n"
            f"- Session ID: {session_id}\n"
            f"- Question Type: {question_type}\n"
            f"- uReply Answer: {ureply_answer}\n",
            allowed_mentions=discord.AllowedMentions(everyone=True),
            view=view,
        )


bot.run(discord_bot_token)
