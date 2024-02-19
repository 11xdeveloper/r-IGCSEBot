import os
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.environ.get("IGCSEBOT_TOKEN")
LINK = os.environ.get("MONGO_LINK")
BETA = os.environ.get("BETA") != "False"


BOTMAIN = 861445044790886467
BOTBETA = 947857467726000158

# r/IGCSE
GUILD_ID = 576460042774118420
MODLOG_CHANNEL_ID = 894596848357089330
BOTLOG_CHANNEL_ID = 1209121077456933006 if BETA else 1017792876584906782
WELCOME_CHANNEL_ID = 930088940654956575
MODMAIL_LOGS_ID = 1204423423799988314
FORUMTHREAD_ID = 1205148033642397786
CREATEDM_ID = 895961641219407923
DMS_CLOSED_CHANNEL_ID = 1202499061786214440

# Bot Dev - Testing Server
"""GUILD_ID = 1111128710133854289
MODLOG_CHANNEL_ID = 1186971403459760191
BOTLOG_CHANNEL_ID = 1185411597888393307
WELCOME_CHANNEL_ID = 1185414011597094993
CREATE_DM_CHANNEL_ID = 1193428766941270076
DMS_CLOSED_CHANNEL_ID = 1202555358841933845"""

SHOULD_LOG_ALL = False

FORCED_MUTE_ROLE = 1188519534177566760
MODERATOR_ROLE = 578170681670369290
STAFF_MODERATOR_ROLE = 578170681670369290
TEMP_MODERATOR_ROLE = 784673059906125864
MODERATOR_ROLES = MODERATOR_ROLE, TEMP_MODERATOR_ROLE
ADMIN_ROLE = 854000415074025493
CHAT_MODERATOR_ROLE = 1071458671835488358
BOT_DEVELOPER_ROLE = 854000415074025493
IGCSE_HELPER_ROLE = 696415516893380700
AL_HELPER_ROLE = 869584464324468786

FEEDBACK_CHANNEL_ID = None
FEEDBACK_NAME = None
HOTM_VOTING_CHANNEL = 991202262472998962
CHATMOD_APP_CHANNEL = 1070571771423621191
MOD_CHANNEL = 984718514579464224
CONFESSION_CHANNEL = 965177290814267462
STUDY_SESSION_CHANNEL = 941276796937179157
BOTUPDATES_CHANNEL = 998738803437092884
