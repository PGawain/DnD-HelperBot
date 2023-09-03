import datetime
import logging
import json
import math
import os
import random
import emoji
import re
from telegram import Bot, InputFile, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ConversationHandler, Updater
from telegram.ext import filters, ContextTypes, CallbackQueryHandler
from telegram.error import BadRequest
import requests

#Provides loggins module 
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.WARNING
)

global dbPath
dbPath = "database/newUserDB.json"
tmp_char = {}
new_campaign = {}
current_campaign = 9999


#User login/signup conversation handler states
SIGNUP = map(chr, range(1))
VIEW_CHAR, VIEW_CHAR_ACTIONS = map(chr, range(2, 4))

NAME, RACE, SUBRACE, CLASS, BACKGROUND, BACKSTORIES, ABILITY_SCORES, SCORES, CHOOSE_ARMOR, CHOOSE_WEAPONS, MENU, ATTRIBUTE_CHOICE, CHANGES_HANDLER, END = map(chr, range(4, 18))

CAMPAIGN_CHOICE, CAMPAIGN_NAME, CAMPAIGN_CHOOSEKEY, CREATE_EVENT, JOIN_PUBLIC_CAMPAIGN, JOIN_PRIVATE_CAMPAIGN, CHAR_SELECTION, UPLOAD_MAP, END_UPLOADING, FINAL_MAP = map(chr, range(18, 28))

FIXED_MONSTER, DISEASE, MONSTER_ARMOR, NPC, EVENT_CHOICE, SAVE_MONSTER, CHOOSE_MONSTER, MONSTER_CHOICE, GROUP_ENCOUNTER, MONSTER_NAME, MONSTER_XP, MONSTER_HIT, MONSTER_SPEED, MONSTER_ABILITY, MONSTER_SAVING_THROWS, LEGENDARY_RESISTANCE, MONSTER_ACTIONS, LEGENDARY_ACTIONS, MONSTER_SKILL, MONSTER_SKILL_VALUE, MONSTER_RESISTANCES, MONSTER_IMMUNITIES, SAVE_DISEASE, NPC_NAME, NPC_RACE, NPC_SUBRACE, NPC_CLASS, NPC_BACKGROUND, NPC_ABILITY_SCORES, NPC_SCORES, NPC_ARMOR, NPC_WEAPON, SAVE_NPC= map(chr, range(28, 61))

ASI, FEATURE_CHOOSE_OPTION = map(chr, range(61, 63))

START, BEGINNING_CHOICE, CREATE_SEND, SEND_EVENT, CHOOSE_NEWHP, MODIFY_HP, CHOOSE_CHARACTER, PLAYER_ACTIONS, ACTION_CHOICE, UPLOAD_MAP, END_UPLOADING, ROLL_DICE, ROLL_FIGHT, ROLL_TASK, MODIFY_LEVEL, WRITE_JOURNAL, READ_JOURNAL, PRINT_INFO, ASK_JOURNAL= map(chr, range(63, 82))

WEAPON_TYPE_MOD, WEAPON_CHOOSE_MOD, ARMOR_MOD, BACKSTORIES_MOD, INVENTORY = map(chr, range(82, 87))

CHOOSE_EVENT, CHOOSE_ATTRIBUTE, ABILITY_CHOICE, ARMOR_CHOICE, WEAPON_CHOICE, SAVING_CHOICE, ACTIONS_CHOICE, SKILLS_CHOICE, IMMUNITIES_CHOICE, RESISTANCES_CHOICE, CHOOSE_MODIFY_MONSTER, SAVE_MODIFY, INITIAL_FEATURES, MOD_FEATURES, SAVE_NEW_MAP = map(chr, range(87, 102))

#Character creation conversation handler states
def startUpApp():
    """Ask the user to input the token of the bot"""
    while True:
        token = input("Insert token: ")
        try:
            application = ApplicationBuilder().token(token).build()  # Try to build the application
            return application  # If it succeeds, return the application
        except Exception as e:
            print(f"Invalid token. Please insert a valid one: {e}")


def botSetup():
    """Setup function for the bot, creates the application and adds all the handlers"""
    application = startUpApp()

    help_handler = CommandHandler('help', help)
    application.add_handler(help_handler)

    #DEBUG and UTILITY COMMANDS
    readJournal_handler = CommandHandler('read', readJournal) #test command for journal only. TODO: remove
    application.add_handler(readJournal_handler) #test command for journal only. TODO: remove
    tmp_char_handler = CommandHandler('tmp', printTmpChar) #test command for journal only. TODO: remove
    application.add_handler(tmp_char_handler) #test command for journal only. TODO: remove
    global master

    #Login and Signup conversation handler
    id_conv_handler = ConversationHandler(
        entry_points= [CommandHandler('start', start)],
        states={
            SIGNUP: [MessageHandler(filters.TEXT & ~filters.COMMAND, signup)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        allow_reentry=False,
        per_user=True, per_chat=True
    )

    application.add_handler(id_conv_handler)

    char_view_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(view_char_list, pattern='^VIEW$')],
        states={
            VIEW_CHAR: [MessageHandler(filters.TEXT & ~filters.COMMAND, view_char)],
            VIEW_CHAR_ACTIONS: [CallbackQueryHandler(deleteChar, pattern='^DELETE$'),
                                CallbackQueryHandler(mainMenuChoice, pattern='^BACK$')]
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        allow_reentry=True,
    )

    application.add_handler(char_view_handler)

    char_creation_handler = ConversationHandler(
        entry_points= [CallbackQueryHandler(create_char, pattern='^CREATE$'),
                       CallbackQueryHandler(chooseAttributePrompt, pattern='^MODIFY$'),
                       CallbackQueryHandler(mainMenuChoice, pattern='^MENU$')],
        states={
            #Character creation states	
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, name)],
            RACE: [MessageHandler(filters.TEXT & ~filters.COMMAND, chooseRace)],
            SUBRACE: [MessageHandler(filters.TEXT & ~filters.COMMAND, chooseSubrace)],
            CLASS: [MessageHandler(filters.TEXT & ~filters.COMMAND, chooseClass)],
            BACKGROUND: [MessageHandler(filters.TEXT & ~filters.COMMAND, chooseBackground)],
            INITIAL_FEATURES: [CallbackQueryHandler(initialFeatures)],
            INVENTORY: [MessageHandler(filters.TEXT & ~filters.COMMAND, chooseInventory)],
            BACKSTORIES:    [CallbackQueryHandler(chooseBackgroundStory, pattern='^WRITE$'), 
                             CallbackQueryHandler(chooseBackgroundStory, pattern='^GENERATE$'),
                             CallbackQueryHandler(chooseBackgroundStory, pattern='^NONE$')],
            ABILITY_SCORES: [CallbackQueryHandler(setAbilityScores, pattern='^RANDOM$'), 
                             CallbackQueryHandler(setAbilityScores, pattern='^FIXED$'),
                             CallbackQueryHandler(setAbilityScores, pattern='^AUTO$')],
            SCORES: [MessageHandler(filters.TEXT & ~filters.COMMAND, saveScores)],
            CHOOSE_ARMOR: [MessageHandler(filters.TEXT & ~filters.COMMAND, chooseArmor)],
            CHOOSE_WEAPONS: [MessageHandler(filters.TEXT & ~filters.COMMAND, chooseWeapons)],
            MENU: [CallbackQueryHandler(mainMenuChoice, pattern='^MENU$')],
            #Modify character states
            ATTRIBUTE_CHOICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, chooseAttribute)],
            CHANGES_HANDLER: [MessageHandler(filters.TEXT & ~filters.COMMAND, modifyAttribute)],
            WEAPON_TYPE_MOD: [MessageHandler(filters.TEXT & ~filters.COMMAND, weaponTypeMod)],
            WEAPON_CHOOSE_MOD: [MessageHandler(filters.TEXT & ~filters.COMMAND, weaponChooseMod)],
            ARMOR_MOD: [MessageHandler(filters.TEXT & ~filters.COMMAND, armorMod)],
            BACKSTORIES_MOD: [CallbackQueryHandler(backstoriesMod)],
            MOD_FEATURES: [CallbackQueryHandler(modifyFeatures)],
            END: [MessageHandler(filters.TEXT & ~filters.COMMAND, saveCharacter)]
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        allow_reentry=True,
        per_user=True, per_chat=True
    )
    application.add_handler(char_creation_handler)

    campaign_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(joinCampaign, pattern='^JOINCAMPAIGN$'),
                      CallbackQueryHandler(createCampaign, pattern='^CREATECAMPAIGN$')],
        states={
            #Join campaign states
            CAMPAIGN_CHOICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, publicOrPrivateCampaign)],
            #Create campaign states
            CAMPAIGN_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, campaignName)],
            CAMPAIGN_CHOOSEKEY: [MessageHandler(filters.TEXT & ~filters.COMMAND, campaignChooseKey)],
            CREATE_EVENT: [CallbackQueryHandler(createEvent, pattern='^CREATE_EVENT$')],
            #Join campaign states
            JOIN_PUBLIC_CAMPAIGN: [MessageHandler(filters.TEXT & ~filters.COMMAND, joinPublicCampaign)],
            JOIN_PRIVATE_CAMPAIGN: [MessageHandler(filters.TEXT & ~filters.COMMAND, joinPrivateCampaign)],
            CHAR_SELECTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, charSelection)],
            UPLOAD_MAP: [MessageHandler(filters.TEXT & ~filters.COMMAND, uploadMap)],
            END_UPLOADING: [MessageHandler(filters.TEXT & ~filters.COMMAND, endUploading)],
            FINAL_MAP: [MessageHandler(filters.ALL & ~filters.COMMAND, effectiveUpload)]
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        allow_reentry=True,
    )
    application.add_handler(campaign_handler)

    event_creation_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(createEvent, pattern='^CREATE_EVENT$')],
        states={
            EVENT_CHOICE: [CallbackQueryHandler(monsterChoice, pattern = '^MONSTER$'),
                           CallbackQueryHandler(diseaseChoice, pattern = '^DISEASE$'),
                           CallbackQueryHandler(NPCChoice, pattern = '^NPC$')],
            MONSTER_CHOICE:[CallbackQueryHandler(fixedMonster, pattern = '^FIXED_MONSTER$'),
                            CallbackQueryHandler(customMonster, pattern = '^CUSTOM_MONSTER$')],
            CHOOSE_MONSTER: [MessageHandler(filters.TEXT & ~filters.COMMAND, chooseMonster)],
            DISEASE: [MessageHandler(filters.TEXT & ~filters.COMMAND, diseaseChoice)],
            NPC: [MessageHandler(filters.TEXT & ~filters.COMMAND, NPCChoice)],
            SAVE_MONSTER: [MessageHandler(filters.TEXT & ~filters.COMMAND, saveMonster)],
            GROUP_ENCOUNTER:[CallbackQueryHandler(monsterChoice, pattern = '^ADD_MONSTER$'),
                            CallbackQueryHandler(saveMonster, pattern = '^SAVE_EVENT$')],
            MONSTER_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, monsterName)],
            MONSTER_ARMOR: [MessageHandler(filters.TEXT & ~filters.COMMAND, monsterArmor)],
            MONSTER_XP: [MessageHandler(filters.TEXT & ~filters.COMMAND, monsterXP)],
            MONSTER_HIT: [MessageHandler(filters.TEXT & ~filters.COMMAND, monsterHit)],
            MONSTER_SPEED: [MessageHandler(filters.TEXT & ~filters.COMMAND, monsterSpeed)],
            MONSTER_ABILITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, monsterAbility)],
            MONSTER_SAVING_THROWS: [MessageHandler(filters.TEXT & ~filters.COMMAND, monsterSavingThrows)],
            LEGENDARY_RESISTANCE: [MessageHandler(filters.TEXT & ~filters.COMMAND, legendaryResistance)],
            MONSTER_ACTIONS:[MessageHandler(filters.TEXT & ~filters.COMMAND, monsterActions)],
            LEGENDARY_ACTIONS:[MessageHandler(filters.TEXT & ~filters.COMMAND, monsterLegActions)],
            MONSTER_SKILL:[MessageHandler(filters.TEXT & ~filters.COMMAND, monsterSkill)],
            MONSTER_SKILL_VALUE:[MessageHandler(filters.TEXT & ~filters.COMMAND, monsterSkillValue)],
            MONSTER_IMMUNITIES:[MessageHandler(filters.TEXT & ~filters.COMMAND, monsterImmunities)],
            MONSTER_RESISTANCES:[MessageHandler(filters.TEXT & ~filters.COMMAND, monsterResistances)],
            SAVE_DISEASE:[MessageHandler(filters.TEXT & ~filters.COMMAND, saveDisease)],
            NPC_NAME:[MessageHandler(filters.TEXT & ~filters.COMMAND, NPCName)],
            NPC_RACE:[MessageHandler(filters.TEXT & ~filters.COMMAND, NPCRace)],
            NPC_SUBRACE:[MessageHandler(filters.TEXT & ~filters.COMMAND, NPCSubrace)],
            NPC_CLASS:[MessageHandler(filters.TEXT & ~filters.COMMAND, NPCClass)],
            NPC_BACKGROUND:[MessageHandler(filters.TEXT & ~filters.COMMAND, NPCBackground)],
            NPC_ABILITY_SCORES: [CallbackQueryHandler(NPCAbilityScores, pattern='^NPC_RANDOM$'), 
                             CallbackQueryHandler(NPCAbilityScores, pattern='^NPC_FIXED$'),
                             CallbackQueryHandler(NPCAbilityScores, pattern='^NPC_AUTO$')],
            NPC_SCORES:[MessageHandler(filters.TEXT & ~filters.COMMAND, saveNPCScores)],
            NPC_ARMOR:[MessageHandler(filters.TEXT & ~filters.COMMAND, NPCArmor)],
            NPC_WEAPON:[MessageHandler(filters.TEXT & ~filters.COMMAND, NPCWeapon)],
            SAVE_NPC:[MessageHandler(filters.TEXT & ~filters.COMMAND, saveNPC)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        allow_reentry=True,
    )
    application.add_handler(event_creation_handler)

    event_modify_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(eventChoice, pattern='^MOD-\d+$')],
        states={
            CHOOSE_ATTRIBUTE: [MessageHandler(filters.TEXT & ~filters.COMMAND, attributeChoice)],
            ABILITY_CHOICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, abilityChoice)],
            ARMOR_CHOICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, armorChoice)],
            WEAPON_CHOICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, weaponChoice)],
            SAVING_CHOICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, savingChoice)],
            ACTIONS_CHOICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, actionsChoice)],
            SKILLS_CHOICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, skillsChoice)],
            IMMUNITIES_CHOICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, immunitiesChoice)],
            RESISTANCES_CHOICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, resistancesChoice)],
            CHOOSE_MODIFY_MONSTER: [MessageHandler(filters.TEXT & ~filters.COMMAND, chooseModifyMonster)],
            SAVE_MODIFY: [MessageHandler(filters.TEXT & ~filters.COMMAND, saveModify)]
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        allow_reentry=True,
    )
    application.add_handler(event_modify_handler)

    game_handler = ConversationHandler(
        entry_points= [CommandHandler('abil', checkForClassFeatures)],
        states={
            ASI: [CallbackQueryHandler(asiKB)],
            FEATURE_CHOOSE_OPTION: [CallbackQueryHandler(featureChooseOption)]
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        allow_reentry=True,
        per_user=True, per_chat=True
    )
    application.add_handler(game_handler)

    game_start_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(startGameMenu, pattern='^GAME_START$')],
        states={
            START: [MessageHandler(filters.TEXT & ~filters.COMMAND, startGameMenu)],
            BEGINNING_CHOICE:[CallbackQueryHandler(chooseEventPrompt, pattern = '^MODIFY_EVENTS$'),
                              CallbackQueryHandler(HP, pattern = '^MODIFY_HP$'),
                              CallbackQueryHandler(startEvents, pattern = '^BEGIN_EVENTS$'),
                              CallbackQueryHandler(startEvents, pattern = '^UPLOAD_MAP$'),
                              CallbackQueryHandler(chooseCharToMod, pattern = '^MODIFY_LEVEL$'),
                              CallbackQueryHandler(chooseCharToMod, pattern = '^RETURN$'),
                              CallbackQueryHandler(askJournal, pattern = '^WRITE_JOURNAL$'),
                              CallbackQueryHandler(readJournal, pattern = '^READ_JOURNAL$'),
                              CallbackQueryHandler(startGameMenu, pattern = '^BACKMENU$'),
                              CallbackQueryHandler(infoPlayers, pattern = '^INFO_PLAYERS$'),
                              CallbackQueryHandler(viewMap, pattern = '^VIEW_MAP$'),
                              CallbackQueryHandler(uploadNewMap, pattern = '^NEW_MAP$')],
            CREATE_SEND: [CallbackQueryHandler(createEventToSend, pattern = '^EVENT_INT$'),
                              CallbackQueryHandler(createEventToSend, pattern = '^OTHER_INFO$')],
            SEND_EVENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, sendEvent)],
            CHOOSE_NEWHP: [MessageHandler(filters.TEXT & ~filters.COMMAND, chooseNewHP)],
            MODIFY_HP: [MessageHandler(filters.TEXT & ~filters.COMMAND, modifyHP)],
            CHOOSE_CHARACTER: [MessageHandler(filters.TEXT & ~filters.COMMAND, charSelection)],
            UPLOAD_MAP: [MessageHandler(filters.TEXT & ~filters.COMMAND, uploadMap)],
            END_UPLOADING: [MessageHandler(filters.TEXT & ~filters.COMMAND, endUploading)],
            FINAL_MAP: [MessageHandler(filters.ALL & ~filters.COMMAND, effectiveUpload)],
            PLAYER_ACTIONS: [MessageHandler(filters.TEXT & ~filters.COMMAND, playerMenu)],
            ACTION_CHOICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, actionChoice),
                            CallbackQueryHandler(askJournal, pattern = '^WRITE_JOURNAL$'),
                            ],
            ROLL_DICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, chooseWeap)],
            ROLL_FIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, rollDiceFight)],
            ROLL_TASK: [MessageHandler(filters.TEXT & ~filters.COMMAND, rollDiceTask)],
            MODIFY_LEVEL: [MessageHandler(filters.TEXT & ~filters.COMMAND, modifyLevel)],
            WRITE_JOURNAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, writeJournal)],
            READ_JOURNAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, readJournal)],
            PRINT_INFO: [MessageHandler(filters.TEXT & ~filters.COMMAND, printInfo)],
            ASK_JOURNAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, askJournal)],
            SAVE_NEW_MAP: [MessageHandler(filters.TEXT & ~filters.COMMAND, saveNewMap)]
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        allow_reentry=True,
    )
    application.add_handler(game_start_handler)
    application.run_polling()

async def printTmpChar(update, context):
    if "tmp_character" in tmp_char[update.effective_chat.id]:
        print("TMP CHARACTER - USED FOR CREATION")
        print(json.dumps(tmp_char[update.effective_chat.id]["tmp_character"], indent=4))
    else:
        print("No tmp char or selected char found")
        print(json.dumps(tmp_char, indent=4))


async def start(update, context):
    """Start command, checks if user is already present in the database, if not, start login/signup procedure"""
    telegramID = str(update.effective_chat.id)
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Ahoy!")
    with open(dbPath, "r") as f:
        data = json.load(f)
    for user in data["users"]:
        if telegramID == str(user["telegramID"]):
            print("User found!")
            username = user["username"]
            await context.bot.send_message(chat_id=update.effective_chat.id, text="Benvenuto " + username) #TODO sistemare interazione con utente
            await mainMenuChoice(update, context)
            return ConversationHandler.END
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Inserisci nome") #TODO sistemare interazione con utente
        return SIGNUP
    
async def signup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Signup procedure, adds user to the database"""
    username = update.message.text
    with open(dbPath, "r") as f:
        data = json.load(f)
    for user in data["users"]:
        if username == str(user["username"]):
            await context.bot.send_message(chat_id=update.effective_chat.id, text="Use an unique username, you moron! Choose wisely!") #TODO sistemare interazione con utente
            return SIGNUP
    new_user = {"telegramID" : update.effective_chat.id, "username": username, "characters": []}
    data["users"].append(new_user)
    with open(dbPath, "w") as f:
        json.dump(data, f)
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Welcome aboard, " + username + "!") 
    await mainMenuChoice(update, context)
    return ConversationHandler.END

async def cancel(update, context):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Error occourred, please restart the conversation with the command /start")
    return ConversationHandler.END

async def help(update, context):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="If the bot is not responding, please check if it is running on the server and your internet connection. If the error persists, try to restart the bot with the command /start")

async def mainMenuChoice(update, context):
    """
    This function generates an inline keyboard with options for the main menu of the bot. 
    
    The keyboard includes choices to view existing character sheets, create new ones, join existing campaigns, or create new campaigns. The generated keyboard is sent as a message to the user's chat. This function could be called from every other function that needs to return to the main menu and also works as a entry point for the character creation handler."""
    keyboard = [
        [InlineKeyboardButton("View existing", callback_data=str("VIEW")),
         InlineKeyboardButton("Create new", callback_data=str("CREATE"))],
        [InlineKeyboardButton("Join existing campaign", callback_data=str("JOINCAMPAIGN")),
         InlineKeyboardButton("Create new campaign", callback_data=str("CREATECAMPAIGN"))]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    message = "Would you like to view your existing character sheets or create a new one?"
    await context.bot.send_message(chat_id=update.effective_chat.id, text=message, reply_markup=reply_markup)
# ------------------------------- CHARACTER VISUALIZATION ---------------------------------
async def view_char_list(update, context):
    """" This function creates an inline keyboard with all the user's characters and sends it to the user """
    print("Viewing character")
    with open(dbPath, "r") as f:
        data = json.load(f)
    for user in data["users"]:
        if str(update.effective_chat.id) == str(user["telegramID"]):
            if not user["characters"]:
                message = "You don't have any characters yet!"
                await context.bot.send_message(chat_id=update.effective_chat.id, text=message)
                await mainMenuChoice(update, context)
                return ConversationHandler.END
            keyboard = []
            for char in user["characters"]:
                keyboard.append([char["name"]])
            reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
            message = "Choose a character to view"
            await context.bot.send_message(chat_id=update.effective_chat.id, text=message, reply_markup=reply_markup)
            return VIEW_CHAR

async def view_char(update, context):
    """ This function is called when the user chooses a character to view. It gets all the character's data from the database and sends it to the user in a readable format. It also creates an inline keyboard with options to modify or delete the character. """
    selected_char = update.message.text

    global tmp_char
    if update.effective_chat.id not in tmp_char:
        tmp_char[update.effective_chat.id] = {}
    tmp_char[update.effective_chat.id]["tmp_character"] = {}

    with open(dbPath, "r") as f:
        data = json.load(f)

    for user in data["users"]: #TODO: migliorare come stampa a schermo
        if str(update.effective_chat.id) == str(user["telegramID"]):
            for char in user["characters"]:
                if str(char["name"]) == str(selected_char):
                    tmp_char[update.effective_chat.id]["tmp_character"] = char
                    database_string = ""
                    for key, value in tmp_char[update.effective_chat.id]["tmp_character"].items():
                        if key == "ability_scores":
                            database_string += "Ability Scores and Modifiers:\n"
                            for ability, score in value.items():
                                database_string += f"- {ability}: {score}\n"
                                modifier = tmp_char[update.effective_chat.id]["tmp_character"]["ability_modifiers"][ability]
                                if modifier > 0:
                                    modifier = "+" + str(modifier)
                                database_string += f"- Modifier: {modifier}\n\n"
                        else: #caso base
                            if key == "ability_modifiers" or key == "weapons" or key == "armor":
                                continue
                            database_string += f"{key}: {value}\n"
                    await context.bot.send_message(chat_id=update.effective_chat.id, text=database_string)
    keyboard = [[InlineKeyboardButton("Modify character", callback_data=str("MODIFY"))], 
    [InlineKeyboardButton("Delete character", callback_data=str("DELETE"))],
    [InlineKeyboardButton("Back", callback_data=str("BACK"))]]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    message = "What would you like to do with this character?"
    await context.bot.send_message(chat_id=update.effective_chat.id, text=message, reply_markup=reply_markup)
    return VIEW_CHAR_ACTIONS
# ------------------------------- CHARACTER DELETE ---------------------------------------
async def deleteChar(update, context):
    global tmp_char
    with open(dbPath, "r") as f:
        data = json.load(f)

    chat_id = str(update.effective_chat.id)
    selected_char_name = str(tmp_char[update.effective_chat.id]["tmp_character"]["name"])
    
    for user in data["users"]:
        if chat_id == str(user["telegramID"]):
            characters = user["characters"]
            for i, char in enumerate(characters):
                if str(char["name"]) == selected_char_name:
                    print("Deleting char: " + selected_char_name)
                    characters.pop(i)
                    break
    
    with open(dbPath, "w") as f:
        json.dump(data, f, indent=4)
    await mainMenuChoice(update, context)
    return ConversationHandler.END
# ---------------------------------- CHARACTER CREATION ----------------------------------
async def create_char(update, context):
    """
    Begin character creation process by prompting the user for their character's name.

    This function is the first step in the character creation handler. It serves as a placeholder to instruct the user to input their character's name. Once the user responds with the name, the process of creating the character will continue."""
    message = "Okay, let's get to work then! What's your character's name?"
    await context.bot.send_message(chat_id=update.effective_chat.id, text=message)

    return NAME

async def name(update, context): 
    """
    Handle character name input and guide the user through selecting a character race.

    This function is part of the character creation process and is called after the user provides a character name. It checks whether the provided name is unique for the user and creates a new character entry if the name is available. Subsequently, it initializes
    the temporary character data, sets the current weight to 0, and prompts the user to choose a character race from the available options.
    """
    char_name = update.message.text

    with open(dbPath, "r") as f:
        data = json.load(f)
    for user in data["users"]: #check if user already has a character with that name, if not, create it
        if str(update.effective_chat.id) == str(user["telegramID"]):
            if "characters" not in user:
                user["characters"] = []
            for char in user["characters"]:
                if str(char_name) == str(char["name"]):
                    message = "You already have a character with that name! Input another one"
                    await context.bot.send_message(chat_id=update.effective_chat.id, text=message)
                    return NAME

    with open("database/char_sheet.json", "r") as f:
        new_char = json.load(f)
    new_char["name"] = char_name

    tmp_char[update.effective_chat.id] = {}
    tmp_char[update.effective_chat.id]["tmp_character"] = new_char
    tmp_char[update.effective_chat.id]["tmp_character"]["current_weight"] = 0
    
    with open("5eDefaults/races.json", "r") as fp:
        races = json.load(fp)
    # acquiring list of available races
    races = [*races]

    reply_keyboard = []
    for race in races:
        reply_keyboard.append([race])

    reply_keyboard.append([emoji.emojize("Info races \U00002139")])

    race_kb=ReplyKeyboardMarkup(
        reply_keyboard, one_time_keyboard=True, input_field_placeholder='Choose your race'
    )
    
    message="Character created! Please choose a Race:"
    await context.bot.send_message(chat_id=update.effective_chat.id, text=message, reply_markup=race_kb)
    return RACE

async def chooseRace(update, context):
    """
    Handle character race selection and provide race-related choices.

    This function is responsible for handling the user's selection of a character race. It receive the chosen race from the user input, if the user selected "Info races" the function displays detailed descriptions of available races. After the user
    selects a race, it stores the chosen race in the temporary character data. If the chosen race has subraces, the user is prompted to choose a subrace. If there are no subraces, the user is prompted to choose a character class.
    """
    global race
    race = update.message.text
    global tmp_char

    with open("5eDefaults/races.json", "r") as fp:
        races = json.load(fp)

    # Print to the user information about races
    if race == "Info races ℹ️":
        reply_keyboard = []

        race_kb=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=True, input_field_placeholder='Choose your race'
        )

        for description in races["dwarf"]["race_description"]["subraces"]:
            message = description["description"]
        await context.bot.send_message(chat_id=update.effective_chat.id, text=message, reply_markup=race_kb)

        for description in races["elf"]["race_description"]["subraces"]:
            message = description["description"]
            await context.bot.send_message(chat_id=update.effective_chat.id, text=message, reply_markup=race_kb)

        for description in races["halfling"]["race_description"]["subraces"]:
            message = description["description"]
        await context.bot.send_message(chat_id=update.effective_chat.id, text=message, reply_markup=race_kb)

        for description in races["human"]["race_description"]["subraces"]:
            message = description["description"]
        await context.bot.send_message(chat_id=update.effective_chat.id, text=message, reply_markup=race_kb)
        
        # TODO: add info come possibili sottorazze, bonus e bonus sottorazze sulle abilità
        return RACE

    tmp_char[update.effective_chat.id]["tmp_character"]["race"] = race

    if "subraces_choice" in races[race]:
        reply_keyboard = []
        for subrace in races[race]["subraces_choice"]["options"]:
            reply_keyboard.append([subrace["display_name"]])
    else:
        with open("5eDefaults/classes.json", "r") as fp:
            classes = json.load(fp)
        # acquiring list of available races
        classes = [*classes]

        reply_keyboard = []
        for className in classes:
            reply_keyboard.append([className])


        class_kb=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=True, input_field_placeholder='Choose your class'
        )
        message="Well well, we have a " + race + " here! So, what do you do for a living?"
        await context.bot.send_message(chat_id=update.effective_chat.id, text=message, reply_markup=class_kb)
        return CLASS

    subrace_kb=ReplyKeyboardMarkup(
        reply_keyboard, one_time_keyboard=True, input_field_placeholder='Choose your subrace'
    )
    message="Well well, we have a " + race + " here! And do you belong to any particular group or tribe within your people, my friend?"
    await context.bot.send_message(chat_id=update.effective_chat.id, text=message, reply_markup=subrace_kb)
    return SUBRACE

async def chooseSubrace(update, context):
    """
    Handle subrace selection and prompt the user to choose a character class.

    This function is responsible for handling the user's selection of a subrace for their character. It stores the chosen subrace in the temporary character data and then prompts the user to select a character class from the available options.
    """

    subrace = update.message.text
    global tmp_char
    tmp_char[update.effective_chat.id]["tmp_character"]["subrace"] = subrace


    with open("5eDefaults/classes.json", "r") as fp:
        classes = json.load(fp)
    # acquiring list of available races
    classes = [*classes]

    reply_keyboard = []
    for className in classes:
        reply_keyboard.append([className])


    class_kb=ReplyKeyboardMarkup(
        reply_keyboard, one_time_keyboard=True, input_field_placeholder='Choose your class'
    )
    message="Ah, a " + subrace + "! I can see the family resemblance now. You look just like the legends of your people! So, what do you do for a living?"
    await context.bot.send_message(chat_id=update.effective_chat.id, text=message, reply_markup=class_kb)
    return CLASS

async def chooseClass(update, context):
    """
    Handle character class selection and apply class-related features.

    This function is responsible for handling the user's selection of a character class. It stores the chosen class in the temporary character data and applies class-related features to the character's inventory. If the chosen class has features that require a choice, the user is prompted to choose an option and a new state is returned to handle the choice.  After applying features the user is prompted to choose a character background from the available options.
    """

    global char_class
    char_class = update.message.text
    global tmp_char
    tmp_char[update.effective_chat.id]["tmp_character"]["class"] = char_class

    with open("5eDefaults/classes.json", "r") as fp:
        classes = json.load(fp)
    for className in classes:
        if className == char_class:
            inventory = classes[className]["inventory"]
            break
    for category in inventory:
        for item in inventory[category]:
            tmp_char[update.effective_chat.id]["tmp_character"]["inventory"][category].append(item)

    options = await initialFeatures(update, context)
    if options:
        with open("5eDefaults/classes.json", "r") as fp:
            classData = json.load(fp)
        char_class = tmp_char[update.effective_chat.id]["tmp_character"]["class"]
        if "1" in classData[char_class]["levels"]:
            level_data = classData[char_class]["levels"]["1"]
        if "features" in level_data and isinstance(level_data["features"], list):
            for feature in level_data["features"]:
                if "options" in feature:
                    message = "You gained a new feature!" + "\nName: " + feature["display_name"] + "\nDescription: " + feature["description"]
                    keyboard = []
                    for option in feature["options"]:
                        message += "\n- " + option["display_name"] + ": " + option["description"]
                        keyboard.append([InlineKeyboardButton(option["display_name"], callback_data=feature["display_name"]+"-"+option["display_name"])])
                    await context.bot.send_message(chat_id=update.effective_chat.id, text=message, reply_markup=InlineKeyboardMarkup(keyboard))
                    return INITIAL_FEATURES

    with open("5eDefaults/backgrounds.json", "r") as fp:
        backgrounds = json.load(fp)
    # acquiring list of available backgrounds stories
    backgrounds = [*backgrounds]

    reply_keyboard = []
    for background in backgrounds:
        reply_keyboard.append([background])

    subrace_kb=ReplyKeyboardMarkup(
        reply_keyboard, one_time_keyboard=True, input_field_placeholder='Choose your background'
    )
    message="Ah, a " + char_class + ", a wise choice indeed! Now, what about your background? Have you had any interesting experiences in your past that shaped who you are today?"
    await context.bot.send_message(chat_id=update.effective_chat.id, text=message, reply_markup=subrace_kb)
    return BACKGROUND

async def initialFeatures(update, context):
    """
    Handle callback data from initial class features and guide the user to choose a background.

    This function is responsible for processing callback data related to initial features gained from choosing a character class that required further choices from the user. It saves the chosen feature and its option to the temporary
    character data. After saving the feature, the function prompts the user to choose a character background from the available options.
    """
    if update.callback_query is not None:
        input_data = update.callback_query.data
        feature = input_data.split("-")[0]
        option = input_data.split("-")[1]
        # Save the feature
        player = tmp_char[update.effective_chat.id]["tmp_character"]
        if "features" not in player:
            player["features"] = []
        player["features"].append({"name": feature, "option": option})
                        
        with open("5eDefaults/backgrounds.json", "r") as fp:
            backgrounds = json.load(fp)
        # acquiring list of available backgrounds stories
        backgrounds = [*backgrounds]

        reply_keyboard = []
        for background in backgrounds:
            reply_keyboard.append([background])

        subrace_kb=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=True, input_field_placeholder='Choose your background'
        )
        char_class = tmp_char[update.effective_chat.id]["tmp_character"]["class"]
        message="Ah, a " + char_class + ", a wise choice indeed! Now, what about your background? Have you had any interesting experiences in your past that shaped who you are today?"
        await context.bot.send_message(chat_id=update.effective_chat.id, text=message, reply_markup=subrace_kb)
        return BACKGROUND
    
    multiOptions = False
    with open("5eDefaults/classes.json", "r") as fp:
        classData = json.load(fp)
    char_class = tmp_char[update.effective_chat.id]["tmp_character"]["class"]
    if "1" in classData[char_class]["levels"]:
        level_data = classData[char_class]["levels"]["1"]
    if "features" in level_data and isinstance(level_data["features"], list):
        for feature in level_data["features"]:
            if "options" not in feature or feature["options"] is None: #The feature does not require any further action
                player = tmp_char[update.effective_chat.id]["tmp_character"]
                player["features"].append({"name": feature["display_name"]})
                message = "You gained a new feature!" + "\nName: " + feature["display_name"] + "\nDescription: " + feature["description"]
                await context.bot.send_message(chat_id=update.effective_chat.id, text=message)	
            else:
                multiOptions = True
        return multiOptions

async def chooseBackground(update, context):
    """
    Handle character background selection and manage background-related inventory items.

    This function is responsible for handling the user's selection of a character background. It stores the chosen background in the temporary character data and manages the character's inventory items based on the background's associated items. If an item is a list, the function iterates through its contents and adds them individually. If an item has weight (meaning it is part of the inventory.json file), it checks the weight and updates the character's total weight. If an item has multiple choices separated by
    "or", the user is prompted to choose one of the options and the INVENTORY state is returned. After managing the inventory items, the function sends messages to acknowledge the background selection and offers the user options to create a background story.
    """
    global background 
    background = update.message.text
    global tmp_char
    tmp_char[update.effective_chat.id]["tmp_character"]["background"] = background
    with open("5eDefaults/backgrounds.json", "r") as fp:
        backgrounds = json.load(fp)
    for backgroundName in backgrounds:
        if backgroundName == background:
            inventory = backgrounds[backgroundName]["inventory"]["misc"]
            break
    for item in inventory:
        if isinstance(item, list):
            # If the item is a list, iterate through its contents and add them individually
            for sub_item in item:
                item_weight = await checkInventoryWeight(update, context, sub_item)
                await updateWeight(update, context, item_weight)
                tmp_char[update.effective_chat.id]["tmp_character"]["inventory"]["misc"].append(sub_item)
        else:
            item_weight = await checkInventoryWeight(update, context, item)
            if item_weight:
                await updateWeight(update, context, item_weight)
                tmp_char[update.effective_chat.id]["tmp_character"]["inventory"]["misc"].append(item)
            else:
                print(f"{item} has no weight")

    
    for item in tmp_char[update.effective_chat.id]["tmp_character"]["inventory"]["misc"]:
        if " or " in item:
            choices = item.split(" or ")
            kb = []
            for choice in choices:
                item_weight = await checkInventoryWeight(update, context, choice)
                choice = choice + " (" + str(item_weight) + " lb)"
                kb.append([choice])
            reply_markup = ReplyKeyboardMarkup(kb, one_time_keyboard=True)
            message = "Choose one of the following items: "
            await context.bot.send_message(chat_id=update.effective_chat.id, text=message, reply_markup=reply_markup)
            #Remove the item from the inventory
            tmp_char[update.effective_chat.id]["tmp_character"]["inventory"]["misc"].remove(item)
            return INVENTORY

    message="Mhhh I see... A " + background + "! You know, I've met a few folks with that kind of experience. They always have the best stories. You may have to tell me some of yours one day!"
    await context.bot.send_message(chat_id=update.effective_chat.id, text=message)

    keyboard = [
        [
            InlineKeyboardButton("I want to write the story", callback_data=str("WRITE")),
            InlineKeyboardButton("Generate a random story", callback_data=str("GENERATE")),
        ],

        [
            InlineKeyboardButton("No thanks", callback_data=str("NONE")),
        ]
    ]


    reply_markup = InlineKeyboardMarkup(keyboard)
    message="Would you like to create a background story for your character?"
    
    await context.bot.send_message(chat_id=update.effective_chat.id, text=message, reply_markup=reply_markup)
    return BACKSTORIES

async def checkInventoryWeight(update, context, item):
    """
    Retrieve and return the weight of a specified item from the inventory data.

    This function is responsible for checking the weight of a specified item by searching for the item's information in the inventory data. If the item is found, the function returns its weight; if not found, it returns a weight of 0.
    """
    with open("5eDefaults/inventory.json", "r") as fp:
        inventoryList = json.load(fp)
    for gear_item in inventoryList["adventuring_gear"]:
        if str(item) == str(gear_item["name"]):
            print(f"{item} is present in the inventory JSON.")
            print(f"Weight: {gear_item['weight']}")
            return float(gear_item["weight"])
    print(inventoryList["adventuring_gear"][-1]["name"])    
    print(f"{item} is NOT present in the inventory JSON.")
    return 0

async def chooseInventory(update, context):
    """
    Handle the user's selection of inventory items with choices.

    This function is responsible for processing the user's selection of inventory items that have choices separated by "or". When such items are encountered in the character's inventory, the function splits the choices, prompts the user to select one, and returns to the INVENTORY state to manage the user's choice. If there are no more items with choices, the function proceeds to acknowledge the background selection and offer options to create a background story.
    """
    choice = update.message.text
    choice = choice.split("(")[0].strip()
    
    global tmp_char
    tmp_char[update.effective_chat.id]["tmp_character"]["inventory"]["misc"].append(choice)
    item_weight = await checkInventoryWeight(update, context, choice)
    await updateWeight(update, context, item_weight)

    for item in tmp_char[update.effective_chat.id]["tmp_character"]["inventory"]["misc"]:
        if " or " in item:
            choices = item.split(" or ")
            kb = []
            for choice in choices:
                item_weight = await checkInventoryWeight(update, context, choice)
                choice = choice + " (" + str(item_weight) + " lb)"
                kb.append([choice])
            reply_markup = ReplyKeyboardMarkup(kb, one_time_keyboard=True)
            message = "Choose one of the following items: "
            await context.bot.send_message(chat_id=update.effective_chat.id, text=message, reply_markup=reply_markup)
            #Remove the item from the inventory
            tmp_char[update.effective_chat.id]["tmp_character"]["inventory"]["misc"].remove(item)
            return INVENTORY
    
    message="Mhhh I see... A " + background + "! You know, I've met a few folks with that kind of experience. They always have the best stories. You may have to tell me some of yours one day!"
    await context.bot.send_message(chat_id=update.effective_chat.id, text=message)

    keyboard = [
        [
            InlineKeyboardButton("I want to write the story", callback_data=str("WRITE")),
            InlineKeyboardButton("Generate a random story", callback_data=str("GENERATE")),
        ],

        [
            InlineKeyboardButton("No thanks", callback_data=str("NONE")),
        ]
    ]


    reply_markup = InlineKeyboardMarkup(keyboard)
    message="Would you like to create a background story for your character?"
    
    await context.bot.send_message(chat_id=update.effective_chat.id, text=message, reply_markup=reply_markup)
    return BACKSTORIES

async def chooseBackgroundStory(update, context):
    """
    Handle the user's choice regarding their character's background story.

    This function is responsible for processing the user's choice regarding their character's background story. Depending on the user's choice, the function may prompt the user to write their own story or generate a random one. It also prepares for the next step in the conversation, allowing the user to choose how to generate their ability scores.
    """
    callback_data = update.callback_query.data
    global tmp_char


    if callback_data == "WRITE":
        message = "Perfect! Write your background story and press 'enter'"
        await context.bot.send_message(chat_id=update.effective_chat.id, text=message)

    elif callback_data == "GENERATE":
        message = "Ok, I will generate a random background story for you"
        await context.bot.send_message(chat_id=update.effective_chat.id, text=message)
        with open("5eDefaults/backgorundgenerator.json", "r") as fp:
            backgroundsStories = json.load(fp)
            random_number = random.randint(0, 2)

            #switchcase per identificare l'indice associato alla razza
            if race == "dwarf":
                race_num = 0
            elif race == "elf":
                race_num = 1
            elif race == "halfling":
                race_num = 2
            elif race == "human":
                race_num = 3
            else:
                race_num = 4

            #switchcase per identificare l'indice associato alla classe
            if char_class == "wizard":
                class_num = 0
            else:
                class_num = 1

            #switchcase per identificare l'indice associato al background
            if background == "acolyte":
                back_num = 0
            elif background == "criminal":
                back_num = 1
            elif background == "folk_hero":
                back_num = 2
            elif background == "noble":
                back_num = 3
            elif background == "sage":
                back_num = 4
            else:
                back_num = 5
            
    
            races = backgroundsStories["races"]
            theRace = races[race_num][race]
            theClass = theRace[class_num][char_class]
            theBack = theClass[back_num][background]
            message = theBack[random_number]
            await context.bot.send_message(chat_id=update.effective_chat.id, text=message)

    elif callback_data == "NONE":
        message = ""

    keyboard = [
        [
            InlineKeyboardButton("Randomly genereted value", callback_data=str("RANDOM")),
            InlineKeyboardButton("Fixed value array", callback_data=str("FIXED"))
        ],
        [
            InlineKeyboardButton("Full auto", callback_data=str("AUTO")),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    message="Now, let's get to the fun part! How do you want to generate your ability scores?"
    await context.bot.send_message(chat_id=update.effective_chat.id, text=message, reply_markup=reply_markup)
    return ABILITY_SCORES

async def setAbilityScores(update, context):
    """
    Handle the user's choice regarding how to generate their character's ability scores and their generation.

    This function is responsible for processing the user's choice regarding how to generate their character's ability scores. Depending on the user's choice, the function may generate the scores automatically, randomly, or using a fixed array. 
    AUTO: The function generates the scores automatically, randomly rolling 4d6 and keeping the highest 3 rolls for each ability score. This process is repeated six times, so that the user has six numbers in total. These six numbers are the character's ability scores and are assigned randomly to the character's abilities. 
    RANDOM: The function generates the scores randomly, using the same process as AUTO, but the user is prompted to assign the scores to the character's abilities as they see fit.
    FIXED: The function generates the scores using a fixed array of numbers. The user is prompted to assign the scores to the character's abilities as they see fit.
    After handling the generation of the ability scores, this function calls the setModifiers function to calculate the character's ability score modifiers and the setRacialBonuses function to apply the character's racial bonuses to the ability scores. Finally, the function calls the getProficiencies function to assign the character's proficiencies.

    If an armor is present in the character's inventory, the function verifies if the user has to choose between two armor types and prompts the user to choose one. If the user has to choose between two armor types, the function returns the ARMOR state to handle the user's choice. If the user does not have to choose between two armor types, the function assign the armor to the character's inventory and continues with the character creation process.

    If the armor is not present or there wasn't a choice to make, the function checks if any weapons are present in the character's inventory and repeats a similar process to handle the user's assignment of weapons. If the user has to choose between two weapons, the function returns the WEAPON state to handle the user's choice. If the user does not have to choose between two weapons, the function assign the weapon to the character's inventory and finally saves the character to the database.
    """
    global tmp_char
 
    abilities_to_set = all(value == 0 for value in tmp_char[update.effective_chat.id]["tmp_character"]["ability_scores"].values())
    FullAutoFlag = False
    if abilities_to_set == True: 
        callback_data = update.callback_query.data
        #First iteraction, calculate the scores
        ability_scores = []
        message = ""
        if callback_data == "AUTO":
            #Full auto mode allows the user to skip the whole process and get a character with random stats
            tmp_char[update.effective_chat.id]["tmp_character"]["ability_scores"] = {}
            for i in range(6):
                rolls = [random.randint(1, 6) for j in range(4)]
                rolls.remove(min(rolls))
                score = sum(rolls)
                ability_scores.append(score)
            with open('5eDefaults/sheetData.json') as f:
                data = json.load(f)
            abilities = [stat['display_name'] for stat in data['stats'].values()]
            for ability in abilities:
                tmp_char[update.effective_chat.id]["tmp_character"]["ability_scores"][ability] = ability_scores.pop()
            #Calcola valori aggiuntivi
            await setModifiers(update, context)
            await setRacialBonuses(update, context)
            # Stampa i punteggi delle abilità assegnati dall'utente
            message = "Your character's ability scores (after racial bonuses) are: "
            for ability, score in tmp_char[update.effective_chat.id]["tmp_character"]["ability_scores"].items():
                message += "\n" + ability + ": " + str(score)
            await context.bot.send_message(chat_id=update.effective_chat.id, text=message)
            await getProficiencies(update, context)
            message = "Your character's proficiencies are:\n"
            for category, ability in tmp_char[update.effective_chat.id]["tmp_character"]["proficiency"].items():
                if ability:
                    abilities = ", ".join(ability)
                else:
                    abilities = "None"
                
                if category == "weapon":
                    category_name = "Weapons"
                elif category == "skill":
                    category_name = "Skills"
                elif category == "armor":
                    category_name = "Armor"
                else:
                    category_name = category.capitalize()  # Nel caso ci siano altre categorie

                message += f"{category_name}: {abilities}\n"

            await context.bot.send_message(chat_id=update.effective_chat.id, text=message)
            FullAutoFlag = True
        elif callback_data == "RANDOM":
            message = "To generate your character's six ability scores randomly, our bot will roll four 6-sided dice and record the total of the highest three dice for you. This process will be repeated five more times, so that you have six numbers in total. These six numbers will be your character's ability scores: "
            # Roll 4d6 and keep the highest 3 rolls for each ability score
            for i in range(6):
                rolls = [random.randint(1, 6) for j in range(4)]
                rolls.remove(min(rolls))
                score = sum(rolls)
                ability_scores.append(score)
        elif callback_data == "FIXED":
            message = "To generate your character's six ability scores using a fixed array, our bot will use the following numbers: "
            ability_scores = [15, 14, 13, 12, 10, 8]

        if not FullAutoFlag:   
            # Salva i punteggi nella conversazione
            tmp_char[update.effective_chat.id]["tmp_character"]["ability_scores"] = {
                "points": ability_scores,
            }
            # Estrae i nomi delle abilità e li salva nello stato della conversazione
            with open('5eDefaults/sheetData.json') as f:
                data = json.load(f)
            abilities = [stat['display_name'] for stat in data['stats'].values()]
            tmp_char[update.effective_chat.id]["tmp_character"]["ability_scores"]["remaining"] = abilities

            message += str(ability_scores[0]) + ", " + str(ability_scores[1]) + ", " + str(ability_scores[2]) + ", " + str(ability_scores[3]) + ", " + str(ability_scores[4]) + ", " + str(ability_scores[5]) + "." + "Please assign these scores to your character's ability scores as you see fit."
            await context.bot.send_message(chat_id=update.effective_chat.id, text=message)

    if not FullAutoFlag:
        remaining_abilities = tmp_char[update.effective_chat.id]["tmp_character"]["ability_scores"]["remaining"]

        remaining_scores = tmp_char[update.effective_chat.id]["tmp_character"]["ability_scores"]["points"]

        if(len(remaining_abilities) == 0):
            #rimuovi variabili ausiliarie
            del tmp_char[update.effective_chat.id]["tmp_character"]["ability_scores"]["remaining"]
            del tmp_char[update.effective_chat.id]["tmp_character"]["ability_scores"]["points"]  
            # Calcola valori aggiuntivi
            await setModifiers(update, context)
            await setRacialBonuses(update, context)
            # Stampa i punteggi delle abilità assegnati dall'utente
            message = "Your character's ability scores are: "
            for ability, score in tmp_char[update.effective_chat.id]["tmp_character"]["ability_scores"].items():
                message += "\n" + ability + ": " + str(score)
            await context.bot.send_message(chat_id=update.effective_chat.id, text=message)
            await getProficiencies(update, context)
            message = "Your character's proficiencies are:\n"
            for category, ability in tmp_char[update.effective_chat.id]["tmp_character"]["proficiency"].items():
                if ability:
                    abilities = ", ".join(ability)
                else:
                    abilities = "None"
                
                if category == "weapon":
                    category_name = "Weapons"
                elif category == "skill":
                    category_name = "Skills"
                elif category == "armor":
                    category_name = "Armor"
                else:
                    category_name = category.capitalize()  # Nel caso ci siano altre categorie

                message += f"{category_name}: {abilities}\n"

            await context.bot.send_message(chat_id=update.effective_chat.id, text=message)
        else: 
            ability = remaining_abilities[0]
            keyboard = [    
                [str(score) for score in remaining_scores]
            ]
            reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
            message = "What score would you like to assign to your " + ability + " ability?"
            await context.bot.send_message(chat_id=update.effective_chat.id, text=message, reply_markup=reply_markup)
            return SCORES
    
    await setMaxWeight(update, context)
    if tmp_char[update.effective_chat.id]["tmp_character"]["inventory"]["armor"]: #List is not empty
        for item in tmp_char[update.effective_chat.id]["tmp_character"]["inventory"]["armor"]:
            ArmorChoiceFlag = False
            if " or " in item:
                choices = item.split(" or ")
                kb = []
                for choice in choices:
                    if await checkWeightClearance(update, context, await getArmorInfo(update, context, choice, True)):
                        armor = await getArmorInfo(update, context, choice)
                        kb.append([armor])
                
                if kb:
                    reply_markup = ReplyKeyboardMarkup(kb, one_time_keyboard=True)
                    message = "Choose one of the following items: "
                    await context.bot.send_message(chat_id=update.effective_chat.id, text=message, reply_markup=reply_markup)
                    #Remove the item from the inventory
                    tmp_char[update.effective_chat.id]["tmp_character"]["inventory"]["armor"].remove(item)
                    ArmorChoiceFlag = True #Flag to check if the user has to choose an armor, in this way the function checks the weights of all the armors that the user has and we dont have to check it later
                else:
                    message = "You can't carry any of these weapons due to weight restrictions1"
                    info = "Item: " + item + "\nWeight: " + str(total_weight) + " lb" + "\nCarrying now: " + str(tmp_char[update.effective_chat.id]["tmp_character"]["current_weight"]) + " lb" + "\nMax weight: " + str(tmp_char[update.effective_chat.id]["tmp_character"]["max_weight"]) + " lb"
                    message += "\n\n" + info
                    await context.bot.send_message(chat_id=update.effective_chat.id, text=message, reply_markup=reply_markup)
            else:
                item_weight = await getArmorInfo(update, context, item, True)
                await updateWeight(update, context, item_weight)
                await context.bot.send_message(chat_id=update.effective_chat.id, text="You chose " + item + " armor")
        if ArmorChoiceFlag:
            return CHOOSE_ARMOR

    #If there is no armor selected or there was only one choice, then select weapons
    if tmp_char[update.effective_chat.id]["tmp_character"]["inventory"]["weapons"]:
        WeaponChoiceFlag = False
        for item in tmp_char[update.effective_chat.id]["tmp_character"]["inventory"]["weapons"]:
            if " or " in item:
                choices = item.split(" or ")
                kb = []
                for choice in choices:
                    #Check if it's a general choice or a specific one
                    if "any" in choice:
                        category = await checkForWeaponType(update, context, choice)
                        counter = 0
                        if "+" in category:
                            weapon_types = category.split("+")
                            for weapon_type in weapon_types:
                                with open('5eDefaults/weapons.json') as f:
                                    data = json.load(f)
                                for weapon in data[weapon_type]:
                                    if await checkWeightClearance(update, context, await getWeaponInfo(update, context, weapon["name"], True)) and counter < 64:
                                        weaponData = await getWeaponInfo(update, context, weapon["name"])
                                        kb.append([weaponData])
                                        counter += 1
                        else:
                            if bool(re.search(r'\d', item)):
                                quantity, item = item.split(" ", 1)  # Split only at the first space
                                quantity = int(quantity)
                            else:
                                quantity = 1
                            with open('5eDefaults/weapons.json') as f:
                                data = json.load(f)
                            for weapon in data[category]:
                                item_weight = await getWeaponInfo(update, context, weapon["name"], True)
                                total_weight = float(item_weight) * quantity
                                if await checkWeightClearance(update, context, total_weight):
                                    weaponData = await getWeaponInfo(update, context, weapon["name"])
                                    kb.append([weaponData])
                    else:
                        if bool(re.search(r'\d', choice)):
                            quantity, choice = choice.split(" ", 1)  # Split only at the first space
                            quantity = int(quantity)
                        else:
                            quantity = 1

                        item_weight = await getWeaponInfo(update, context, choice, True)
                        total_weight = int(item_weight) * quantity
                        if await checkWeightClearance(update, context, total_weight):
                            weapon = await getWeaponInfo(update, context, choice)
                            kb.append([weapon])
                
                if kb:
                    reply_markup = ReplyKeyboardMarkup(kb, one_time_keyboard=True)
                    message = "Choose one of the following weapons: "
                    await context.bot.send_message(chat_id=update.effective_chat.id, text=message, reply_markup=reply_markup)
                    #Remove the item from the inventory
                    tmp_char[update.effective_chat.id]["tmp_character"]["inventory"]["weapons"].remove(item)
                    WeaponChoiceFlag = True #Works like ArmorChoiceFlag
                else:
                    message = "You can't carry any of these weapons due to weight restrictions2"
                    info = "Item: " + item + "\nWeight: " + str(total_weight) + " lb" + "\nCarrying now: " + str(tmp_char[update.effective_chat.id]["tmp_character"]["current_weight"]) + " lb" + "\nMax weight: " + str(tmp_char[update.effective_chat.id]["tmp_character"]["max_weight"]) + " lb"
                    message += "\n\n" + info
                    await context.bot.send_message(chat_id=update.effective_chat.id, text=message, reply_markup=reply_markup)
            else:
                if bool(re.search(r'\d', item)):
                    quantity, item = item.split(" ", 1)  # Split only at the first space
                    quantity = int(quantity)
                else:
                    quantity = 1

                item_weight = await getWeaponInfo(update, context, item, True)
                total_weight = float(item_weight) * quantity
                if await checkWeightClearance(update, context, total_weight):
                    await updateWeight(update, context, total_weight)
                    await context.bot.send_message(chat_id=update.effective_chat.id, text="You chose " + item + " weapon")
                else:
                    message = "You can't carry any of these weapons due to weight restrictions3"
                    info = "Item: " + item + "\nWeight: " + str(total_weight) + " lb" + "\nCarrying now: " + str(tmp_char[update.effective_chat.id]["tmp_character"]["current_weight"]) + " lb" + "\nMax weight: " + str(tmp_char[update.effective_chat.id]["tmp_character"]["max_weight"]) + " lb"
                    message += "\n\n" + info
                    await context.bot.send_message(chat_id=update.effective_chat.id, text=message, reply_markup=reply_markup)
        if WeaponChoiceFlag:
            return CHOOSE_WEAPONS

    #If there is no weapon selected or there was only one choice, then save the character
    await saveCharacter(update, context)
    return ConversationHandler.END

async def saveScores(update, context):
    """
    Support function for the setAbilityScores function.

    This function is responsible for processing the user's choice of ability score to assign to a specific ability. The function saves the user's choice and removes the ability score from the list of available scores. The function then returns to the setAbilityScores function to handle the user's next choice.
    """
    global tmp_char
    ability = tmp_char[update.effective_chat.id]["tmp_character"]["ability_scores"]["remaining"][0]
    score = update.message.text
    tmp_char[update.effective_chat.id]["tmp_character"]["ability_scores"][ability] = score
    tmp_char[update.effective_chat.id]["tmp_character"]["ability_scores"]["remaining"].remove(ability)
    tmp_char[update.effective_chat.id]["tmp_character"]["ability_scores"]["points"].remove(int(score))
    next_state = await setAbilityScores(update, context)
    return next_state

async def setModifiers(update, context):
    """
    Calculate the character's ability score modifiers.
    """

    if "ability_modifiers" not in tmp_char[update.effective_chat.id]["tmp_character"]:
        tmp_char[update.effective_chat.id]["tmp_character"]["ability_modifiers"] = {}
    status = "Added ability modifiers to character sheet."
    for ability in tmp_char[update.effective_chat.id]["tmp_character"]["ability_scores"]:
        score = tmp_char[update.effective_chat.id]["tmp_character"]["ability_scores"][ability]
        modifier = math.floor((int(score) - 10) / 2)
        tmp_char[update.effective_chat.id]["tmp_character"]["ability_modifiers"][ability] = modifier
        status += "\n- " + ability + ": " + str(modifier)

async def setRacialBonuses(update, context):
    """
    Apply the character's racial bonuses to the ability scores.
    """

    with open('5eDefaults/races.json') as f:
        data = json.load(f)

    race = tmp_char[update.effective_chat.id]["tmp_character"]["race"]
    subrace = tmp_char[update.effective_chat.id]["tmp_character"]["subrace"]
    race_modifier = data.get(race).get("default").get("ability_score_modifiers")
    subrace_modifier = None
    if subrace is not None:
        subraces_choice = data.get(race).get("subraces_choice")
        if subraces_choice:
            for option in subraces_choice["options"]:
                if option["display_name"] == subrace:
                    subrace_modifier = option.get("ability_score_modifiers")

    for ability in tmp_char[update.effective_chat.id]["tmp_character"]["ability_scores"]:
        for ability_rm, modifier_rm in race_modifier.items():
            if ability.lower() == ability_rm.lower():
                ability_score = int(tmp_char[update.effective_chat.id]["tmp_character"]["ability_scores"][ability])
                tmp_char[update.effective_chat.id]["tmp_character"]["ability_scores"][ability] = ability_score + modifier_rm
        if subrace_modifier is not None:
            for ability_sm, modifier_sm in subrace_modifier.items():
                if ability.lower() == ability_sm.lower():
                    ability_score = int(tmp_char[update.effective_chat.id]["tmp_character"]["ability_scores"][ability])
                    tmp_char[update.effective_chat.id]["tmp_character"]["ability_scores"][ability] = ability_score + modifier_sm

async def getProficiencies(update, context):
    """
    Assign the character's proficiencies based on its race, subrace and class.
    """

    with open('5eDefaults/races.json') as f:
        data = json.load(f)

    race = tmp_char[update.effective_chat.id]["tmp_character"]["race"]
    subrace = tmp_char[update.effective_chat.id]["tmp_character"]["subrace"]
    char_class = tmp_char[update.effective_chat.id]["tmp_character"]["class"]

    # Inizializza le liste vuote per le proficiency
    weapon_proficiencies_race = []
    skill_proficiencies_race = []
    armor_proficiencies_race = []
    weapon_proficiencies_subrace = []
    skill_proficiencies_subrace = []
    armor_proficiencies_subrace = []

    race_data = data.get(race)
    if race_data:
        race_default = race_data.get("default")
        if race_default:
            proficiency_data = race_default.get("proficiency")
            if proficiency_data:
                weapon_proficiencies_race = proficiency_data.get("weapons", [])
                skill_proficiencies_race = proficiency_data.get("skill", [])
                armor_proficiencies_race = proficiency_data.get("armor", [])

    if subrace is not None:
        subraces_choice = race_data.get("subraces_choice")
        if subraces_choice:
            for option in subraces_choice["options"]:
                if option["display_name"] == subrace:
                    proficiency_data = option.get("proficiency")
                    if proficiency_data:
                        weapon_proficiencies_subrace = proficiency_data.get("weapons", [])
                        skill_proficiencies_subrace = proficiency_data.get("skill", [])
                        armor_proficiencies_subrace = proficiency_data.get("armor", [])
                    break

    with open("5eDefaults/classes.json") as f:
        data = json.load(f)
    
    class_data = data.get(char_class)
    if class_data:
        proficiency_data = class_data.get("proficiency")
        if proficiency_data:
            weapon_proficiencies_class = proficiency_data.get("weapons", [])
            skill_proficiencies_class = proficiency_data.get("skill", [])
            armor_proficiencies_class = proficiency_data.get("armor", [])

    tmp_char[update.effective_chat.id]["tmp_character"]["proficiency"] = {
        "weapons": weapon_proficiencies_race + weapon_proficiencies_subrace + weapon_proficiencies_class,
        "skill": skill_proficiencies_race + skill_proficiencies_subrace + skill_proficiencies_class,
        "armor": armor_proficiencies_race + armor_proficiencies_subrace + armor_proficiencies_class
    }
    
async def setMaxWeight(update, context):
    tmp_char[update.effective_chat.id]["tmp_character"]["max_weight"] = (float(tmp_char[update.effective_chat.id]["tmp_character"]["ability_scores"]["Strength"]) + float(tmp_char[update.effective_chat.id]["tmp_character"]["ability_modifiers"]["Strength"]))*15
    return

async def updateWeight(update, context, item_weight):
    if item_weight is None:
        print("Item weight is None")
        return 0
    tmp_char[update.effective_chat.id]["tmp_character"]["current_weight"] = float(tmp_char[update.effective_chat.id]["tmp_character"]["current_weight"]) + float(item_weight)
    return

async def checkForWeaponType(update, context, string):
    if "simple" in string:
        if "melee" in string:
            return "simple_melee"
        elif "ranged" in string:
            return "simple_ranged"
        else:
            return "simple_melee+simple_ranged"
    if "martial" in string:
        if "melee" in string:
            return "martial_melee"
        elif "ranged" in string:
            return "martial_ranged"
        else:
            return "martial_melee+martial_ranged"

async def checkWeightClearance(update, context, item_weight):
    """
    Check if the character has enough weight capacity to carry the item.
    """

    if float(tmp_char[update.effective_chat.id]["tmp_character"]["current_weight"]) + float(item_weight) > float(tmp_char[update.effective_chat.id]["tmp_character"]["max_weight"]):
        return False
    else:
        return True

async def getArmorInfo(update, context, armor, weightFlag = False):
    """
    Retrieve information about a specific armor type.

    This function retrieves information about a specific armor from the 5eDefaults armors JSON file. The function searches for the provided armor name, extracting details like armor class, weight, cost, and any associated effects. If the `weightFlag` parameter is set to `True`, only the armor weight is returned.
    """

    with open("5eDefaults/armors.json") as f:
        data = json.load(f)

    found = False
    for armor_type in data:
        for armors in data[armor_type]:
            if armors["name"] == armor:
                armor_weight = armors["weight"]
                if weightFlag == True:
                    return armor_weight
                armor_class = armors["armor_class"]
                armor_stealth = ""
                armor_price = armors["cost"]
                if armors.get("stealth") == "disadvantage":
                    armor_stealth = "stealth nerf"
                found = True
                break
    
    if found:
        armor = armor + " " + "(" + armor_price + ") " + "\n" + armor_class + " (" + armor_weight + " lb)"
        if armor_stealth != "":
            armor = armor + " (" + armor_stealth + ")"
        return armor
    else:
        print("Armor not found: " + armor)

async def getWeaponInfo(update, context, weapon, weightFlag = False):
    """
    Retrieve information about a specific weapon.

    This function retrieves information about a specific weapon from the 5eDefaults weapons JSON file.
    The function searches for the provided weapon name, extracting details like damage, weight, and cost.
    If the `weightFlag` parameter is set to `True`, only the weapon weight is returned.
    """
    with open("5eDefaults/weapons.json") as f:
        data = json.load(f)

    found = False
    for weapon_type in data:
        for weapons in data[weapon_type]:
            if weapons["name"] == weapon:
                weapon_weight = weapons["weight"]
                if weightFlag == True:
                    return weapon_weight
                weapon_damage = weapons["damage"]
                weapon_price = weapons["cost"]
                found = True
                break
    if found:
        weapon = weapon + " " + "(" + weapon_price + ") " + "\n" + weapon_damage + " (" + weapon_weight + " lb)"
        return weapon
    else:
        print("Weapon not found: " + weapon)

async def chooseArmor(update, context):
    """
    Handle the selection of armor by the user.

    This function is responsible for handling the user's selection of armor during character creation. It verifies if the user has to choose between two armor types and prompts the user to choose one. If the user has to choose between two armor types, the function returns the ARMOR state to handle the user's choice. If the user does not have to choose between two armor types, the function assigns the selected armor to the character's inventory and continues with the character creation process. 
    
    The weapons interaction is similar to the armor one, but has another check to see if the user is being prompted to choose a number of weapons (eg: 4 Javelins) and handles the weight increase accordingly.
    """
    armor = update.message.text
    armor = armor.split("(")[0].strip()
    item_weight = await getArmorInfo(update, context, armor, True)
    await updateWeight(update, context, item_weight)
    tmp_char[update.effective_chat.id]["tmp_character"]["inventory"]["armor"].append(armor)
        
    await context.bot.send_message(chat_id=update.effective_chat.id, text="You chose " + armor + " armor")
    
    if tmp_char[update.effective_chat.id]["tmp_character"]["inventory"]["weapons"]:
        WeaponChoiceFlag = False
        for item in tmp_char[update.effective_chat.id]["tmp_character"]["inventory"]["weapons"]:
            if " or " in item:
                choices = item.split(" or ")
                kb = []
                for choice in choices:
                    #Check if it's a general choice or a specific one
                    if "any" in choice:
                        category = await checkForWeaponType(update, context, choice)
                        counter = 0
                        if "+" in category:
                            weapon_types = category.split("+")
                            for weapon_type in weapon_types:
                                with open('5eDefaults/weapons.json') as f:
                                    data = json.load(f)
                                for weapon in data[weapon_type]:
                                    if await checkWeightClearance(update, context, await getWeaponInfo(update, context, weapon["name"], True)) and counter < 64:
                                        weaponData = await getWeaponInfo(update, context, weapon["name"])
                                        kb.append([weaponData])
                                        counter += 1
                        else:
                            if bool(re.search(r'\d', item)):
                                quantity, item = item.split(" ", 1)  # Split only at the first space
                                quantity = int(quantity)
                            else:
                                quantity = 1
                            with open('5eDefaults/weapons.json') as f:
                                data = json.load(f)
                            for weapon in data[category]:
                                item_weight = await getWeaponInfo(update, context, weapon["name"], True)
                                total_weight = float(item_weight) * quantity
                                if await checkWeightClearance(update, context, total_weight):
                                    weaponData = await getWeaponInfo(update, context, weapon["name"])
                                    kb.append([weaponData])
                    else:
                        if bool(re.search(r'\d', choice)):
                            quantity, choice = choice.split(" ", 1)  # Split only at the first space
                            quantity = int(quantity)
                        else:
                            quantity = 1

                        item_weight = await getWeaponInfo(update, context, choice, True)
                        total_weight = int(item_weight) * quantity
                        if await checkWeightClearance(update, context, total_weight):
                            weapon = await getWeaponInfo(update, context, choice)
                            kb.append([weapon])
                
                if kb:
                    reply_markup = ReplyKeyboardMarkup(kb, one_time_keyboard=True)
                    message = "Choose one of the following weapons: "
                    await context.bot.send_message(chat_id=update.effective_chat.id, text=message, reply_markup=reply_markup)
                    #Remove the item from the inventory
                    tmp_char[update.effective_chat.id]["tmp_character"]["inventory"]["weapons"].remove(item)
                    WeaponChoiceFlag = True #Works like ArmorChoiceFlag
                else:
                    message = "You can't carry any of these weapons due to weight restrictions4"
                    info = "Item: " + item + "\nWeight: " + str(total_weight) + " lb" + "\nCarrying now: " + str(tmp_char[update.effective_chat.id]["tmp_character"]["current_weight"]) + " lb" + "\nMax weight: " + str(tmp_char[update.effective_chat.id]["tmp_character"]["max_weight"]) + " lb"
                    message += "\n\n" + info
                    await context.bot.send_message(chat_id=update.effective_chat.id, text=message, reply_markup=reply_markup)
            else:
                if bool(re.search(r'\d', item)):
                    quantity, item = item.split(" ", 1)  # Split only at the first space
                    quantity = int(quantity)
                else:
                    quantity = 1

                item_weight = await getWeaponInfo(update, context, item, True)
                total_weight = float(item_weight) * quantity
                if await checkWeightClearance(update, context, total_weight):
                    await updateWeight(update, context, total_weight)
                    await context.bot.send_message(chat_id=update.effective_chat.id, text="You chose " + item + " weapon")
                else:
                    message = "You can't carry any of these weapons due to weight restrictions5"
                    info = "Item: " + item + "\nWeight: " + str(total_weight) + " lb" + "\nCarrying now: " + str(tmp_char[update.effective_chat.id]["tmp_character"]["current_weight"]) + " lb" + "\nMax weight: " + str(tmp_char[update.effective_chat.id]["tmp_character"]["max_weight"]) + " lb"
                    message += "\n\n" + info
                    await context.bot.send_message(chat_id=update.effective_chat.id, text=message, reply_markup=reply_markup)
        if WeaponChoiceFlag:
            return CHOOSE_WEAPONS
    
    #If there is no weapon selected or there was only one choice, then save the character
    await saveCharacter(update, context)
    return ConversationHandler.END

async def chooseWeapons(update, context):
    """
    Handle the selection of weapons by the user.

    This function handles the user's selection of weapons during character creation. It extracts the weapon name from the user's input and uses the 'getWeaponInfo' function to retrieve weapon information. The selected weapon is added to the character's inventory, and if the user has to choose between weapon options, the function prompts the user to make a choice. If the user needs to choose, it returns the CHOOSE_WEAPONS state to continue handling the choice. If there's no need for further weapon choices or if the user has made a choice, the character creation process is saved and ended.
    
    The weapons interaction is similar to the armor one, but has another check to see if the user is being prompted to choose a number of weapons (eg: 4 Javelins) and handles the weight increase accordingly.
    """
    weapon = update.message.text
    weapon = weapon.split("(")[0].strip()
    item_weight = await getWeaponInfo(update, context, weapon, True)
    await updateWeight(update, context, item_weight)
    tmp_char[update.effective_chat.id]["tmp_character"]["inventory"]["weapons"].append(weapon)
    await context.bot.send_message(chat_id=update.effective_chat.id, text="You chose " + weapon + " weapon")


    if tmp_char[update.effective_chat.id]["tmp_character"]["inventory"]["weapons"]:
        WeaponChoiceFlag = False
        for item in tmp_char[update.effective_chat.id]["tmp_character"]["inventory"]["weapons"]:
            if " or " in item:
                choices = item.split(" or ")
                kb = []
                for choice in choices:
                    #Check if it's a general choice or a specific one
                    if "any" in choice:
                        category = await checkForWeaponType(update, context, choice)
                        counter = 0
                        if "+" in category:
                            weapon_types = category.split("+")
                            for weapon_type in weapon_types:
                                with open('5eDefaults/weapons.json') as f:
                                    data = json.load(f)
                                for weapon in data[weapon_type]:
                                    if await checkWeightClearance(update, context, await getWeaponInfo(update, context, weapon["name"], True)) and counter < 64:
                                        weaponData = await getWeaponInfo(update, context, weapon["name"])
                                        kb.append([weaponData])
                                        counter += 1
                        else:
                            if bool(re.search(r'\d', item)):
                                quantity, item = item.split(" ", 1)  # Split only at the first space
                                quantity = int(quantity)
                            else:
                                quantity = 1
                            with open('5eDefaults/weapons.json') as f:
                                data = json.load(f)
                            for weapon in data[category]:
                                item_weight = await getWeaponInfo(update, context, weapon["name"], True)
                                total_weight = float(item_weight) * quantity
                                if await checkWeightClearance(update, context, total_weight):
                                    weaponData = await getWeaponInfo(update, context, weapon["name"])
                                    kb.append([weaponData])
                    else:
                        if bool(re.search(r'\d', choice)):
                            quantity, choice = choice.split(" ", 1)  # Split only at the first space
                            quantity = int(quantity)
                        else:
                            quantity = 1

                        item_weight = await getWeaponInfo(update, context, choice, True)
                        total_weight = int(item_weight) * quantity
                        if await checkWeightClearance(update, context, total_weight):
                            weapon = await getWeaponInfo(update, context, choice)
                            kb.append([weapon])
                
                if kb:
                    reply_markup = ReplyKeyboardMarkup(kb, one_time_keyboard=True)
                    message = "Choose one of the following weapons: "
                    await context.bot.send_message(chat_id=update.effective_chat.id, text=message, reply_markup=reply_markup)
                    #Remove the item from the inventory
                    tmp_char[update.effective_chat.id]["tmp_character"]["inventory"]["weapons"].remove(item)
                    WeaponChoiceFlag = True #Works like ArmorChoiceFlag
                else:
                    message = "You can't carry any of these weapons due to weight restrictions6"
                    info = "Item: " + item + "\nWeight: " + str(total_weight) + " lb" + "\nCarrying now: " + str(tmp_char[update.effective_chat.id]["tmp_character"]["current_weight"]) + " lb" + "\nMax weight: " + str(tmp_char[update.effective_chat.id]["tmp_character"]["max_weight"]) + " lb"
                    message += "\n\n" + info
                    await context.bot.send_message(chat_id=update.effective_chat.id, text=message, reply_markup=reply_markup)
            else:
                if bool(re.search(r'\d', item)):
                    quantity, item = item.split(" ", 1)  # Split only at the first space
                    quantity = int(quantity)
                else:
                    quantity = 1

                item_weight = await getWeaponInfo(update, context, item, True)
                total_weight = float(item_weight) * quantity
                if await checkWeightClearance(update, context, total_weight):
                    await updateWeight(update, context, total_weight)
                    await context.bot.send_message(chat_id=update.effective_chat.id, text="You chose " + item + " weapon")
                else:
                    message = "You can't carry any of these weapons due to weight restrictions7"
                    info = "Item: " + item + "\nWeight: " + str(total_weight) + " lb" + "\nCarrying now: " + str(tmp_char[update.effective_chat.id]["tmp_character"]["current_weight"]) + " lb" + "\nMax weight: " + str(tmp_char[update.effective_chat.id]["tmp_character"]["max_weight"]) + " lb"
                    message += "\n\n" + info
                    await context.bot.send_message(chat_id=update.effective_chat.id, text=message, reply_markup=reply_markup)
        if WeaponChoiceFlag:
            return CHOOSE_WEAPONS
    #If there is no weapon selected or there was only one choice, then save the character
    await saveCharacter(update, context)
    return ConversationHandler.END
 
async def saveCharacter(update, context):
    """
    Save the character to the database.
    """

    global tmp_char
    new_char = tmp_char[update.effective_chat.id]["tmp_character"]
    with open(dbPath, "r") as f:
        data = json.load(f)

    for user in data["users"]:
        if str(user.get("telegramID")) == str(update.effective_chat.id):
            if "characters" not in user:
                user["characters"] = []
            user["characters"].append(new_char)
            break
    with open(dbPath, "w") as f:
        json.dump(data, f, indent=4)
    
    #Reset tmp_char
    tmp_char[update.effective_chat.id]["tmp_character"] = {}

    #TODO: solo menu -- da testare! Fintier 
    keyboard = [
        [
            InlineKeyboardButton("Back to menu", callback_data=str("MENU"))
        ]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    message = "Congratulations, your character has been updated! If you wish to modify it, you can do so from the menu."
    await context.bot.send_message(chat_id=update.effective_chat.id, text=message, reply_markup=reply_markup)
    return MENU
# ---------------------------------- MODIFY CHARACTER ----------------------------------
async def chooseAttributePrompt(update, context):
    """ This function is called when the user wants to modify a character. It prompts the user to choose which attribute to modify """
    with open("database/char_sheet.json", "r") as fp:
        attributes = json.load(fp)
    attributes = [*attributes]

    keyboard = []
    for attribute in attributes:
        if attribute != "ability_modifiers" and attribute != "current_weight" and attribute != "max_weight" and attribute != "level"and attribute != "features" and attribute != "ability_scores" and attribute != "inventory":
            keyboard.append([attribute])
    keyboard.append(["Finished"])

    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, input_field_placeholder='Which field you want to modify?')
    message = "You weren't honest with me, were you? You can't fool me, I know you want to change something about your story. What is it?"
    disclaimer = "\n⚠️ CHARACTER CUSTOMIZATION DISCLAIMER ⚠️ \nGreetings, brave adventurer! As you embark on the path of character modification, remember that the realm of possibilities is vast and uncharted. Feel free to mold your character's weapons and armor in unique ways, deviating from the standard creation rules. However, heed this caution: the rules of your campaign may vary. Before you reshape your destiny, confer with your storyteller to ensure your creative choices align with the tapestry of their world. May your customization be a beacon of self-expression on your epic journey!"
    message += "\n\n" + disclaimer
    await context.bot.send_message(chat_id=update.effective_chat.id, text=message, reply_markup=reply_markup)
    return ATTRIBUTE_CHOICE

async def chooseAttribute(update, context):
    """ This function is called when the user chooses an attribute to modify, it handles the switch case and prompts the user to insert the new value for the chosen attribute (displaying the correct custom keyboard, if needed).
    It also handles the "Finished" choice, which saves the character to the database and ends the conversation."""
    choice = update.message.text

    if choice == "Finished":
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Your character has been updated!")
        await mainMenuChoice(update, context)
        return ConversationHandler.END
    if "attributesToModify" not in tmp_char[update.effective_chat.id]["tmp_character"]:
        tmp_char[update.effective_chat.id]["tmp_character"]["attributesToModify"] = []
    tmp_char[update.effective_chat.id]["tmp_character"]["attributesToModify"].append(choice)
    if choice == "name":
        await context.bot.send_message(chat_id=update.effective_chat.id, text="What should I call you?")
    elif choice == "race":
        with open("5eDefaults/races.json", "r") as fp:
            races = json.load(fp)
        races = [*races]

        reply_keyboard = []
        for race in races:
            reply_keyboard.append([race])

        race_kb=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=True, input_field_placeholder='Choose your race'
        )
        
        message="Choose a new Race:"
        await context.bot.send_message(chat_id=update.effective_chat.id, text=message, reply_markup=race_kb)
    elif choice == "subrace":
        with open("5eDefaults/races.json", "r") as fp:
            races = json.load(fp)
        selected_char = tmp_char[update.effective_chat.id]["tmp_character"]["name"]
        with open(dbPath, "r") as f:
            data = json.load(f)
        for user in data["users"]:
            for char in user["characters"]:
                if char["name"] == selected_char:
                    race = char["race"]
                    break
        if "subraces_choice" in races[race]: 
            reply_keyboard = []  
            # acquiring list of available subraces
            for subrace in races[race]["subraces_choice"]["options"]:
                reply_keyboard.append([subrace["display_name"]])
            await context.bot.send_message(chat_id=update.effective_chat.id, text="What's your subrace?", reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, input_field_placeholder='Choose your subrace'))
        else:
            await context.bot.send_message(chat_id=update.effective_chat.id, text="You don't have any subrace, you're a " + race + "!")
            await modifyPrompt(update, context)
            return ATTRIBUTE_CHOICE
    elif choice == "class":
        with open("5eDefaults/classes.json", "r") as fp:
            classes = json.load(fp)
        # acquiring list of available classes
        classes = [*classes]

        reply_keyboard = []
        for className in classes:
            reply_keyboard.append([className])

        class_kb=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=True, input_field_placeholder='Choose your class'
        )
        await context.bot.send_message(chat_id=update.effective_chat.id, text="What's your class?", reply_markup=class_kb)
    elif choice == "background":
        with open("5eDefaults/backgrounds.json", "r") as fp:
            backgrounds = json.load(fp)
        # acquiring list of available races
        backgrounds = [*backgrounds]

        reply_keyboard = []
        for background in backgrounds:
            reply_keyboard.append([background])

        subrace_kb=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=True, input_field_placeholder='Choose your background'
        )
        await context.bot.send_message(chat_id=update.effective_chat.id, text="What's your background?", reply_markup=subrace_kb)
    elif choice == "background story":
        keyboard = [
            [InlineKeyboardButton("I want to write the story", callback_data=str("WRITE")),
             InlineKeyboardButton("Generate a random story", callback_data=str("GENERATE")),],
            [InlineKeyboardButton("No thanks", callback_data=str("NONE"))]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)
        message="Would you like to create a new background story for your character?"
        await context.bot.send_message(chat_id=update.effective_chat.id, text=message, reply_markup=reply_markup)
        return BACKSTORIES_MOD
    elif choice == "weapons":
        selected_char = tmp_char[update.effective_chat.id]["tmp_character"]["name"]
        weapons = []
        with open(dbPath, "r") as f:
            data = json.load(f)
        for user in data["users"]:
            for char in user["characters"]:
                if char["name"] == selected_char:
                    weapons = char["inventory"]["weapons"]
                    break
        kb = []
        for weapon in weapons:
            kb.append([weapon])
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Which weapon do you want to change?", reply_markup=ReplyKeyboardMarkup(kb, one_time_keyboard=True, input_field_placeholder='Choose a weapon to be replaced'))
        return WEAPON_TYPE_MOD
    elif choice == "armor":
        keyboard = [
            [("Light Armor")],
            [("Medium Armor")],
            [("Heavy Armor")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
        message = "Choose your armor class:"
        await context.bot.send_message(chat_id=update.effective_chat.id, text=message, reply_markup=reply_markup)
        return ARMOR_MOD
    else:
        with open("database/char_sheet.json", "r") as fp:
            attributes = json.load(fp)
        attributes = [*attributes]

        keyboard = []
        for attribute in attributes:
            if attribute != "ability_modifiers" and attribute != "current_weight" and attribute != "max_weight" and attribute != "level"and attribute != "features" and attribute != "ability_scores" and attribute != "inventory":
                keyboard.append([attribute])
        keyboard.append(["Finished"])
        await context.bot.send_message(chat_id=update.effective_chat.id, text="You can't modify this attribute, please choose one allowed", reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, input_field_placeholder='Which field you want to modify?'))
        return ATTRIBUTE_CHOICE
    return CHANGES_HANDLER

async def modifyAttribute(update, context):
    """"This function is called when the user wants to modify an attribute of his character. Handles the input and modifies the tmp_char dictionary."""
    global tmp_char
    choices = tmp_char[update.effective_chat.id]["tmp_character"]["attributesToModify"]
    json_tmp_char = json.dumps(tmp_char, indent=4)
    if "modified" not in tmp_char[update.effective_chat.id]["tmp_character"]:
        tmp_char[update.effective_chat.id]["tmp_character"]["modified"] = []
    for attribute in choices:
        if attribute == "weapons":
            newWeapon = update.message.text
            newWeapon = newWeapon.split("(")[0].strip()
            selected_char = tmp_char[update.effective_chat.id]["tmp_character"]["name"]
            weapons = []
            with open(dbPath, "r") as f:
                data = json.load(f)
            for user in data["users"]:
                for char in user["characters"]:
                    if char["name"] == selected_char:
                        weapons = char["inventory"]["weapons"]
                        break
            for weapon in weapons:
                if weapon == str(tmp_char[update.effective_chat.id]["tmp_character"]["weaponToModify"]):
                    weapons.remove(weapon)
                    weapons.append(newWeapon)
                    break
            tmp_char[update.effective_chat.id]["tmp_character"][attribute] = weapons
        elif attribute == "armor":
            newArmor = update.message.text
            newArmor = newArmor.split("(")[0].strip()	
            tmp_char[update.effective_chat.id]["tmp_character"][attribute] = newArmor
        else:
            if attribute == "name":
                tmp_char[update.effective_chat.id]["tmp_character"]["old_name"] = tmp_char[update.effective_chat.id]["tmp_character"]["name"]
            if attribute == "race" or attribute == "subrace":
                tmp_char[update.effective_chat.id]["tmp_character"]["old_race"] = tmp_char[update.effective_chat.id]["tmp_character"]["race"]
                tmp_char[update.effective_chat.id]["tmp_character"]["old_subrace"] = tmp_char[update.effective_chat.id]["tmp_character"]["subrace"]
            tmp_char[update.effective_chat.id]["tmp_character"][attribute] = update.message.text
        tmp_mod_value = attribute
        tmp_char[update.effective_chat.id]["tmp_character"]["modified"].append(attribute)
        tmp_char[update.effective_chat.id]["tmp_character"]["attributesToModify"].remove(attribute)
    
    for key in tmp_char[update.effective_chat.id]["tmp_character"]["attributesToModify"]:
        print("attributes in Attr" + key)
    for key in tmp_char[update.effective_chat.id]["tmp_character"]["modified"]:
        print("modified " + key)
    # If the attribute "race" has been modified, there is a great probability that the subrace
    # previously choosen is not compatibile anymore. So we have to check if the subrace is still valid, 
    # and if not, we have to ask the user to choose a new one.
    if str(tmp_mod_value) == "race":
        print("prompting subrace")
        tmp_mod_value = "validated"
        with open(dbPath, "r") as f:
            data = json.load(f)
        for user in data["users"]:
            if str(user.get("telegramID")) == str(update.effective_chat.id):
                for character in user["characters"]:
                    if character["name"] == tmp_char[update.effective_chat.id]["tmp_character"]["name"]:
                        subrace = character["subrace"]
                        break
                break
        with open("5eDefaults/races.json", "r") as fp:
            races = json.load(fp)
        race = tmp_char[update.effective_chat.id]["tmp_character"]["race"]
        if "subraces_choice" not in races[race]:
            #Like in human and dragonborn
            tmp_char[update.effective_chat.id]["tmp_character"]["subrace"] = ""
            tmp_char[update.effective_chat.id]["tmp_character"]["modified"].append("subrace")
        else:
            for istance in races[race]["subraces_choice"]["options"]:
                if istance["display_name"] == subrace:
                    break #tutto ok, subrazza esiste (anche se raro)
                else:
                    if "subraces_choice" in races[race]: 
                        reply_keyboard = []  
                    # acquiring list of available subraces
                    for subrace in races[race]["subraces_choice"]["options"]:
                        reply_keyboard.append([subrace["display_name"]])
                    reply_markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, input_field_placeholder='Choose your subrace')
                    message = "Your subrace doesn't fit anymore, please choose one of the following:"
                    await context.bot.send_message(chat_id=update.effective_chat.id, text=message, reply_markup=reply_markup)
                    tmp_char[update.effective_chat.id]["tmp_character"]["attributesToModify"].append("subrace")
                    return CHANGES_HANDLER
    #If the user changes his class, we have to change the features of the character
    if str(tmp_mod_value) == "class":
        tmp_char[update.effective_chat.id]["tmp_character"]["modified"].append("features")
        with open("5eDefaults/classes.json", "r") as fp:
            classData = json.load(fp)
        char_class = tmp_char[update.effective_chat.id]["tmp_character"]["class"]
        if "1" in classData[char_class]["levels"]:
            level_data = classData[char_class]["levels"]["1"]
        if "features" in level_data and isinstance(level_data["features"], list):
            tmp_char[update.effective_chat.id]["tmp_character"]["featuresMulti"] = []
            tmp_char[update.effective_chat.id]["tmp_character"]["features"] = []
            for feature in level_data["features"]:
                if "options" not in feature or feature["options"] is None: #The feature does not require any further action
                    player = tmp_char[update.effective_chat.id]["tmp_character"]
                    player["features"].append({"name": feature["display_name"]})
                else:
                    tmp_char[update.effective_chat.id]["tmp_character"]["featuresMulti"].append(feature)
            if tmp_char[update.effective_chat.id]["tmp_character"]["featuresMulti"]:
                keyboard = []
                for feature in tmp_char[update.effective_chat.id]["tmp_character"]["featuresMulti"]:
                    message = "You gained a new feature!" + "\nName: " + feature["display_name"] + "\nDescription: " + feature["description"]
                    keyboard = []
                    for option in feature["options"]:
                        message += "\n- " + option["display_name"] + ": " + option["description"]
                        keyboard.append([InlineKeyboardButton(option["display_name"], callback_data=feature["display_name"]+"-"+option["display_name"])])
                    await context.bot.send_message(chat_id=update.effective_chat.id, text=message, reply_markup=InlineKeyboardMarkup(keyboard))
                return MOD_FEATURES

        if "1" in classData[char_class]["levels"]:
            level_data = classData[char_class]["levels"]["1"]
        if "features" in level_data and isinstance(level_data["features"], list):
            for feature in level_data["features"]:
                if "options" in feature:
                    message = "You gained a new feature!" + "\nName: " + feature["display_name"] + "\nDescription: " + feature["description"]
                    keyboard = []
                    for option in feature["options"]:
                        message += "\n- " + option["display_name"] + ": " + option["description"]
                        keyboard.append([InlineKeyboardButton(option["display_name"], callback_data=feature["display_name"]+"-"+option["display_name"])])
                    await context.bot.send_message(chat_id=update.effective_chat.id, text=message, reply_markup=InlineKeyboardMarkup(keyboard))
                    return INITIAL_FEATURES
        pass
    
    # If everything went smooth and changes are valid, we can save the character to the database    

    if any(key in tmp_char[update.effective_chat.id]["tmp_character"]["modified"] for key in ["subrace", "race"]):
        #remove the old racial bonuses
        with open('5eDefaults/races.json') as f:
            data = json.load(f)

        if "old_race" in tmp_char[update.effective_chat.id]["tmp_character"]:
            race = tmp_char[update.effective_chat.id]["tmp_character"]["old_race"]
        else:
            race = tmp_char[update.effective_chat.id]["tmp_character"]["old_race"]
        
        if "old_subrace" in tmp_char[update.effective_chat.id]["tmp_character"]:
            subrace = tmp_char[update.effective_chat.id]["tmp_character"]["old_subrace"]
        else:
            subrace = tmp_char[update.effective_chat.id]["tmp_character"]["subrace"]
        
        race_modifier = data.get(race).get("default").get("ability_score_modifiers")
        subrace_modifier = None
        if subrace is not None:
            subraces_choice = data.get(race).get("subraces_choice")
            if subraces_choice:
                for option in subraces_choice["options"]:
                    if option["display_name"] == subrace:
                        subrace_modifier = option.get("ability_score_modifiers")

        for ability in tmp_char[update.effective_chat.id]["tmp_character"]["ability_scores"]:
            for ability_rm, modifier_rm in race_modifier.items():
                if ability.lower() == ability_rm.lower():
                    ability_score = int(tmp_char[update.effective_chat.id]["tmp_character"]["ability_scores"][ability])
                    tmp_char[update.effective_chat.id]["tmp_character"]["ability_scores"][ability] = ability_score - modifier_rm
            if subrace_modifier is not None:
                for ability_sm, modifier_sm in subrace_modifier.items():
                    if ability.lower() == ability_sm.lower():
                        ability_score = int(tmp_char[update.effective_chat.id]["tmp_character"]["ability_scores"][ability])
                        tmp_char[update.effective_chat.id]["tmp_character"]["ability_scores"][ability] = ability_score - modifier_sm
        #set the new ones
        await setRacialBonuses(update, context)
        tmp_char[update.effective_chat.id]["tmp_character"]["modified"].append("ability_scores")

    #Checks if the character has to change his proficiencies
    if any(key in tmp_char[update.effective_chat.id]["tmp_character"]["modified"] for key in ["subrace", "race", "class"]):
        await getProficiencies(update, context)
        tmp_char[update.effective_chat.id]["tmp_character"]["modified"].append("proficiency")

    with open(dbPath, "r") as f:
        data = json.load(f)
    for user in data["users"]:
        if str(user.get("telegramID")) == str(update.effective_chat.id):
            for character in user["characters"]:
                if "old_name" in tmp_char[update.effective_chat.id]["tmp_character"] and character["name"] == tmp_char[update.effective_chat.id]["tmp_character"]["old_name"]:
                    for attribute in tmp_char[update.effective_chat.id]["tmp_character"]["modified"]:
                        if attribute == "weapons" or attribute == "armor":
                            character["inventory"][attribute] = tmp_char[update.effective_chat.id]["tmp_character"][attribute]
                        character[attribute] = tmp_char[update.effective_chat.id]["tmp_character"][attribute]
                    break
                elif character["name"] == tmp_char[update.effective_chat.id]["tmp_character"]["name"]:
                    for attribute in tmp_char[update.effective_chat.id]["tmp_character"]["modified"]:
                        if attribute == "weapons" or attribute == "armor":
                            character["inventory"][attribute] = tmp_char[update.effective_chat.id]["tmp_character"][attribute]
                        character[attribute] = tmp_char[update.effective_chat.id]["tmp_character"][attribute]
                    break
            break
    with open(dbPath, "w") as f:
        json.dump(data, f, indent=4)

    await modifyPrompt(update, context)
    return ATTRIBUTE_CHOICE

async def modifyFeatures(update, context):
    """This function is called when the user has to choose a feature from a list of options. It handles the input and modifies the tmp_char dictionary."""
    global tmp_char
    callback_data = update.callback_query.data
    feature, option = callback_data.split("-")
    tmp_char[update.effective_chat.id]["tmp_character"]["features"].append({"name": feature, "option": option})
    del tmp_char[update.effective_chat.id]["tmp_character"]["featuresMulti"]

    with open(dbPath, "r") as f:
        data = json.load(f)
    for user in data["users"]:
        if str(user.get("telegramID")) == str(update.effective_chat.id):
            for character in user["characters"]:
                if character["name"] == tmp_char[update.effective_chat.id]["tmp_character"]["name"]:
                    for attribute in tmp_char[update.effective_chat.id]["tmp_character"]["modified"]:
                        character[attribute] = tmp_char[update.effective_chat.id]["tmp_character"][attribute]
                    break
            break
    with open(dbPath, "w") as f:
        json.dump(data, f, indent=4)

    await modifyPrompt(update, context)
    return ATTRIBUTE_CHOICE

async def weaponTypeMod(update, context):
    """
    Handles the weapon type choice during character modification.
    """
    global tmp_char
    weaponToModify = update.message.text
    tmp_char[update.effective_chat.id]["tmp_character"]["weaponToModify"] = weaponToModify
    with open("5eDefaults/weapons.json") as f:
        data = json.load(f)
    weapon_types = []
    for weapon_type in data:
        weapon_type = weapon_type.replace("_", " ").capitalize()
        # TODO: Aggiungi le emoji corrispondenti alle categorie delle armi - non funziona
        if weapon_type == "Simple melee":
            weapon_type = "\U0001F5E1" + " " + weapon_type
        elif weapon_type == "Simple ranged":
            weapon_type = "\U0001F3F9" + " " + weapon_type
        elif weapon_type == "Martial melee":
            weapon_type = "\U00002694" + " " + weapon_type
        elif weapon_type == "Martial ranged":
            weapon_type = "\U0001F3AF" + " " + weapon_type
        weapon_types.append([weapon_type])

    await context.bot.send_message(chat_id=update.effective_chat.id, text="Choose the new weapon type:", reply_markup=ReplyKeyboardMarkup(weapon_types, one_time_keyboard=True, input_field_placeholder='Choose the new weapon type'))
    return WEAPON_CHOOSE_MOD

async def weaponChooseMod(update, context):
    """
    Handles the weapon choice during character modification.
    """
    weapon_type = update.message.text
    weapon_type = weapon_type.split(" ")[1] + " " + weapon_type.split(" ")[2]
    weapon_type = weapon_type.lower().replace(" ", "_")
    with open("5eDefaults/weapons.json") as f:
        data = json.load(f)
    weapon_list = []
    for weapon in data[weapon_type]:
        weapon_name = weapon["name"]
        weapon_price = weapon["cost"]
        weapon_damage = weapon["damage"]
        weapon = weapon_name + " (" + weapon_price + ") " + "\n" + weapon_damage
        weapon_list.append(weapon)
    keyboard = []
    for weapon in weapon_list:
        keyboard.append([weapon])
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Choose your weapon:", reply_markup=reply_markup)
    return CHANGES_HANDLER

async def armorMod(update, context):
    """
    Handles the armor choice during character modification.
    """
    with open("5eDefaults/armors.json") as f:
        data = json.load(f)
    userInput = update.message.text
    armor_type = userInput.lower().replace(" ", "_")    
    if armor_type in data: #se l'utente ha scelto un tipo di armatura
        global armor_type_final
        armor_type_final = armor_type
        armor_list = []
        for armor in data[armor_type]:
            armor_name = armor["name"]
            armor_price = armor["cost"]
            armor_class = armor["armor_class"]
            armor_stealth = ""
            if armor.get("stealth") == "disadvantage":
                armor_stealth = "stealth nerf"

            armor = armor_name + " " + "(" + armor_price + ") " + "\n" + armor_class
            if armor_stealth != "":
                armor = armor + " (" + armor_stealth + ")"
            armor_list.append(armor)
        keyboard = []
        for armor in armor_list:
            keyboard.append([armor])
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Choose your armor:", reply_markup=reply_markup)
        return CHANGES_HANDLER

async def backstoriesMod(update, context):
    """
    Handles the background story choice during character modification.
    """
    callback_data = update.callback_query.data
    global tmp_char

    if callback_data == "WRITE":
        message = "Perfect! Write your background story and press 'enter'"
        await context.bot.send_message(chat_id=update.effective_chat.id, text=message)

    elif callback_data == "GENERATE":
        message = "Ok, I will generate a random background story for you"
        await context.bot.send_message(chat_id=update.effective_chat.id, text=message)
        selected_char = tmp_char[update.effective_chat.id]["tmp_character"]["name"]
        with open(dbPath, "r") as f:
            data = json.load(f)
        for user in data["users"]:
            for char in user["characters"]:
                if char["name"] == selected_char:
                    race = char["race"]
                    char_class = char["class"]
                    background = char["background"]
                    break
        with open("5eDefaults/backgorundgenerator.json", "r") as fp:
            backgroundsStories = json.load(fp)
            random_number = random.randint(0, 2)

            #switchcase per identificare l'indice associato alla razza
            if race == "dwarf":
                race_num = 0
            elif race == "elf":
                race_num = 1
            elif race == "halfling":
                race_num = 2
            elif race == "human":
                race_num = 3
            else:
                race_num = 4

            #switchcase per identificare l'indice associato alla classe
            if char_class == "wizard":
                class_num = 0
            else:
                class_num = 1

            #switchcase per identificare l'indice associato al background
            if background == "acolyte":
                back_num = 0
            elif background == "criminal":
                back_num = 1
            elif background == "folk_hero":
                back_num = 2
            elif background == "noble":
                back_num = 3
            elif background == "sage":
                back_num = 4
            else:
                back_num = 5    
    
            races = backgroundsStories["races"]
            theRace = races[race_num][race]
            theClass = theRace[class_num][char_class]
            theBack = theClass[back_num][background]
            message = theBack[random_number]
            await context.bot.send_message(chat_id=update.effective_chat.id, text=message)
            tmp_char[update.effective_chat.id]["tmp_character"]["background story"] = message
            tmp_char[update.effective_chat.id]["tmp_character"]["modified"].append("background story")
            tmp_char[update.effective_chat.id]["tmp_character"]["attributesToModify"].remove("background story")
            await modifyPrompt(update, context)
            return ATTRIBUTE_CHOICE
    elif callback_data == "NONE":
        message = ""

async def modifyPrompt(update, context):
    """ This function is called when the user wants to modify a character. It prompts the user to choose which attribute to modify and save time by not having to retype the same keyboard every time."""
    with open("database/char_sheet.json", "r") as fp:
        attributes = json.load(fp)
    attributes = [*attributes]
    
    keyboard = []
    for attribute in attributes:
        if attribute != "ability_modifiers" and attribute != "current_weight" and attribute != "max_weight" and attribute != "level"and attribute != "features" and attribute != "ability_scores":
            keyboard.append([attribute])
    keyboard.append(["Finished"])
    
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, input_field_placeholder='Which field you want to modify?')
    message = "Do you want to change something else?"
    await context.bot.send_message(chat_id=update.effective_chat.id, text=message, reply_markup=reply_markup)
# ---------------------------------- CAMPAIGN ----------------------------------
async def joinCampaign(update, context):
    """
    This is the first function called when the user wants to join a campaign. It prompts the user to choose between public, private or already joined campaigns.
    """
    message = "Calling all bold adventurers! The realm beckons with both public and private campaigns awaiting your valor. In the public quests, your deeds will be witnessed by all, your name echoing through the taverns and kingdoms alike. Or, should you seek a more intimate journey, private campaigns whisper secrets that require a key to unlock their hidden depths. Choose your destiny wisely, for the path you select shall shape your fate and the tales told of your triumphs. Declare now, will you step into the limelight of a public campaign or venture into the shadows of a private quest?"

    keyboard = [
        ["Public"],
        ["Private"],
        ["My campaigns"]
    ]
    await context.bot.send_message(chat_id=update.effective_chat.id, text=message, reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True))
    return CAMPAIGN_CHOICE

async def publicOrPrivateCampaign(update, context):
    """
    This function is called when the user has to choose between public, private or already joined campaigns, it handles the user choice and prompts the user to choose a campaign or to insert the campaign name and key (for private campaigns)
    """
    choice = update.message.text
    if choice == "My campaigns":
        message = "Here are the campaigns you are currently playing in. Choose one to continue your adventure!"
        with open ("database/campaignsDB.json", "r") as fp:
            data = json.load(fp)
        
        keyboard = []
        for campaign in data:
            for player in campaign["players"]:
                if player["ID"] == update.effective_chat.id:
                    campaign_info = campaign["name"] + " - " + str(len(campaign["players"]))
                    if campaign["ID_Master"] == update.effective_chat.id:
                        campaign_info = campaign_info + "  -  (DM)"
                    keyboard.append([campaign_info])
        
        await context.bot.send_message(chat_id=update.effective_chat.id, text=message, reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True))
        return UPLOAD_MAP
    elif choice == "Public":
        message = "Public campaigns are open to all adventurers. These quests are visible to all and will be listed in the public campaign directory. Choose a campaign from the list below to join the adventure!"
        with open ("database/campaignsDB.json", "r") as fp:
            data = json.load(fp)
        
        keyboard = []
        for campaign in data:
            if campaign["public"] == True:
                player_ids = [player["ID"] for player in campaign["players"]]
                if update.effective_chat.id not in player_ids:
                    campaign_info = campaign["name"] + " - " + str(len(campaign["players"]))
                    keyboard.append([campaign_info])
        
        await context.bot.send_message(chat_id=update.effective_chat.id, text=message, reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True))
        return JOIN_PUBLIC_CAMPAIGN
    elif choice == "Private":
        message = "Private campaigns are only open to those with the secret key. These quests are hidden from the public and will not be listed in the public campaign directory. If you know the name of the campaign and the key, enter it below to join the adventure! Insert the name of the campaign and the key separated by a space."
        await context.bot.send_message(chat_id=update.effective_chat.id, text=message)
        return JOIN_PRIVATE_CAMPAIGN
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Ok, see you later!")
        return ConversationHandler.END

async def joinPublicCampaign(update, context):
    campaignInfo = update.message.text
    campaignName = campaignInfo.split(" - ")[0]
    global new_campaign
    new_campaign = {"name": campaignName}
    with open ("database/campaignsDB.json", "r") as fp:
        data = json.load(fp)
    for campaign in data:
        if campaign["name"] == campaignName:
            player = {"ID": update.effective_chat.id, "ID_char": ""}
            campaign["players"].append(player)
            break
    global current_campaign
    current_campaign = campaign["ID"]
    with open ("database/campaignsDB.json", "w") as fp:
        json.dump(data, fp)

    kb = [["I'm ready!"]]
    await context.bot.send_message(chat_id=update.effective_chat.id, text="You joined the campaign!", reply_markup=ReplyKeyboardMarkup(kb, one_time_keyboard=True))
    return UPLOAD_MAP

async def joinPrivateCampaign(update, context):
    campaignInfo = update.message.text
    campaignName = campaignInfo.split(" ")[0]
    campaignKey = campaignInfo.split(" ")[1]
    global new_campaign
    new_campaign = {"name": campaignName}
    with open ("database/campaignsDB.json", "r") as fp:
        data = json.load(fp)
    for campaign in data:
        if campaign["public"] == False and campaign["name"] == campaignName and campaign["key"] == campaignKey:
            if update.effective_chat.id not in [player["ID"] for player in campaign["players"]]:
                player = {"ID": update.effective_chat.id, "ID_char": {}}
                campaign["players"].append(player)
                global current_campaign
                current_campaign = campaign["ID"]
                break
            else:
                message = "You are already playing in this campaign! Please choose another one."
                keyboard = [
                    ["Public"],
                    ["Private"],
                    ["My campaigns"]
                ]
                await context.bot.send_message(chat_id=update.effective_chat.id, text=message, reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True))
                return CAMPAIGN_CHOICE
    with open ("database/campaignsDB.json", "w") as fp:
        json.dump(data, fp)
    await context.bot.send_message(chat_id=update.effective_chat.id, text="You joined the private campaign named " + campaignName + "!")
    
    return UPLOAD_MAP

async def uploadMap(update, context):
    global master
    chosenCampaign = update.message.text
    global current_campaign
    campaignToCompare = chosenCampaign.split(" - ")[0]
    master = False

    keyboard = [["Upload map"], ["Skip uploading"]]
    with open ("database/campaignsDB.json", "r") as fp:
        data = json.load(fp)
    
    for campaign in data:
        if campaign["name"] == campaignToCompare:
            if str(campaign["ID_Master"]) == str(update.effective_chat.id):
                master = True
                current_campaign = campaign["ID"]
                break
            elif str(update.effective_chat.id) in [str(player["ID"]) for player in campaign["players"]]:
                current_campaign = campaign["ID"]
                break
        if str(campaign["ID"]) == str(current_campaign) and str(campaign["ID_Master"]) == str(update.effective_chat.id):
            master = True
            break

    if master == True:
        try:
            print("Current campaign: " + str(current_campaign))
            with open(f'maps/{current_campaign}.jpg', 'rb') as f:
                #The master already uploaded a map
                keyboard = [
                [InlineKeyboardButton("Start the game", callback_data=str("GAME_START"))]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            message = "Great! Now you can begin to create your story!"
            await context.bot.send_message(chat_id=update.effective_chat.id, text=message, reply_markup = reply_markup)
            return ConversationHandler.END
        except FileNotFoundError:
            message = "Welcome to your campaign Dungeon Master! The adventurers are waiting for you! First of all, please upload the map you have prepared for the campaign"
            await context.bot.send_message(chat_id=update.effective_chat.id, text=message, reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True))
            return END_UPLOADING
    if master == False:
        keyboard = [
            [InlineKeyboardButton("Start the game", callback_data=str("GAME_START"))]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Press this button to start the game", reply_markup = reply_markup)
        return ConversationHandler.END

async def endUploading(update, context):   
    choice = update.message.text
    if choice == "Upload map":
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Ok then upload your map and press enter. The map will be available for every player")
        return FINAL_MAP
        #TODO il bot deve aspettare che il master carichi la mappa e poi proseguire. Come carica la mappa? Informati (x Fede da fede)
    elif choice == "Skip uploading":
        print("skip")

    keyboard = [
        [InlineKeyboardButton("Start the game", callback_data=str("GAME_START"))]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    message = "Great! Now you can begin to create your story!"
    await context.bot.send_message(chat_id=update.effective_chat.id, text=message, reply_markup = reply_markup)
    return ConversationHandler.END

async def effectiveUpload(update, context):
    photo = update.message.photo
    largest_photo = photo[-1]
    fileID = largest_photo.file_id
    photo_file = await context.bot.get_file(largest_photo.file_id)
    
    response = requests.get(photo_file.file_path)
    os.makedirs("maps", exist_ok=True)
    if response.status_code == 200:
        with open(f'maps/{current_campaign}.jpg', 'wb') as f:
            f.write(response.content)
            print('File downloaded successfully.')
    else:
        print('Failed to download the file.')

    #with open(f'maps/{current_campaign}.jpg', 'rb') as f:
    #    await context.bot.send_photo(chat_id=update.effective_chat.id, photo=InputFile(f), caption=f"Here's your saved map for campaign n*{current_campaign}")
    keyboard = [
        [InlineKeyboardButton("Start the game", callback_data=str("GAME_START"))]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    message = "Great! Now you can begin to create your story!"
    await context.bot.send_message(chat_id=update.effective_chat.id, text=message, reply_markup = reply_markup)
    return ConversationHandler.END

async def charSelection(update, context):
    global curr_player_name
    """
    This function is called when the user has to choose a character to play with. It handles the user choice and prompts the user to choose a character or to create a new one.
    """
    choice = update.message.text
    if choice == "Select a character":
        with open ("database/newUserDB.json", "r") as fp:
            data = json.load(fp)
        keyboard = []
        for user in data["users"]: 
            if str(update.effective_chat.id) == str(user["telegramID"]):
                for char in user["characters"]:
                    charInfo = str(char["name"]) + " - " + str(char["race"]) + " " + str(char["class"])
                    keyboard.append([charInfo])
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Which character would you like to select?", reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True))
        return CHOOSE_CHARACTER
    elif choice == "Create a new character":
        keyboard = [[InlineKeyboardButton("Go back and forge your character!", callback_data=str("MENU"))]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        message = "You will be teleported to the main menu. Hang on tight!"
        await context.bot.send_message(chat_id=update.effective_chat.id, text=message, reply_markup=reply_markup)
        return CHOOSE_CHARACTER
    else:
        choice = choice.split(" - ")[0]
        curr_player_name = choice
        with open ("database/newUserDB.json", "r") as fp:
            data = json.load(fp)
        for user in data["users"]:
            if str(update.effective_chat.id) == str(user["telegramID"]):
                for char in user["characters"]:
                    if char["name"] == choice:
                        charInfo = char
        global current_campaign
        global masterID
        with open("database/campaignsDB.json", "r") as fp:
            data = json.load(fp)
        for campaign in data:
            if campaign["ID"] == current_campaign:
                masterID = campaign["ID_Master"]
                for player in campaign["players"]:
                    if player["ID"] == update.effective_chat.id:
                        player["ID_char"] = charInfo
                        break
        with open("database/campaignsDB.json", "w") as fp:
            json.dump(data, fp, indent=4)
        kb = []
        kb.append(["CONTINUE"])
        await context.bot.send_message(chat_id=update.effective_chat.id, text="You are now playing as " + choice + "! Please wait for the master to start the campaign.", reply_markup=ReplyKeyboardMarkup(kb, one_time_keyboard=True))

        #This snippet sends a message to the master of the campaign when a new player joins
        #user_chat = await context.bot.get_chat(update.effective_chat.id)
        #user_name = user_chat.first_name
        #await context.bot.send_message(chat_id=masterID, text="A new player named " + user_name + " joined your campaign!")
        return PLAYER_ACTIONS

async def createCampaign(update, context):
    global master
    master = True
    message = "Brave adventurer, seize the quill of destiny! Create a new campaign, where heroes rise, darkness trembles, and realms come alive. Shape a world that sparks wonder and challenges the bold. Let your imagination soar and unleash a tale that will captivate all who dare to join. The stage awaits, storyteller. What will be the name of your campaign?"
    await context.bot.send_message(chat_id=update.effective_chat.id, text=message)
    return CAMPAIGN_NAME

async def campaignName(update, context):
    """
    Handles the campaign name choice during campaign creation. 

    This function also set the global variable new_campaign, which is a temporary dictionary containing all the information about the campaign.
    """
    campaignName = update.message.text
    global new_campaign

    new_campaign = {
        "name": campaignName,
        "ID": "",
        "public": True,
        "key": "",
        "ID_Master": update.effective_chat.id,
        "players": [],
        "events": []
    }

    player = {"ID": update.effective_chat.id, "ID_char": ""}
    new_campaign["players"].append(player)

    message = "The name of your campaign is " + campaignName + ". Do you want it be public or private? Note that private campaigns are only open to those with the secret key. These quests are hidden from the public and will not be listed in the public campaign directory."
    keyboard = [
        ["Public"],
        ["Private"]
        ]
    await context.bot.send_message(chat_id=update.effective_chat.id, text=message, reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True))
    return CAMPAIGN_CHOOSEKEY

async def campaignChooseKey(update, context):
    """
    Handles the campaign key choice during campaign creation.

    This function is responsible for handling the user's choice of whether the campaign should be public or private. Depending on the choice and the current state of the campaign creation process, the function responds accordingly.
    If the user chooses "Public" and the campaign key is empty, the campaign is set to public and a message is sent indicating its status.
    If the user chooses "Private" and the campaign key is empty, the campaign is set to private, and the user is prompted to provide a campaign key. Once the key is provided, the function continues with the campaign creation process, sending messages to guide the user further.
    """
    choice = update.message.text
    global new_campaign
    if choice == "Public" and new_campaign["key"] == "":
        message = "Your campaign is now public. You can find it in the public campaign directory."
        await context.bot.send_message(chat_id=update.effective_chat.id, text=message)
    elif choice == "Private" and new_campaign["key"] == "":
        message = "Your campaign is now private. Please choose a key for your campaign. The key must be at least 3 characters long."
        await context.bot.send_message(chat_id=update.effective_chat.id, text=message)
        new_campaign["public"] = False
        return CAMPAIGN_CHOOSEKEY
    else:
        new_campaign["key"] = choice 
    
    message = "As the master of the campaign, you shall create events for your players to experience. These events will be the foundation of your campaign, the building blocks of your story."
    keyboard = [
        [InlineKeyboardButton("Create event", callback_data=str("CREATE_EVENT"))]
        ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_message(chat_id=update.effective_chat.id, text=message, reply_markup=reply_markup)
    await campaignCreated(update, context)
    return ConversationHandler.END

async def campaignCreated(update, context):
    """
    This function is called when the campaign creation process is over. It saves the campaign in the proper database.
    """
    global new_campaign
    global current_campaign
    id = 0
    try:
        with open("database/campaignsDB.json", "r") as fp:
            campaigns = json.load(fp)
        
        for campaign in campaigns:
            id += 1
    except json.JSONDecodeError:
        # Handle the case when the file is empty (or not in valid JSON format)
        campaigns = []

    new_campaign["ID"] = id
    current_campaign = id
    campaigns.append(new_campaign)
    with open("database/campaignsDB.json", "w") as fp:
        json.dump(campaigns, fp, indent=4)

async def askJournal(update, context):
    # Funzione che viene chiamata quando si decide di scrivere sul giornale della campagna
    message = "What do you want to write on the journal?"
    await context.bot.send_message(chat_id=update.effective_chat.id, text=message)
    return WRITE_JOURNAL 

async def writeJournal(update, context):
    print("writing Journal")
    text = update.message.text
    global current_campaign

    folder = "journals"
    if not os.path.exists(folder):
        os.makedirs(folder)

    filename = os.path.join(folder, f"journal{current_campaign}.txt")


    if os.path.exists(filename):
        with open(filename, "a") as file:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            file.write(f"\n{timestamp}: {text}")
    else:
        with open(filename, "w") as file:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            file.write(f"{timestamp}: {text}")

    
    message = "The journal has been updated!"
    await context.bot.send_message(chat_id=update.effective_chat.id, text=message)
    if master == False:
        kb = [["Back to the menu"]]
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Now you can return back to the main menu", reply_markup=ReplyKeyboardMarkup(kb, one_time_keyboard=True))
        return PLAYER_ACTIONS
    elif master == True:
        keyboard = [
            [InlineKeyboardButton("Back to menu", callback_data=str("GAME_START"))]
            ]   
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Now you can return to the main menu", reply_markup=InlineKeyboardMarkup(keyboard))
        ConversationHandler.END

async def readJournal(update, context):
    # Funzione che viene chiamata quando si decide di leggere il giornale della campagna
    global current_campaign
    folder = "journals"
    filename = os.path.join(folder, f"journal{current_campaign}.txt")
    if os.path.exists(filename):
        with open(filename, "r") as file:
            message = file.read()
    else:
        message = "The journal is empty."
    await context.bot.send_message(chat_id=update.effective_chat.id, text=message)
    if master == False:
        kb = []
        kb.append(["Back to main menu"])
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Now you can go back to the menu", reply_markup = ReplyKeyboardMarkup(kb, one_time_keyboard=True))
        return PLAYER_ACTIONS
    elif master == True:
        keyboard = [
            [InlineKeyboardButton("Back to menu", callback_data=str("GAME_START"))]
            ]   
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Now you can return to the main menu", reply_markup=InlineKeyboardMarkup(keyboard))
        ConversationHandler.END
    #return ConversationHandler.END

# ---------------------------------- CREATE EVENTS ----------------------------------

async def createEvent(update, context):
    global encounterArray
    encounterArray = []
    keyboard = [
        [InlineKeyboardButton("Disease", callback_data=str("DISEASE")), InlineKeyboardButton("Custom NPC", callback_data=str("NPC"))],
        [InlineKeyboardButton("Monster", callback_data=str("MONSTER"))]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    message = "You can now create a new encounter in your campaign! Which type of encounter do you want it to be?"
    await context.bot.send_message(chat_id=update.effective_chat.id, text=message, reply_markup=reply_markup)
    return EVENT_CHOICE

async def monsterChoice(update, context):
    global new_monster
    with open("database/monster_sheet.json", "r") as f:
        new_monster = json.load(f)
    keyboard = [
        [InlineKeyboardButton("Custom Monster", callback_data=str("CUSTOM_MONSTER")), InlineKeyboardButton("Fixed Monster", callback_data=str("FIXED_MONSTER"))]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    message = "Do you want to add a fixed monster or create one by yourself?"
    await context.bot.send_message(chat_id=update.effective_chat.id, text=message, reply_markup=reply_markup)
    return MONSTER_CHOICE

async def fixedMonster(update, context):
    keyboard = [
        [("Black Dragon")],
        [("Demon")],
        [("Lich")],
        [("Mimic")],
        [("Goblin")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
    message = "Choose the type of monster you want to add to the events list:"
    await context.bot.send_message(chat_id=update.effective_chat.id, text=message, reply_markup=reply_markup)
    return CHOOSE_MONSTER

async def chooseMonster(update, context):
    with open("5eDefaults/monsters.json", "r") as f2:
        data = json.load(f2)
    userInput = update.message.text
    global monster_type, monster_name
    if userInput == "Black Dragon":
        keyboard = [
            [("Wyrmling")],
            [("Young")],
            [("Adult")],
            [("Ancient")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
        message = "There are different types of black dragons based on their age! Which one do you want to add?"
        await context.bot.send_message(chat_id=update.effective_chat.id, text=message, reply_markup=reply_markup)
        monster_type = "Black Dragon"
        return CHOOSE_MONSTER
    elif userInput == "Demon":
        keyboard = [
            [("Balor")],
            [("Barlgura")],
            [("Glabrezu")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
        message = "You can choose between these three terrible demons. Choose wisely!"
        await context.bot.send_message(chat_id=update.effective_chat.id, text=message, reply_markup=reply_markup)
        monster_type = "Demon"
        return CHOOSE_MONSTER
    elif userInput == "Lich":
        message = "You chose to add a Lich monster to your campaign's encounters!"
        await context.bot.send_message(chat_id=update.effective_chat.id, text=message)
        monster_type = "Lich"
        monster_name = "Lich"
        new_monster = data["Monsters"]["Lich"]
    elif userInput == "Mimic":
        message = "You chose to add a Mimic monster to your campaign's encounters!"
        await context.bot.send_message(chat_id=update.effective_chat.id, text=message)
        monster_type = "Mimic"
        monster_name = "Mimic"
        new_monster = data["Monsters"]["Mimic"]
    elif userInput == "Goblin":
        keyboard = [
            [("Standard Goblin")],
            [("Goblin Boss")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
        message = "Do you want it to be just a normal goblin or a terrible boss?"
        await context.bot.send_message(chat_id=update.effective_chat.id, text=message, reply_markup=reply_markup)
        monster_type = "Goblin"
        return CHOOSE_MONSTER
    elif userInput == "Wyrmling":
        message = "You chose to add a Wyrmling black dragon to your events!"
        await context.bot.send_message(chat_id=update.effective_chat.id, text=message)
        monster_name = "Wyrmling"
        new_monster = data["Monsters"][monster_type][monster_name]
    elif userInput == "Young":
        message = "You chose to add a Young black dragon to your events!"
        await context.bot.send_message(chat_id=update.effective_chat.id, text=message)
        monster_name = "Young"
        new_monster = data["Monsters"][monster_type][monster_name]
    elif userInput == "Adult":
        message = "You chose to add a Adult black dragon to your events!"
        await context.bot.send_message(chat_id=update.effective_chat.id, text=message)
        monster_name = "Adult"
        new_monster = data["Monsters"][monster_type][monster_name]
    elif userInput == "Ancient":
        message = "You chose to add a Ancient black dragon to your events!"
        await context.bot.send_message(chat_id=update.effective_chat.id, text=message)
        monster_name = "Ancient"
        new_monster = data["Monsters"][monster_type][monster_name]
    elif userInput == "Balor":
        message = "You chose to add the Balor demon to your events!"
        await context.bot.send_message(chat_id=update.effective_chat.id, text=message)
        monster_name = "Balor"
        new_monster = data["Monsters"][monster_type][monster_name]
    elif userInput == "Barlgura":
        message = "You chose to add the Barlgura demon to your events!"
        await context.bot.send_message(chat_id=update.effective_chat.id, text=message)
        monster_name = "Barlgura"
        new_monster = data["Monsters"][monster_type][monster_name]
    elif userInput == "Glabrezu":
        message = "You chose to add the Glabrezu demon to your events!"
        await context.bot.send_message(chat_id=update.effective_chat.id, text=message)
        monster_name = "Glabrezu"
        new_monster = data["Monsters"][monster_type][monster_name]
    elif userInput == "Standard Goblin":
        message = "You chose to add a Standard goblin to your events!"
        await context.bot.send_message(chat_id=update.effective_chat.id, text=message)
        monster_name = "Standard Goblin"
        new_monster = data["Monsters"][monster_type][monster_name]
    elif userInput == "Goblin Boss":
        message = "You chose to add a Goblin Boss to your events!"
        await context.bot.send_message(chat_id=update.effective_chat.id, text=message)
        monster_name = "Goblin Boss"
        new_monster = data["Monsters"][monster_type][monster_name]
    else:
        keyboard = [
            [InlineKeyboardButton("Back", callback_data=str("FIXED_MONSTER"))]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        message = "You need to choose a monster from the list given! Please try again!"
        await context.bot.send_message(chat_id=update.effective_chat.id, text=message, reply_markup=reply_markup)
        return MONSTER_CHOICE
    monster = new_monster
    await currentEncounter(update, context, monster)
    keyboard = [
        [InlineKeyboardButton("Add monster", callback_data=str("ADD_MONSTER")), InlineKeyboardButton("Save event", callback_data=str("SAVE_EVENT"))]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    message = "Do you want to add another monster to the current event or do you want to save it as it is?"
    await context.bot.send_message(chat_id=update.effective_chat.id, text=message, reply_markup=reply_markup)
    return GROUP_ENCOUNTER

async def customMonster(update, context):
    message = "You chose to create a custom monster, so you can set all his abilities and values as you like. But first, what's going to be the monster's name?"
    await context.bot.send_message(chat_id=update.effective_chat.id, text=message)
    return MONSTER_NAME

async def monsterName(update, context):
    new_monster["Name"] = update.message.text
    message = "Your monster is going to be named " + new_monster["Name"] + ". Now let's set his armor, what value do you want it to be?"
    await context.bot.send_message(chat_id=update.effective_chat.id, text=message)
    return MONSTER_ARMOR

async def monsterArmor(update, context):
    armor_points = update.message.text
    if armor_points.isdigit():
        new_monster["Armor Class"] = armor_points
        message = "Your monster now has " + armor_points + " armor points. How many hit points do you want it to have?"
        await context.bot.send_message(chat_id=update.effective_chat.id, text=message)
        return MONSTER_HIT
    else:
        message = "The value you chose is not valid, you must choose a number!"
        await context.bot.send_message(chat_id=update.effective_chat.id, text=message)
        return MONSTER_ARMOR
    
async def monsterHit(update, context):
    hit_points = update.message.text
    if hit_points.isdigit():
        new_monster["Hit Points"] = hit_points
        message = "Your monster now has " + hit_points + " hit points. Now choose the amount of XP you want the challenge to give."
        await context.bot.send_message(chat_id=update.effective_chat.id, text=message)
        return MONSTER_XP
    else:
        message = "The value you chose is not valid, you must choose a number!"
        await context.bot.send_message(chat_id=update.effective_chat.id, text=message)
        return MONSTER_HIT

async def monsterXP(update, context):
    xp_points = update.message.text
    if xp_points.isdigit():
        new_monster["Challenge"] = xp_points
        message = "Beating this monster now gives you " + xp_points + " XP. Now choose the speed of your monster."
        await context.bot.send_message(chat_id=update.effective_chat.id, text=message)
        return MONSTER_SPEED
    else:
        message = "The value you chose is not valid, you must choose a number!"
        await context.bot.send_message(chat_id=update.effective_chat.id, text=message)
        return MONSTER_XP
    
async def monsterSpeed(update, context):
    speed_value = update.message.text
    if speed_value.isdigit():
        new_monster["Speed"] = speed_value
        message = "Your set your monster's speed at " + speed_value + ". Now it's time for your monster's ability points! Let's start from the strength, what value do you want it to be?"
        await context.bot.send_message(chat_id=update.effective_chat.id, text=message)
        return MONSTER_ABILITY
    else:
        message = "The value you chose is not valid, you must choose a number!"
        await context.bot.send_message(chat_id=update.effective_chat.id, text=message)
        return MONSTER_SPEED
    
async def monsterAbility(update, context):
    for abilities in new_monster["Ability Scores"]:
        if new_monster["Ability Scores"][abilities] == 0:
            current_ability = abilities
            break
    ability_value = update.message.text
    if ability_value.isdigit():
        new_monster["Ability Scores"][current_ability] = int(ability_value)
    else:
        message = "The value you chose is not valid, you must choose a number!"
        await context.bot.send_message(chat_id=update.effective_chat.id, text=message)
        return MONSTER_ABILITY
    for abilities in new_monster["Ability Scores"]:
        if new_monster["Ability Scores"][abilities] == 0:
            message = "You now have to choose the value for the " + abilities + " ability. Choose wisely!"
            await context.bot.send_message(chat_id=update.effective_chat.id, text=message)
            return MONSTER_ABILITY
    message = "You finished setting up the monster's ability scores. Now it's the saving throws's turn. Let's start from the strength one, how much do you want it to be?"
    await context.bot.send_message(chat_id=update.effective_chat.id, text=message)
    return MONSTER_SAVING_THROWS
                
async def monsterSavingThrows(update, context):
    for savings in new_monster["Saving Throws"]:
        if new_monster["Saving Throws"][savings] == "":
            current_saving = savings
            break
    saving_value = update.message.text
    pattern = r'^[+-]\d+$'
    if re.match(pattern, saving_value) != None:
        new_monster["Saving Throws"][current_saving] = saving_value
    else:
        message = "The string you just inserted is not valid, it must be in the form + or - a number!"
        await context.bot.send_message(chat_id=update.effective_chat.id, text=message)
        return MONSTER_SAVING_THROWS
    for savings in new_monster["Saving Throws"]:
        if new_monster["Saving Throws"][savings] == "":
            message = "You now have to choose the value for the " + savings + " ability. Choose wisely!"
            await context.bot.send_message(chat_id=update.effective_chat.id, text=message)
            return MONSTER_SAVING_THROWS
    message = "You are now over with all this ability stuff! It's time to choose if you want your monster to have a legendary resistance, a powerful ability that allows him to choose to succeed in a failing throw three times a day."
    keyboard = [
            [("True")],
            [("False")]
        ]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
    await context.bot.send_message(chat_id=update.effective_chat.id, text=message, reply_markup=reply_markup)
    return LEGENDARY_RESISTANCE

async def legendaryResistance(update, context):
    legendary_choice = update.message.text
    if legendary_choice == "True":
        new_monster["Legendary Resistance"] = "If " + new_monster["Name"] + "  fails a saving throw, it can choose to succeed instead"
    elif legendary_choice == "False":
        new_monster["Legendary Resistance"] = ""
    else:
        message = "You must choose an answer from the keyboard to go on with the monster's creation."
        keyboard = [
            [("True")],
            [("False")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
        await context.bot.send_message(chat_id=update.effective_chat.id, text=message, reply_markup=reply_markup)
        return LEGENDARY_RESISTANCE
    with open("5eDefaults/monsteractions.json") as f:
        data = json.load(f)
    message = "Now that you did set your monster's legendary resistance is time to talk about the actions it can perform. You can choose one from the following list with some of the most common ones, or you can just type in one by yourself"
    keyboard = []
    for actions in data["actions"]:
        keyboard.append([actions])
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)    
    await context.bot.send_message(chat_id=update.effective_chat.id, text=message, reply_markup=reply_markup)
    return MONSTER_ACTIONS

async def monsterActions(update, context):
    with open("5eDefaults/monsteractions.json") as f:
            data = json.load(f)
    monster_action = update.message.text
    if monster_action == "Done" or monster_action == "done":
        message = "We are almost over with the creation of your monster, there are only a few questions you still have to answer. There is a particular type of actions called 'Legendary actions' that a monster can perform at any time. Do you want to add some of them to your monster?"
        keyboard = [["Done"]]
        for actions in data["actions"]:
            keyboard.append([actions])
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True) 
        await context.bot.send_message(chat_id=update.effective_chat.id, text=message, reply_markup = reply_markup)
        return LEGENDARY_ACTIONS
    else:
        new_monster["Actions"].append(monster_action)
        message = "You successfully added " + monster_action + " to your monster's actions. If you want to add more actions just select a new one or press done if you want to skip to the next part"
        keyboard = [["Done"]]
        for actions in data["actions"]:
            keyboard.append([actions])
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True) 
        await context.bot.send_message(chat_id=update.effective_chat.id, text=message, reply_markup=reply_markup)
        return MONSTER_ACTIONS

async def monsterLegActions(update, context):
    monster_leg_action = update.message.text
    if monster_leg_action == "Done" or monster_leg_action == "done":
        with open("5eDefaults/monsterskills.json") as f:
            data = json.load(f)
        message = "Now that we are over with all those actions let's talk about skills. Which skill does your monster have? If you don't want to add any skills, just press 'Done'"
        keyboard = [["Done"]]
        for skills in data["skills"]:
            keyboard.append([skills])
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
        await context.bot.send_message(chat_id=update.effective_chat.id, text=message, reply_markup = reply_markup)
        return MONSTER_SKILL
    else:
        with open("5eDefaults/monsteractions.json") as f:
            data = json.load(f)
        new_monster["Legendary Actions"].append(monster_leg_action)
        message = "You added " + monster_leg_action + " to your monster actions. Do you want to add another one?"
        keyboard = [["Done"]]
        for actions in data["actions"]:
            keyboard.append([actions])
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
        await context.bot.send_message(chat_id=update.effective_chat.id, text=message, reply_markup=reply_markup)
        return LEGENDARY_ACTIONS

async def monsterSkill(update, context):
    global temp_skill
    temp_skill = update.message.text
    if temp_skill == "Done" or temp_skill == "done":
        message = "Only 2 fields to fill, keep going! It's time for the damage immunities, does your monster have any?"
        with open("5eDefaults/monsterimmunities.json") as f:
            data = json.load(f)
        keyboard = [["Done"]]
        for immunities in data["immunities"]:
            keyboard.append([immunities])
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
        await context.bot.send_message(chat_id=update.effective_chat.id, text=message, reply_markup=reply_markup)
        return MONSTER_IMMUNITIES
    else:
        message = "You chose " + temp_skill + " as a skill to add. What value do you want it to have?"
        await context.bot.send_message(chat_id=update.effective_chat.id, text=message)
        return MONSTER_SKILL_VALUE

async def monsterSkillValue(update, context):
    skill_val = update.message.text
    if skill_val.isdigit():
        final_skill = temp_skill + " +" + skill_val
        new_monster["Skills"].append(final_skill)
        message = "Successfully added " + final_skill + " to your monster skills. Do you want to add more?"
        with open("5eDefaults/monsterskills.json") as f:
            data = json.load(f)
        keyboard = [["Done"]]
        for skills in data["skills"]:
            keyboard.append([skills])
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
        await context.bot.send_message(chat_id=update.effective_chat.id, text=message, reply_markup = reply_markup)
        return MONSTER_SKILL
    else:
        message = "You must insert a numeric value, please try again."
        await context.bot.send_message(chat_id=update.effective_chat.id, text=message)
        return MONSTER_SKILL_VALUE

async def monsterImmunities(update, context):
    immunity = update.message.text
    if immunity == "Done" or immunity == "done":
        message = "Only last field missing! Choose your monster's resistances and than you are over with the creation!"
        with open("5eDefaults/monsterresistances.json") as f:
            data = json.load(f)
        keyboard = [["Done"]]
        for resistance in data["resistances"]:
            keyboard.append([resistance])
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
        await context.bot.send_message(chat_id=update.effective_chat.id, text=message, reply_markup = reply_markup)
        return MONSTER_RESISTANCES
    else:
        new_monster["Immunities"].append(immunity)
        message = "You added " + immunity + " as one of your monster's immunities. If you want to add more select a new one."
        with open("5eDefaults/monsterimmunities.json") as f:
            data = json.load(f)
        keyboard = [["Done"]]
        for immunities in data["immunities"]:
            keyboard.append([immunities])
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
        await context.bot.send_message(chat_id=update.effective_chat.id, text=message, reply_markup=reply_markup)
        return MONSTER_IMMUNITIES

async def monsterResistances(update, context):
    resistance = update.message.text
    if resistance == "Done" or resistance == "done":
        message = "Congratulations, you are over with your monster's creation!"
        await context.bot.send_message(chat_id=update.effective_chat.id, text=message)
        monster = new_monster
        await currentEncounter(update, context, monster)
        keyboard = [
            [InlineKeyboardButton("Add monster", callback_data=str("ADD_MONSTER")), InlineKeyboardButton("Save event", callback_data=str("SAVE_EVENT"))]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        message = "Do you want to add another monster to the current event or do you want to save it as it is?"
        await context.bot.send_message(chat_id=update.effective_chat.id, text=message, reply_markup=reply_markup)
        return GROUP_ENCOUNTER
    else:
        new_monster["Resistances"].append(resistance)
        message = "Successfully added " + resistance + " to your monster's resistances. Do you want to add more?"
        with open("5eDefaults/monsterresistances.json") as f:
            data = json.load(f)
        keyboard = [["Done"]]
        for resistance in data["resistances"]:
            keyboard.append([resistance])
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
        await context.bot.send_message(chat_id=update.effective_chat.id, text=message, reply_markup = reply_markup)
        return MONSTER_RESISTANCES

async def currentEncounter(update, context, monster):
    encounterArray.append(monster)
    return

async def saveMonster(update, context):
    with open("database/campaignsDB.json", "r") as f:
        data = json.load(f)
    for campaigns in data:
        if current_campaign == campaigns["ID"]:
            if "events" not in campaigns:
                campaigns["events"] = []
            campaigns["events"].append(encounterArray)
            break
    with open("database/campaignsDB.json", "w") as f:
        json.dump(data, f, indent=4)
    keyboard = [
        [InlineKeyboardButton("Create event", callback_data=str("CREATE_EVENT"))],
        [InlineKeyboardButton("Start the game", callback_data=str("GAME_START"))]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    message = "Do you want to start the game or keep creating events?"
    await context.bot.send_message(chat_id=update.effective_chat.id, text=message, reply_markup=reply_markup)
    return ConversationHandler.END

async def diseaseChoice(update, context):
    message = "You chose to create an event where the adventurers have to face a terrible disease. Choose one from the following list and it will be added directly to your events list."
    with open("5eDefaults/diseases.json") as f:
            data = json.load(f)
    keyboard = []
    for disease in data["Diseases"]:
        keyboard.append([disease])
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
    await context.bot.send_message(chat_id=update.effective_chat.id, text=message, reply_markup = reply_markup)
    return SAVE_DISEASE
    
async def saveDisease(update, context):
    disease_name = update.message.text
    with open("5eDefaults/diseases.json") as f:
            data = json.load(f)
    disease = data["Diseases"][disease_name]
    with open("database/campaignsDB.json", "r") as f:
        data = json.load(f)
    for campaigns in data:
        if current_campaign == campaigns["ID"]:
            if "events" not in campaigns:
                campaigns["events"] = []
            campaigns["events"].append(disease)
            break
    with open("database/campaignsDB.json", "w") as f:
        json.dump(data, f, indent=4)
    keyboard = [
        [InlineKeyboardButton("Create event", callback_data=str("CREATE_EVENT"))],
        [InlineKeyboardButton("Start the game", callback_data=str("GAME_START"))]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    message = "The " + disease_name + " disease has been successfully added to your campaign. Do you want to start the game or keep creating events?"
    await context.bot.send_message(chat_id=update.effective_chat.id, text=message, reply_markup=reply_markup)
    return ConversationHandler.END

async def NPCChoice(update, context):
    global new_NPC
    with open("database/NPC_sheet.json", "r") as f:
        new_NPC = json.load(f)
    new_NPC["current_weight"] = 0
    message = "You decided to create an NPC. Let's start from the beginning, what's the NPC name?"
    await context.bot.send_message(chat_id=update.effective_chat.id, text=message)
    return NPC_NAME

async def NPCName(update, context):
    NPC_name = update.message.text
    new_NPC["name"] = NPC_name
    with open("5eDefaults/races.json", "r") as fp:
        races = json.load(fp)
    races = [*races]

    reply_keyboard = []
    for race in races:
        reply_keyboard.append([race])

    reply_keyboard.append([emoji.emojize("Info races \U00002139")])

    race_kb=ReplyKeyboardMarkup(
        reply_keyboard, one_time_keyboard=True, input_field_placeholder='Choose the race'
    )
    message = "Your NPC is now called " + NPC_name + ". Now we have to choose his race, pick one from the following list."
    await context.bot.send_message(chat_id=update.effective_chat.id, text=message, reply_markup=race_kb)
    return NPC_RACE

async def NPCRace(update, context):
    race = update.message.text
    with open("5eDefaults/races.json", "r") as fp:
        races = json.load(fp)

    # Print to the user information about races
    if race == "Info races ℹ️":
        reply_keyboard = []

        race_kb=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=True, input_field_placeholder='Choose the race'
        )

        for description in races["dwarf"]["race_description"]["subraces"]:
            message = description["description"]
        await context.bot.send_message(chat_id=update.effective_chat.id, text=message, reply_markup=race_kb)

        for description in races["elf"]["race_description"]["subraces"]:
            message = description["description"]
            await context.bot.send_message(chat_id=update.effective_chat.id, text=message, reply_markup=race_kb)

        for description in races["halfling"]["race_description"]["subraces"]:
            message = description["description"]
        await context.bot.send_message(chat_id=update.effective_chat.id, text=message, reply_markup=race_kb)

        for description in races["human"]["race_description"]["subraces"]:
            message = description["description"]
        await context.bot.send_message(chat_id=update.effective_chat.id, text=message, reply_markup=race_kb)
        
        return NPC_RACE

    new_NPC["race"] = race

    if "subraces_choice" in races[race]:
        reply_keyboard = []
        for subrace in races[race]["subraces_choice"]["options"]:
            reply_keyboard.append([subrace["display_name"]])
    else:
        with open("5eDefaults/classes.json", "r") as fp:
            classes = json.load(fp)
        classes = [*classes]

        reply_keyboard = []
        for className in classes:
            reply_keyboard.append([className])


        class_kb=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=True, input_field_placeholder='Choose the class'
        )
        message="Your NPC is going to be a " + race + " i guess! What does he do for a living?"
        await context.bot.send_message(chat_id=update.effective_chat.id, text=message, reply_markup=class_kb)
        return NPC_CLASS

    subrace_kb=ReplyKeyboardMarkup(
        reply_keyboard, one_time_keyboard=True, input_field_placeholder='Choose the subrace'
    )
    message="Your NPC is going to be a " + race + " i guess! Does he also have a particolar subrace?"
    await context.bot.send_message(chat_id=update.effective_chat.id, text=message, reply_markup=subrace_kb)
    return NPC_SUBRACE

async def NPCSubrace(update, context):
    NPC_subrace = update.message.text
    new_NPC["subrace"] = NPC_subrace


    with open("5eDefaults/classes.json", "r") as fp:
        classes = json.load(fp)
    classes = [*classes]

    reply_keyboard = []
    for className in classes:
        reply_keyboard.append([className])


    class_kb=ReplyKeyboardMarkup(
        reply_keyboard, one_time_keyboard=True, input_field_placeholder='Choose the class'
    )
    message="Your NPC is now part of the " + NPC_subrace + " subrace! What does he do for a living?"
    await context.bot.send_message(chat_id=update.effective_chat.id, text=message, reply_markup=class_kb)
    return NPC_CLASS

async def NPCClass(update, context):
    NPC_class = update.message.text
    new_NPC["class"] = NPC_class

    with open("5eDefaults/backgrounds.json", "r") as fp:
        backgrounds = json.load(fp)
    backgrounds = [*backgrounds]

    reply_keyboard = []
    for background in backgrounds:
        reply_keyboard.append([background])

    subrace_kb=ReplyKeyboardMarkup(
        reply_keyboard, one_time_keyboard=True, input_field_placeholder='Choose the background'
    )
    message="Ah, a " + NPC_class + ", a wise choice indeed! Now, what about your background? Have you had any interesting experiences in your past that shaped who you are today?"
    await context.bot.send_message(chat_id=update.effective_chat.id, text=message, reply_markup=subrace_kb)
    return NPC_BACKGROUND

async def NPCBackground(update, context):
    background = update.message.text
    new_NPC["background"] = background
    keyboard = [
        [
            InlineKeyboardButton("Randomly genereted value", callback_data=str("NPC_RANDOM")),
            InlineKeyboardButton("Fixed value array", callback_data=str("NPC_FIXED"))
        ],
        [
            InlineKeyboardButton("Full auto", callback_data=str("NPC_AUTO")),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    message="Interesting, your NPC has a " + background + " past! But let's go on now, we have to start setting up the ability scores. How do you want this to happend?"
    await context.bot.send_message(chat_id=update.effective_chat.id, text=message, reply_markup=reply_markup)
    return NPC_ABILITY_SCORES

async def NPCAbilityScores(update, context):

    abilities_to_set = all(value == 0 for value in new_NPC["ability_scores"].values())

    if abilities_to_set == True: 
        callback_data = update.callback_query.data
        #First iteraction, calculate the scores
        ability_scores = []
        message = ""
        if callback_data == "NPC_AUTO":
            #Full auto mode allows the user to skip the whole process and get a character with random stats
            new_NPC["ability_scores"] = {}
            for i in range(6):
                rolls = [random.randint(1, 6) for j in range(4)]
                rolls.remove(min(rolls))
                score = sum(rolls)
                ability_scores.append(score)
            with open('5eDefaults/sheetData.json') as f:
                data = json.load(f)
            abilities = [stat['display_name'] for stat in data['stats'].values()]
            for ability in abilities:
                new_NPC["ability_scores"][ability] = ability_scores.pop()
            message = "Your NPC's ability scores are: "
            for ability, score in new_NPC["ability_scores"].items():
                message += "\n" + ability + ": " + str(score)
            await context.bot.send_message(chat_id=update.effective_chat.id, text=message)
            await setNPCModifiers(update, context)


            keyboard = [
                [("Light Armor")],
                [("Medium Armor")],
                [("Heavy Armor")]
            ]
            reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
            await context.bot.send_message(chat_id=update.effective_chat.id, text="Now, let's choose your armor!", reply_markup=reply_markup)
            return NPC_ARMOR
        elif callback_data == "NPC_RANDOM":
            message = "To generate your NPC's six ability scores randomly, our bot will roll four 6-sided dice and record the total of the highest three dice for you. This process will be repeated five more times, so that you have six numbers in total. These six numbers will be your character's ability scores: "
            # Roll 4d6 and keep the highest 3 rolls for each ability score
            for i in range(6):
                rolls = [random.randint(1, 6) for j in range(4)]
                rolls.remove(min(rolls))
                score = sum(rolls)
                ability_scores.append(score)
        elif callback_data == "NPC_FIXED":
            message = "To generate your NPC's six ability scores using a fixed array, our bot will use the following numbers: "
            ability_scores = [15, 14, 13, 12, 10, 8]
            
        # Salva i punteggi nella conversazione
        new_NPC["ability_scores"] = {
            "points": ability_scores,
        }
        # Estrae i nomi delle abilità e li salva nello stato della conversazione
        with open('5eDefaults/sheetData.json') as f:
            data = json.load(f)
        abilities = [stat['display_name'] for stat in data['stats'].values()]
        new_NPC["ability_scores"]["remaining"] = abilities

        message += str(ability_scores[0]) + ", " + str(ability_scores[1]) + ", " + str(ability_scores[2]) + ", " + str(ability_scores[3]) + ", " + str(ability_scores[4]) + ", " + str(ability_scores[5]) + "." + "Please assign these scores to your character's ability scores as you see fit."
        await context.bot.send_message(chat_id=update.effective_chat.id, text=message)

    remaining_abilities = new_NPC["ability_scores"]["remaining"]

    remaining_scores = new_NPC["ability_scores"]["points"]

    if(len(remaining_abilities) == 0):
        #rimuovi variabili ausiliarie
        del new_NPC["ability_scores"]["remaining"]
        del new_NPC["ability_scores"]["points"]  
        # Calcola valori aggiuntivi
        await setNPCModifiers(update, context)
        await setNPCRacialBonuses(update, context)
        # Stampa i punteggi delle abilità assegnati dall'utente
        message = "Your NPC's ability scores are: "
        for ability, score in new_NPC["ability_scores"].items():
            message += "\n" + ability + ": " + str(score)
        await context.bot.send_message(chat_id=update.effective_chat.id, text=message)
    else: 
        ability = remaining_abilities[0]
        keyboard = [    
            [str(score) for score in remaining_scores]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
        message = "What score would you like to assign to your " + ability + " ability?"
        await context.bot.send_message(chat_id=update.effective_chat.id, text=message, reply_markup=reply_markup)
        return NPC_SCORES
    
    keyboard = [
        [("Light Armor")],
        [("Medium Armor")],
        [("Heavy Armor")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
    message = "Choose your armor class:"
    await context.bot.send_message(chat_id=update.effective_chat.id, text=message, reply_markup=reply_markup)
    return NPC_ARMOR

async def saveNPCScores(update, context):
    global tmp_char
    ability = new_NPC["ability_scores"]["remaining"][0]
    score = update.message.text
    new_NPC["ability_scores"][ability] = score
    new_NPC["ability_scores"]["remaining"].remove(ability)
    new_NPC["ability_scores"]["points"].remove(int(score))
    next_state = await NPCAbilityScores(update, context)
    return next_state

async def setNPCModifiers(update, context):
    if "ability_modifiers" not in new_NPC:
        new_NPC["ability_modifiers"] = {}
    for ability in new_NPC["ability_scores"]:
        score = new_NPC["ability_scores"][ability]
        modifier = math.floor((int(score) - 10) / 2)
        new_NPC["ability_modifiers"][ability] = modifier

async def setNPCRacialBonuses(update, context):
    with open('5eDefaults/races.json') as f:
        data = json.load(f)

    race = new_NPC["race"]
    subrace = new_NPC["subrace"]
    race_modifier = data.get(race).get("default").get("ability_score_modifiers")
    subrace_modifier = None
    if subrace is not None:
        subraces_choice = data.get(race).get("subraces_choice")
        if subraces_choice:
            for option in subraces_choice["options"]:
                if option["display_name"] == subrace:
                    subrace_modifier = option.get("ability_score_modifiers")

    for ability in new_NPC["ability_scores"]:
        for ability_rm, modifier_rm in race_modifier.items():
            if ability.lower() == ability_rm.lower():
                ability_score = int(new_NPC["ability_scores"][ability])
                new_NPC["ability_scores"][ability] = ability_score + modifier_rm
        if subrace_modifier is not None:
            for ability_sm, modifier_sm in subrace_modifier.items():
                if ability.lower() == ability_sm.lower():
                    ability_score = int(new_NPC["ability_scores"][ability])
                    new_NPC["ability_scores"][ability] = ability_score + modifier_sm

async def NPCArmor(update, context):
    with open("5eDefaults/armors.json") as f:
        data = json.load(f)
    await setNPCMaxWeight(update, context)
    userInput = update.message.text
    armor_type = userInput.lower().replace(" ", "_")    
    if armor_type in data: #se l'utente ha scelto un tipo di armatura
        global NPC_armor_type_final
        NPC_armor_type_final = armor_type
        armor_list = []
        for armor in data[armor_type]:
            armor_name = armor["name"]
            armor_price = armor["cost"]
            armor_class = armor["armor_class"]
            armor_stealth = ""
            if armor.get("stealth") == "disadvantage":
                armor_stealth = "stealth nerf"

            armor = armor_name + " " + "(" + armor_price + ") " + "\n" + armor_class
            if armor_stealth != "":
                armor = armor + " (" + armor_stealth + ")"
            armor_list.append(armor)
        keyboard = []
        for armor in armor_list:
            keyboard.append([armor])
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Choose your armor:", reply_markup=reply_markup)
        return NPC_ARMOR
    else: #se è la seconda iterazione (riutilizzo lo stesso stato per comodità)
        armor = userInput.split("(")[0]
        for armors in data[NPC_armor_type_final]:
            if armors["name"] + " " == armor:
                armor_weight = armors["weight"]
        new_NPC["armor"] = armor
        await updateNPCWeight(update, context, armor_weight)
        #TODO: aggiungere armor class e stealth nerf alle stats del personaggio anche in base alle proficiencies
        await context.bot.send_message(chat_id=update.effective_chat.id, text="You chose " + armor + " armor for your NPC") #TODO: sistemare mess di interazione con l'utente
        
    with open("5eDefaults/weapons.json") as f:
        data = json.load(f)
    weapon_types = []
    for weapon_type in data:
        weapon_type = weapon_type.replace("_", " ").capitalize()
        # TODO: Aggiungi le emoji corrispondenti alle categorie delle armi - non funziona
        if weapon_type == "Simple melee":
            weapon_type = "\U0001F5E1" + " " + weapon_type
        elif weapon_type == "Simple ranged":
            weapon_type = "\U0001F3F9" + " " + weapon_type
        elif weapon_type == "Martial melee":
            weapon_type = "\U00002694" + " " + weapon_type
        elif weapon_type == "Martial ranged":
            weapon_type = "\U0001F3AF" + " " + weapon_type
        weapon_types.append([weapon_type])

    await context.bot.send_message(chat_id=update.effective_chat.id, text="Choose your NPC's weapon type:", reply_markup=ReplyKeyboardMarkup(weapon_types, one_time_keyboard=True))
    return NPC_WEAPON

async def setNPCMaxWeight(update, context):
    new_NPC["max_weight"] = (float(new_NPC["ability_scores"]["Strength"]) + float(new_NPC["ability_modifiers"]["Strength"]))*15
    return

async def updateNPCWeight(update, context, item_weight):
    new_NPC["current_weight"] = float(new_NPC["current_weight"]) + float(item_weight)
    return

async def NPCWeapon(update, context):
    with open("5eDefaults/weapons.json") as f:
        data = json.load(f)

    userInput = update.message.text
    if userInput == "Done":
        #character_data = tmp_char.get(update.effective_chat.id, {}).get('tmp_character', {})  # Ottieni i dati del personaggio dal dizionario principale
        weapons = new_NPC.get('weapons', [])  # Ottieni la lista delle armi, se presente
        weapon_string = ', '.join(weapons)  # Unisci gli elementi della lista in una stringa separata da virgole
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Your NPC's weapons are: " + weapon_string)
        message = "You are now done with your NPC stats and inventory. If you want you can now type in a dialogue that will be printed to the adventurers when they first encounter this NPC"
        await context.bot.send_message(chat_id=update.effective_chat.id, text=message)
        return SAVE_NPC
    else:
        weapon_type = userInput.split(" ")[1] + " " + userInput.split(" ")[2]
        weapon_type = weapon_type.lower().replace(" ", "_") #utile solo per il primo if
    
    if weapon_type in data:
        global NPC_weapon_type_final
        NPC_weapon_type_final = weapon_type
        weapon_list = []
        for weapon in data[weapon_type]:
            weapon_name = weapon["name"]
            weapon_price = weapon["cost"]
            weapon_damage = weapon["damage"]
            weapon = weapon_name + " (" + weapon_price + ") " + "\n" + weapon_damage
            weapon_list.append(weapon)
        keyboard = []
        for weapon in weapon_list:
            keyboard.append([weapon])
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Choose your weapon:", reply_markup=reply_markup)
    else: #se è la seconda iterazione (l'utente ha scelto un'arma)
        weapon = userInput.split("(")[0].strip()
        for weapons in data[NPC_weapon_type_final]:
            if weapons["name"] == weapon:
                weapon_weight = weapons["weight"]
        if(float(new_NPC["current_weight"]) + float(weapon_weight) < float(new_NPC["max_weight"])):
            await updateNPCWeight(update, context, weapon_weight)
            new_NPC.setdefault("weapons", [])  # Verifica se esiste già una lista di armi, altrimenti crea una nuova lista vuota
            new_NPC["weapons"].append(weapon)
            await context.bot.send_message(chat_id=update.effective_chat.id, text="You chose " + weapon + " for your NPC") #TODO: sistemare mess di interazione con l'utente
        else:
            message = "Your NPC can't carry that weapon, that's too heavy for him! Choose a lighter one!"
            await context.bot.send_message(chat_id=update.effective_chat.id, text=message)
        weapon_types = []
        for weapon_type in data:
            weapon_type = weapon_type.replace("_", " ").capitalize()
            # TODO: Aggiungi le emoji corrispondenti alle categorie delle armi - non funziona
            if weapon_type == "Simple melee":
                weapon_type = "\U0001F5E1" + " " + weapon_type
            elif weapon_type == "Simple ranged":
                weapon_type = "\U0001F3F9" + " " + weapon_type
            elif weapon_type == "Martial melee":
                weapon_type = "\U00002694" + " " + weapon_type
            elif weapon_type == "Martial ranged":
                weapon_type = "\U0001F3AF" + " " + weapon_type
            weapon_types.append([weapon_type])
        weapon_types.append(["Done"])
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Choose your NPC's weapon type:", reply_markup=ReplyKeyboardMarkup(weapon_types, one_time_keyboard=True))
    
    return NPC_WEAPON

async def saveNPC(update, context):
    NPC_dialogue = update.message.text
    new_NPC["dialogue"] = NPC_dialogue
    with open("database/campaignsDB.json", "r") as f:
        data = json.load(f)
    for campaigns in data:
        if current_campaign == campaigns["ID"]:
            if "events" not in campaigns:
                campaigns["events"] = []
            campaigns["events"].append(new_NPC)
            break
    with open("database/campaignsDB.json", "w") as f:
        json.dump(data, f, indent=4)
    keyboard = [
        [InlineKeyboardButton("Create event", callback_data=str("CREATE_EVENT"))],
        [InlineKeyboardButton("Start the game", callback_data=str("GAME_START"))]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    message = "Your NPC called " + new_NPC["name"] + " has now been saved in your campaign's events. Do you want to start the game or keep creating events?"
    await context.bot.send_message(chat_id=update.effective_chat.id, text=message, reply_markup=reply_markup)
    return ConversationHandler.END
# ---------------------------------- MODIFY EVENTS ----------------------------------

async def chooseEventPrompt(update, context):
    message = "You chose to modify an event. These are the events currently in your campaign:"
    await context.bot.send_message(chat_id=update.effective_chat.id, text=message)
    with open("database/campaignsDB.json") as f:
        data = json.load(f)
    for campaigns in data:
        if current_campaign == campaigns["ID"]:
            campaign = campaigns
            break
    counter = 1
    kb = []
    for events in campaign["events"]:
        message = str(counter) + " - "
        kb.append([InlineKeyboardButton(counter, callback_data=str("MOD-") + str(counter))])
        if isinstance(events, list):
            for event in events:
                for key, value in event.items():
                    message = message + f"{key}: {value}\n"
                message = message + "\n"
            await context.bot.send_message(chat_id=update.effective_chat.id, text=message)
        else:
            for key, value in events.items():
                message = message + f"{key}: {value}\n"
            await context.bot.send_message(chat_id=update.effective_chat.id, text=message)
        counter += 1
    reply_markup = InlineKeyboardMarkup(kb)
    message = "Please insert the number of the event you want to modify."
    await context.bot.send_message(chat_id=update.effective_chat.id, text=message, reply_markup = reply_markup)

async def eventChoice(update, context):
    global monsterNumber
    monsterNumber = 1
    global eventNumber
    query = update.callback_query
    data = query.data
    eventNumber = data.split("-")[1]
    with open("database/campaignsDB.json") as f:
        data = json.load(f)
    for campaigns in data:
        if current_campaign == campaigns["ID"]:
            campaign = campaigns
            break
    event = campaign["events"][int(eventNumber) - 1]
    keyboard = []
    counter = 1
    if isinstance(event, list):
        if len(campaigns["events"][int(eventNumber) - 1]) > 1:
            for monsters in event:
                message = str(counter) + "- "
                for key, value in monsters.items():
                    message = message + f"{key}: {value}\n"
                await context.bot.send_message(chat_id=update.effective_chat.id, text=message)
                counter += 1
            message = "You chose to modify the event number " + eventNumber + ". This is an event with multiple monsters, choose the one you want to modify."
            await context.bot.send_message(chat_id=update.effective_chat.id, text=message)
            return CHOOSE_MODIFY_MONSTER
        else:
           for attributes in event[0]:
                if attributes != "features" and attributes != "max_weight" and attributes != "current_weight":
                    keyboard.append([attributes])
        keyboard.append(["Finished"])
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, input_field_placeholder='Which field you want to modify?')
        message = "You chose to modify the event number " + eventNumber + ". Now choose the field you want to change."
        await context.bot.send_message(chat_id=update.effective_chat.id, text=message, reply_markup = reply_markup)
        return CHOOSE_ATTRIBUTE 
    for attributes in event:
        if attributes != "features" and attributes != "max_weight" and attributes != "current_weight":
            keyboard.append([attributes])
    keyboard.append(["Finished"])
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, input_field_placeholder='Which field you want to modify?')
    message = "You chose to modify the event number " + eventNumber + ". Now choose the field you want to change."
    await context.bot.send_message(chat_id=update.effective_chat.id, text=message, reply_markup = reply_markup)
    return CHOOSE_ATTRIBUTE

async def chooseModifyMonster(update, context):
    global monsterNumber
    monsterNumber = update.message.text
    with open("database/campaignsDB.json") as f:
        data = json.load(f)
    for campaigns in data:
        if current_campaign == campaigns["ID"]:
            campaign = campaigns
            break
    monster = campaign["events"][int(eventNumber) - 1][int(monsterNumber) - 1]
    keyboard = []
    for attributes in monster:
        if attributes != "features" and attributes != "max_weight" and attributes != "current_weight":
            keyboard.append([attributes])
    keyboard.append(["Finished"])
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, input_field_placeholder='Which field you want to modify?')
    message = "You chose to modify the monster number " + monsterNumber + ". Now choose the field you want to change."
    await context.bot.send_message(chat_id=update.effective_chat.id, text=message, reply_markup = reply_markup)
    return CHOOSE_ATTRIBUTE

async def attributeChoice(update, context):
    with open("database/campaignsDB.json") as f:
        data = json.load(f)
    for campaigns in data:
        if current_campaign == campaigns["ID"]:
            campaign = campaigns
            break
    global event_attribute
    event_attribute = update.message.text
    if event_attribute == "Finished":
        message = "You finished modifying the event, what do you want to do next?."
        keyboard = [
        [InlineKeyboardButton("Create event", callback_data=str("CREATE_EVENT"))],
        [InlineKeyboardButton("Start the game", callback_data=str("GAME_START"))]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await context.bot.send_message(chat_id=update.effective_chat.id, text=message, reply_markup=reply_markup)
        return ConversationHandler.END
    elif event_attribute == "Name":
        message = "You chose to change the name, what do you want it to be?"
        await context.bot.send_message(chat_id=update.effective_chat.id, text=message)
    elif event_attribute == "Race":
        with open("5eDefaults/races.json", "r") as fp:
            races = json.load(fp)
        races = [*races]

        reply_keyboard = []
        for race in races:
            reply_keyboard.append([race])

        race_kb=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=True, input_field_placeholder='Choose the race'
        )
        message = "You chose to change your NPC's race."
        await context.bot.send_message(chat_id=update.effective_chat.id, text=message, reply_markup=race_kb)
    elif event_attribute == "Subrace":
        with open("5eDefaults/races.json", "r") as fp:
            races = json.load(fp)
        race = campaign["events"][int(eventNumber)-1]["Race"]
        if "subraces_choice" in races[race]:
            reply_keyboard = []
            for subrace in races[race]["subraces_choice"]["options"]:
                reply_keyboard.append([subrace["display_name"]])
        subrace_kb=ReplyKeyboardMarkup(
        reply_keyboard, one_time_keyboard=True, input_field_placeholder='Choose the subrace'
        )
        message="Your chose to modify your NPC's subrace."
        await context.bot.send_message(chat_id=update.effective_chat.id, text=message, reply_markup=subrace_kb)
    elif event_attribute == "Class":
        with open("5eDefaults/classes.json", "r") as fp:
            classes = json.load(fp)
        classes = [*classes]

        reply_keyboard = []
        for className in classes:
            reply_keyboard.append([className])


        class_kb=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=True, input_field_placeholder='Choose the class'
        )
        message="You chose to modify your NPC's class"
        await context.bot.send_message(chat_id=update.effective_chat.id, text=message, reply_markup=class_kb)
    elif event_attribute == "Background":
        with open("5eDefaults/backgrounds.json", "r") as fp:
            backgrounds = json.load(fp)
        backgrounds = [*backgrounds]

        reply_keyboard = []
        for background in backgrounds:
            reply_keyboard.append([background])

        subrace_kb=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=True, input_field_placeholder='Choose the background'
        )
        message="You chose to modify your NPC's background."
        await context.bot.send_message(chat_id=update.effective_chat.id, text=message, reply_markup=subrace_kb)
    elif event_attribute == "Ability Scores" or event_attribute == "Ability Modifiers":
        reply_keyboard = [["Strength"],
                          ["Dexterity"],
                          ["Constitution"],
                          ["Intelligence"],
                          ["Wisdom"],
                          ["Charisma"]]

        subrace_kb=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=True, input_field_placeholder='Choose the ability'
        )
        message="You chose to modify the NPC's ability scores."
        await context.bot.send_message(chat_id=update.effective_chat.id, text=message, reply_markup=subrace_kb)
        return ABILITY_CHOICE
    elif event_attribute == "Armor":
        keyboard = [
                [("Light Armor")],
                [("Medium Armor")],
                [("Heavy Armor")]
            ]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
        await context.bot.send_message(chat_id=update.effective_chat.id, text="You chose to modify your NPC's armor. Choose a type.", reply_markup=reply_markup)
        return ARMOR_CHOICE
    elif event_attribute == "Weapons":
        keyboard = [
                [("Add")],
                [("Remove")]
            ]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
        await context.bot.send_message(chat_id=update.effective_chat.id, text="You chose to modify your NPC's weapons. Do you want to add or remove a weapon?.", reply_markup=reply_markup)
        return WEAPON_CHOICE
    elif event_attribute == "Dialogue":
        message = "You chose to modify your NPC's dialogue. Please insert the new dialogue."
        await context.bot.send_message(chat_id=update.effective_chat.id, text=message)
    elif event_attribute == "Targets":
        message = "You chose to modify your disease's targets. Please insert the new ones."
        await context.bot.send_message(chat_id=update.effective_chat.id, text=message)
    elif event_attribute == "Immune":
        message = "You chose to modify your disease's immunities. Please insert the new ones."
        await context.bot.send_message(chat_id=update.effective_chat.id, text=message)
    elif event_attribute == "Symptoms":
        message = "You chose to modify your disease's symptoms. Please insert the new ones."
        await context.bot.send_message(chat_id=update.effective_chat.id, text=message)
    elif event_attribute == "Effects":
        message = "You chose to modify your disease's effects. Please insert the new ones."
        await context.bot.send_message(chat_id=update.effective_chat.id, text=message)
    elif event_attribute == "Infection":
        message = "You chose to modify your disease's infection. Please insert the new one."
        await context.bot.send_message(chat_id=update.effective_chat.id, text=message)
    elif event_attribute == "Cure":
        message = "You chose to modify your disease's cure. Please insert the new one."
        await context.bot.send_message(chat_id=update.effective_chat.id, text=message)
    elif event_attribute == "Armor Class" or event_attribute == "Hit Points" or event_attribute == "Challenge" or event_attribute == "Speed":
        message = "You chose to modify your monster's " + event_attribute.lower() + ". Please insert a new numeric value."
        await context.bot.send_message(chat_id=update.effective_chat.id, text=message)
    elif event_attribute == "Saving Throws":
        reply_keyboard = [["Strength"],
                          ["Dexterity"],
                          ["Constitution"],
                          ["Intelligence"],
                          ["Wisdom"],
                          ["Charisma"]]

        subrace_kb=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=True, input_field_placeholder='Choose the throw'
        )
        message="You chose to modify the monster's saving throws."
        await context.bot.send_message(chat_id=update.effective_chat.id, text=message, reply_markup=subrace_kb)
        return SAVING_CHOICE
    elif event_attribute == "Legendary Resistance":
        message = "You chose to modify the legendary resistance of your monster, please insert the new one."
        await context.bot.send_message(chat_id=update.effective_chat.id, text=message)
    elif event_attribute == "Actions" or event_attribute == "Legendary Actions":
        keyboard = [
                [("Add")],
                [("Remove")]
            ]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
        await context.bot.send_message(chat_id=update.effective_chat.id, text="You chose to modify your monster's " + event_attribute.lower() + ". Do you want to add or remove one?.", reply_markup=reply_markup)
        return ACTIONS_CHOICE
    elif event_attribute == "Skills":
        keyboard = [
                [("Add")],
                [("Remove")]
            ]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
        await context.bot.send_message(chat_id=update.effective_chat.id, text="You chose to modify your monster's skills. Do you want to add or remove one?.", reply_markup=reply_markup)
        return SKILLS_CHOICE
    elif event_attribute == "Immunities":
        keyboard = [
                [("Add")],
                [("Remove")]
            ]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
        await context.bot.send_message(chat_id=update.effective_chat.id, text="You chose to modify your monster's immunities. Do you want to add or remove one?.", reply_markup=reply_markup)
        return IMMUNITIES_CHOICE
    elif event_attribute == "Resistances":
        keyboard = [
                [("Add")],
                [("Remove")]
            ]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
        await context.bot.send_message(chat_id=update.effective_chat.id, text="You chose to modify your monster's resistances. Do you want to add or remove one?.", reply_markup=reply_markup)
        return RESISTANCES_CHOICE
    return SAVE_MODIFY

async def abilityChoice(update, context):
    global modify_ability
    modify_ability = update.message.text
    message = "You chose to modify the " + modify_ability.lower() + " ability. Insert a numeric value."
    await context.bot.send_message(chat_id=update.effective_chat.id, text=message)
    return SAVE_MODIFY

async def armorChoice(update, context):
    with open("5eDefaults/armors.json") as f:
        data = json.load(f)
    userInput = update.message.text
    armor_type = userInput.lower().replace(" ", "_")    
    global NPC_armor_modify
    NPC_armor_modify = armor_type
    armor_list = []
    for armor in data[armor_type]:
        armor_name = armor["name"]
        armor_price = armor["cost"]
        armor_class = armor["armor_class"]
        armor_stealth = ""
        if armor.get("stealth") == "disadvantage":
            armor_stealth = "stealth nerf"

        armor = armor_name + " " + "(" + armor_price + ") " + "\n" + armor_class
        if armor_stealth != "":
            armor = armor + " (" + armor_stealth + ")"
        armor_list.append(armor)
    keyboard = []
    for armor in armor_list:
        keyboard.append([armor])
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Choose your new NPC's armor:", reply_markup=reply_markup)
    return SAVE_MODIFY

async def weaponChoice(update, context):
    global choice
    choice = update.message.text
    if choice == "Remove":
        with open("database/campaignsDB.json") as f:
            data = json.load(f)
        for campaigns in data:
            if current_campaign == campaigns["ID"]:
                campaign = campaigns
                break
        event = campaign["events"][int(eventNumber) - 1]
        keyboard = []
        for weapons in event["Weapons"]:
            keyboard.append(weapons)
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, input_field_placeholder='Which weapon do you want to remove?')
        message = "This is the list of the weapons your NPC currently owns."
        await context.bot.send_message(chat_id=update.effective_chat.id, text=message, reply_markup = reply_markup)
        return SAVE_MODIFY
    elif choice == "Add":
        with open("5eDefaults/weapons.json") as f:
            data = json.load(f)
        weapon_types = []
        for weapon_type in data:
            weapon_type = weapon_type.replace("_", " ").capitalize()
            # TODO: Aggiungi le emoji corrispondenti alle categorie delle armi - non funziona
            if weapon_type == "Simple melee":
                weapon_type = "\U0001F5E1" + " " + weapon_type
            elif weapon_type == "Simple ranged":
                weapon_type = "\U0001F3F9" + " " + weapon_type
            elif weapon_type == "Martial melee":
                weapon_type = "\U00002694" + " " + weapon_type
            elif weapon_type == "Martial ranged":
                weapon_type = "\U0001F3AF" + " " + weapon_type
            weapon_types.append([weapon_type])
            await context.bot.send_message(chat_id=update.effective_chat.id, text="Choose your weapon type:", reply_markup=ReplyKeyboardMarkup(weapon_types, one_time_keyboard=True))
        return WEAPON_CHOICE
    else:
        weapon_type = choice.split(" ")[1] + " " + choice.split(" ")[2]
        weapon_type = weapon_type.lower().replace(" ", "_") 
        if weapon_type in data:
            global NPC_weapon_type_final
            NPC_weapon_type_final = weapon_type
            weapon_list = []
            for weapon in data[weapon_type]:
                weapon_name = weapon["name"]
                weapon_price = weapon["cost"]
                weapon_damage = weapon["damage"]
                weapon = weapon_name + " (" + weapon_price + ") " + "\n" + weapon_damage
                weapon_list.append(weapon)
            keyboard = []
            for weapon in weapon_list:
                keyboard.append([weapon])
            reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
            await context.bot.send_message(chat_id=update.effective_chat.id, text="Choose your new weapon:", reply_markup=reply_markup)
        choice = "Add"
        return SAVE_MODIFY

async def savingChoice(update, context):
    global modify_saving
    modify_saving = update.message.text
    message = "You chose to modify the " + modify_saving.lower() + " saving throws. Now insert the new value in the form + or - a number."
    await context.bot.send_message(chat_id=update.effective_chat.id, text=message)
    return SAVE_MODIFY

async def actionsChoice(update, context):
    global choice
    choice = update.message.text
    if choice == "Remove":
        with open("database/campaignsDB.json") as f:
            data = json.load(f)
        for campaigns in data:
            if current_campaign == campaigns["ID"]:
                campaign = campaigns
                break
        event = campaign["events"][int(eventNumber) - 1]
        keyboard = []
        for actions in event["Actions"]:
            keyboard.append(actions)
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, input_field_placeholder='Which ' + event_attribute.lower() +' do you want to remove?')
        message = "This is the list of the " + event_attribute.lower() + " your monster can currently perform."
        await context.bot.send_message(chat_id=update.effective_chat.id, text=message, reply_markup = reply_markup)
    elif choice == "Add":
        with open("5eDefaults/monsteractions.json") as f:
            data = json.load(f)
        message = "These are the " + event_attribute.lower() + " you can add to your monster. Choose a new one."
        keyboard = []
        for actions in data["actions"]:
            keyboard.append([actions])
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)    
        await context.bot.send_message(chat_id=update.effective_chat.id, text=message, reply_markup=reply_markup)
    return SAVE_MODIFY

async def skillsChoice(update, context):
    if choice == "Remove":
        with open("database/campaignsDB.json") as f:
            data = json.load(f)
        for campaigns in data:
            if current_campaign == campaigns["ID"]:
                campaign = campaigns
                break
        event = campaign["events"][int(eventNumber) - 1]
        keyboard = []
        for skills in event["Skills"]:
            keyboard.append(skills)
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, input_field_placeholder='Which skill do you want to remove?')
        message = "This is the list of the skills your monster can currently perform."
        await context.bot.send_message(chat_id=update.effective_chat.id, text=message, reply_markup = reply_markup)
    elif choice == "Add":
        with open("5eDefaults/monsterskills.json") as f:
            data = json.load(f)
        message = "These are the skills you can add to your monster. Choose a new one."
        keyboard = []
        for skills in data["Skills"]:
            keyboard.append([skills])
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)    
        await context.bot.send_message(chat_id=update.effective_chat.id, text=message, reply_markup=reply_markup)
    return SAVE_MODIFY

async def immunitiesChoice(update, context):
    if choice == "Remove":
        with open("database/campaignsDB.json") as f:
            data = json.load(f)
        for campaigns in data:
            if current_campaign == campaigns["ID"]:
                campaign = campaigns
                break
        event = campaign["events"][int(eventNumber) - 1]
        keyboard = []
        for immunities in event["Immunities"]:
            keyboard.append(immunities)
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, input_field_placeholder='Which immunity do you want to remove?')
        message = "This is the list of the immunities your monster currently has."
        await context.bot.send_message(chat_id=update.effective_chat.id, text=message, reply_markup = reply_markup)
    elif choice == "Add":
        with open("5eDefaults/monsterimmunities.json") as f:
            data = json.load(f)
        message = "These are the immunities you can add to your monster. Choose a new one."
        keyboard = []
        for skills in data["Immunities"]:
            keyboard.append([immunities])
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)    
        await context.bot.send_message(chat_id=update.effective_chat.id, text=message, reply_markup=reply_markup)
    return SAVE_MODIFY

async def resistancesChoice(update, context):
    if choice == "Remove":
        with open("database/campaignsDB.json") as f:
            data = json.load(f)
        for campaigns in data:
            if current_campaign == campaigns["ID"]:
                campaign = campaigns
                break
        event = campaign["events"][int(eventNumber) - 1]
        keyboard = []
        for resistances in event["Resistances"]:
            keyboard.append(resistances)
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, input_field_placeholder='Which resistance do you want to remove?')
        message = "This is the list of the resistances your monster currently has."
        await context.bot.send_message(chat_id=update.effective_chat.id, text=message, reply_markup = reply_markup)
    elif choice == "Add":
        with open("5eDefaults/monsterskills.json") as f:
            data = json.load(f)
        message = "These are the resistances you can add to your monster. Choose a new one."
        keyboard = []
        for resistances in data["Resistances"]:
            keyboard.append([resistances])
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)    
        await context.bot.send_message(chat_id=update.effective_chat.id, text=message, reply_markup=reply_markup)
    return SAVE_MODIFY

async def saveModify(update, context):
    modify_flag = True
    modify = update.message.text
    with open("database/campaignsDB.json") as f:
        data = json.load(f)
    for campaigns in data:
        if current_campaign == campaigns["ID"]:
            break
    if event_attribute == "Actions" or event_attribute == "Legendary Actions" or event_attribute == "Skills" or event_attribute == "Immunities" or event_attribute == "Resistances" or event_attribute == "Weapons":
        if choice == "Add":
            if isinstance(campaigns["events"][int(eventNumber) - 1], list):
                campaigns["events"][int(eventNumber) - 1][int(monsterNumber) - 1][event_attribute].add(modify)
            else:
                campaigns["events"][int(eventNumber) - 1][event_attribute].add(modify)
        elif choice == "Remove":
            if isinstance(campaigns["events"][int(eventNumber) - 1], list):
                campaigns["events"][int(eventNumber) - 1][int(monsterNumber) - 1][event_attribute].remove(modify)
            else:
                campaigns["events"][int(eventNumber) - 1][event_attribute].remove(modify)
    elif event_attribute == "Armor Class" or event_attribute == "Hit Points" or event_attribute == "Challenge" or event_attribute == "Speed":
        if modify.isdigit():
            if isinstance(campaigns["events"][int(eventNumber) - 1], list):
                campaigns["events"][int(eventNumber) - 1][int(monsterNumber) - 1][event_attribute] = int(modify)
            else:
                campaigns["events"][int(eventNumber) - 1][event_attribute] = int(modify)
        else:
            modify_flag = False
    elif event_attribute == "Ability Scores" or event_attribute == "Ability Modifiers":
        if modify.isdigit():
            if isinstance(campaigns["events"][int(eventNumber) - 1], list):
                campaigns["events"][int(eventNumber) - 1][int(monsterNumber) - 1][event_attribute][modify_ability] = int(modify)
            else:
                campaigns["events"][int(eventNumber) - 1][event_attribute][modify_ability] = int(modify)
        else:
            modify_flag = False
    elif event_attribute == "Saving Throws":
        pattern = r'^[+-]\d+$'
        if re.match(pattern, modify) != None:
            campaigns["events"][int(eventNumber) - 1][int(monsterNumber) - 1][event_attribute][modify_saving] = modify
        else:
            modify_flag = False
    else:
        if isinstance(campaigns["events"][int(eventNumber) - 1], list):
            campaigns["events"][int(eventNumber) - 1][int(monsterNumber) - 1][event_attribute] = modify
        else:
            campaigns["events"][int(eventNumber) - 1][event_attribute] = modify
    
    if modify_flag:
        message = "The value has been successfully updated. If you want to keep modifying your event choose another field."
    else:
        message = "The value you inserted is invalid, please follow the instructions and try again."

    with open("database/campaignsDB.json", "w") as f:
        json.dump(data, f, indent=4)

    if isinstance(campaigns["events"][int(eventNumber) - 1], list):
        keyboard = []
        if len(campaigns["events"][int(eventNumber) - 1]) > 1:
            for attributes in campaigns["events"][int(eventNumber) - 1][int(monsterNumber) - 1]:
                if attributes != "features" and attributes != "max_weight" and attributes != "current_weight":
                    keyboard.append([attributes])
            keyboard.append(["Finished"])
            reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, input_field_placeholder='Which field you want to modify?')
            await context.bot.send_message(chat_id=update.effective_chat.id, text=message, reply_markup = reply_markup)
            return CHOOSE_ATTRIBUTE
        else:
            for attributes in campaigns["events"][int(eventNumber) - 1][0]:
                if attributes != "features" and attributes != "max_weight" and attributes != "current_weight":
                    keyboard.append([attributes])
            keyboard.append(["Finished"])
            reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, input_field_placeholder='Which field you want to modify?')
            await context.bot.send_message(chat_id=update.effective_chat.id, text=message, reply_markup = reply_markup)
            return CHOOSE_ATTRIBUTE
    keyboard = []
    for attributes in campaigns["events"][int(eventNumber) - 1]:
        if attributes != "features" and attributes != "max_weight" and attributes != "current_weight":
            keyboard.append([attributes])
    keyboard.append(["Finished"])
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, input_field_placeholder='Which field you want to modify?')
    await context.bot.send_message(chat_id=update.effective_chat.id, text=message, reply_markup = reply_markup)
    return CHOOSE_ATTRIBUTE
# ---------------------------------- GAME PHASE ----------------------------------

async def startGameMenu(update, context):
    # Funzione che viene chiamata quando si decide di iniziare la campagna
    #TODO: Fonda da qui continua tu per la gestione della campagna attiva (inizio incontro etc). Agli user deve essere printata una tastiera di scelta con l'opzione "scrivi sul giornale della campagna" tra le altre possibilità come "Roll dice"
    if master == True:
        keyboard = [
            [InlineKeyboardButton("Modify events", callback_data=str("MODIFY_EVENTS"))],
            [InlineKeyboardButton("Modify Monster's HP", callback_data=str("MODIFY_HP"))],
            [InlineKeyboardButton("Begin with the story", callback_data=str("BEGIN_EVENTS"))],
            [InlineKeyboardButton("Modify player's level", callback_data=str("MODIFY_LEVEL"))],
            [InlineKeyboardButton("Write journal", callback_data=str("WRITE_JOURNAL"))],
            [InlineKeyboardButton("Read journal", callback_data=str("READ_JOURNAL"))],
            [InlineKeyboardButton("Info about players", callback_data=str("INFO_PLAYERS"))],
            [InlineKeyboardButton("View map", callback_data=str("VIEW_MAP"))]
            ]
        keyboard2 = [
            [InlineKeyboardButton("Upload map", callback_data=str("UPLOAD_MAP"))]

        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        reply_markup2 = InlineKeyboardMarkup(keyboard2)
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Choose an option betweeen the following: ", reply_markup = reply_markup)

        try:
            with open(f'maps/{current_campaign}.jpg', 'rb') as f:
                pass
        except FileNotFoundError:
            await context.bot.send_message(chat_id=update.effective_chat.id, text="If you didn't already upload a map, please press the following bottom: ", reply_markup = reply_markup2)
        return BEGINNING_CHOICE
    elif master == False:
        message1 = "Hello adventurer! Welcome to this amazing and insidious campaign. You will receive messages from the master soon."
        message2 = "First of all, please select the character who will play this campaign. Would you like to select an existing character or create a new one?"
        keyboard = [["Select a character"], ["Create a new character"]]
        await context.bot.send_message(chat_id=update.effective_chat.id, text=message1)
        await context.bot.send_message(chat_id=update.effective_chat.id, text=message2, reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True))
        return CHOOSE_CHARACTER
    
async def uploadNewMap(update, context):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Please send me the map you want to upload")
    return SAVE_NEW_MAP

async def saveNewMap(update, context):
    photo = update.message.photo
    largest_photo = photo[-1]
    fileID = largest_photo.file_id
    photo_file = await context.bot.get_file(largest_photo.file_id)
    
    response = requests.get(photo_file.file_path)
    os.makedirs("maps", exist_ok=True)
    kb = ["Back to the menu"]
    if response.status_code == 200:
        with open(f'maps/{current_campaign}.jpg', 'wb') as f:
            f.write(response.content)
            print('File downloaded successfully.')
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Map saved successfully.", reply_markup=ReplyKeyboardMarkup([kb], one_time_keyboard=True))
    else:
        print('Failed to download the file.')
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Failed to save the map, please try again.", reply_markup=ReplyKeyboardMarkup([kb], one_time_keyboard=True))
    return START

async def viewMap(update, context):
    try:
        with open(f'maps/{current_campaign}.jpg', 'rb') as f:
            await context.bot.send_photo(chat_id=update.effective_chat.id, photo=InputFile(f), caption=f"Here's your saved map for campaign n* {current_campaign}")
        kb = [[InlineKeyboardButton("No", callback_data=str("GAME_START"))],
              [InlineKeyboardButton("Yes", callback_data=str("NEW_MAP"))]]
        reply_markup = InlineKeyboardMarkup(kb)
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Do you want to upload a new map?", reply_markup = reply_markup)
    except FileNotFoundError:
        await context.bot.send_message(chat_id=update.effective_chat.id, text = "There is no map here, please add one first")
        await startGameMenu(update, context)
    
async def playerMenu(update, context):
    player  = update.message.text 
    keyboard = []
    kb = []
    keyboard.append(["ROLL DICE"])
    keyboard.append(["SKIP THIS EVENT"])
    keyboard.append(["INFO ABOUT MY CHARACTER"])
    keyboard.append(["WRITE JOURNAL"])
    keyboard.append(["READ JOURNAL"])
    keyboard.append(["VIEW MAP"])

    message1 = "Please wait the master to send an event before pressing any button"
    message2 =  "If you want to see your character's sheet press INFO ABOUT MY CHARACTER"

    #kb = [
    #        [InlineKeyboardButton("Write journal", callback_data=str("WRITE_JOURNAL"))]
    #]


    await context.bot.send_message(chat_id=update.effective_chat.id, text=message1)

    await context.bot.send_message(chat_id=update.effective_chat.id, text=message2, reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True))

    #await context.bot.send_message(chat_id=update.effective_chat.id, text="Do you want to write or read the journal?", reply_markup=InlineKeyboardMarkup(kb))

    return ACTION_CHOICE

async def actionChoice(update, context):
    global curr_player
    chosen_action = update.message.text 
    kb = []
    kb.append(["BACK MENU"])
    with open("database/campaignsDB.json", "r") as fp:
        data = json.load(fp)
    for campaign in data:
        if campaign["ID"] == current_campaign:
            masterID = campaign["ID_Master"]
            for player in campaign["players"]:
                if player["ID"] == update.effective_chat.id:
                    curr_player = player["ID_char"] 
                    break

    if chosen_action == "ROLL DICE":
        message = "Why would you want to roll the dice?"
        keyboard = []
        keyboard.append(["I have to fight with someone"])
        keyboard.append(["Other action"])
        await context.bot.send_message(chat_id=update.effective_chat.id, text= message, reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True))
        return ROLL_DICE

    elif chosen_action == "SKIP THIS EVENT":
        #await context.bot.send_message(chat_id=masterID, text= curr_player + "has decided to skip this event")
        #await context.bot.send_message(chat_id=update.effective_chat.id, text= curr_player + "has decided to skip this event")
        await context.bot.send_message(chat_id=update.effective_chat.id, text= "You have skipped the event", reply_markup=ReplyKeyboardMarkup(kb, one_time_keyboard=True))
        return PLAYER_ACTIONS

    elif chosen_action == "INFO ABOUT MY CHARACTER":
        message = ""
        with open ("database/campaignsDB.json", "r") as fp:
            data = json.load(fp)
        for campaign in data:
            if campaign["ID"] == current_campaign:
                    players = campaign["players"]
        for player in players:
            for att in player["ID_char"]:
                if player["ID"] == update.effective_chat.id and player["ID_char"]["name"] == curr_player_name:
                    event = att + ": " + str(player["ID_char"][att]) + "\n"
                    message = message + event
        await context.bot.send_message(chat_id=update.effective_chat.id, text=message, reply_markup=ReplyKeyboardMarkup(kb, one_time_keyboard=True))
        return PLAYER_ACTIONS
        
    elif chosen_action == "READ JOURNAL":
        kb = []
        kb.append(["CONTINUE"])
        await context.bot.send_message(chat_id=update.effective_chat.id, text="press CONTINUE to read the journal", reply_markup=ReplyKeyboardMarkup(kb, one_time_keyboard=True))
        return READ_JOURNAL
    
    elif chosen_action == "WRITE JOURNAL":
        kb = []
        kb.append(["CONTINUE"])
        await context.bot.send_message(chat_id=update.effective_chat.id, text="press CONTINUE to write", reply_markup=ReplyKeyboardMarkup(kb, one_time_keyboard=True))
        return ASK_JOURNAL

    elif chosen_action == "VIEW MAP":
        try:
            with open(f'maps/{current_campaign}.jpg', 'rb') as f:
                await context.bot.send_photo(chat_id=update.effective_chat.id, photo=InputFile(f), caption=f"Here's your saved map for campaign n* {current_campaign}")
        except FileNotFoundError:
                await context.bot.send_message(chat_id=update.effective_chat.id, text = "The master has not upload any map", reply_markup=ReplyKeyboardMarkup(kb, one_time_keyboard=True))
        return PLAYER_ACTIONS

async def chooseWeap(update, context):
    roll_type= update.message.text 
    keyboard = []
    if roll_type == "I have to fight with someone":
        message = "First of all, please select which weapon do you want to use"

        
        with open ("database/newUserDB.json", "r") as fp:
            character = json.load(fp)
        with open("5eDefaults/weapons.json", "r") as fp:
            weapons_list = json.load(fp)

        for user in character["users"]: 
            if str(update.effective_chat.id) == str(user["telegramID"]):
                for char in user["characters"]:
                    if str(char["name"]) == curr_player_name:
                        selected_char_data = char
                        weapons = selected_char_data["weapons"]

        all_weapon_names = []
        all_damage_names = []
        for item in weapons_list["simple_melee"]:
            all_weapon_names.append(item["name"])
            all_damage_names.append(item["damage"])
        for item in weapons_list["simple_ranged"]:
            all_weapon_names.append(item["name"])
            all_damage_names.append(item["damage"])
        for item in weapons_list["martial_melee"]:
            all_weapon_names.append(item["name"])
            all_damage_names.append(item["damage"])
        for item in weapons_list["martial_ranged"]:
            all_weapon_names.append(item["name"])
            all_damage_names.append(item["damage"])                    

        for weapon in weapons:
            for w_name, d_name in zip(all_weapon_names, all_damage_names):
                    if w_name == weapon:
                        keyboard.append([w_name + "-" + d_name])

        await context.bot.send_message(chat_id=update.effective_chat.id, text=message, reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True))
        return ROLL_FIGHT

                    
    elif roll_type == "Other action" or roll_type == "continue":
        message1 = "In the text sent by the master he specified the dice type and how many times you have to roll it to complete the task. Please be honest and don't roll the dice extra times and don't choose the wrong dice!"
        message2 = "Choose the dice"
        keyboard.append(["d4"])
        keyboard.append(["d6"])
        keyboard.append(["d8"])
        keyboard.append(["d10"])
        keyboard.append(["d12"])
        keyboard.append(["d20"])
        keyboard.append(["STOP ROLLING"])
        await context.bot.send_message(chat_id=update.effective_chat.id, text=message1)
        await context.bot.send_message(chat_id=update.effective_chat.id, text=message2, reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True))
        return ROLL_TASK
          
async def rollDiceFight(update, context):
    choice = update.message.text
    #weapon=choice.split("-")[0]
    kb = []
    kb.append(["BACK MENU"])
    dice=choice.split("-")[1]
    rolls=(dice[0])
    n = int(rolls)
    dice_num=dice[1:].split(" ")[0]

    while(n > 0):
        if dice_num == "d4":
            number = random.randint(1, 4)
        elif dice_num == "d6":
            number = random.randint(1, 6)
        elif dice_num == "d8":
            number = random.randint(1, 8)
        elif dice_num == "d10":
            number = random.randint(1, 10)
        elif dice_num == "d12":
            number = random.randint(1, 12)
        elif dice_num == "d20":
            number = random.randint(1, 20)

        n-=1
    str_number = str(number)
    #await context.bot.send_message(master=masterID, text= curr_player + "rolled the dice and scored: " + str_number)
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Soon the master will tell you if the opponent has been defeated", reply_markup=ReplyKeyboardMarkup(kb, one_time_keyboard=True))
    return PLAYER_ACTIONS

async def rollDiceTask(update, context):
    dice = update.message.text 
    keyboard = []
    keyboard.append(["continue"])
    if dice == "d4":
        number = random.randint(1, 4)
        print(number)
        await context.bot.send_message(chat_id=update.effective_chat.id, text="You rolled the dice and scored: " + str(number))
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Press continue and choose what to do now", reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True))
        #await context.bot.send_message(chat_id=masterID, text="You rolled the dice and scored: " + str(number))
        return ROLL_DICE
    elif dice== "d6":
        number = random.randint(1, 6)
        print(number)
        await context.bot.send_message(chat_id=update.effective_chat.id, text="You rolled the dice and scored: " + str(number))
        #await context.bot.send_message(chat_id=masterID, text="You rolled the dice and scored: " + str(number))
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Press continue and choose what to do now", reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True))
        return ROLL_DICE
    elif dice == "d8":
        number = random.randint(1, 8)
        print(number)
        await context.bot.send_message(chat_id=update.effective_chat.id, text="You rolled the dice and scored: " + str(number))
        #await context.bot.send_message(chat_id=masterID, text="You rolled the dice and scored: " + str(number))
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Press continue and choose what to do now", reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True))
        return ROLL_DICE
    elif dice == "d10":
        number = random.randint(1, 10)
        print(number)
        await context.bot.send_message(chat_id=update.effective_chat.id, text="You rolled the dice and scored: " + str(number))
        #await context.bot.send_message(chat_id=masterID, text="You rolled the dice and scored: " + str(number))
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Press continue and choose what to do now", reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True))
        return ROLL_DICE
    elif dice == "d12":
        number = random.randint(1, 12)
        print(number)
        await context.bot.send_message(chat_id=update.effective_chat.id, text="You rolled the dice and scored: " + str(number))
        #await context.bot.send_message(chat_id=masterID, text="You rolled the dice and scored: " + str(number))
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Press continue and choose what to do now", reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True))
        return ROLL_DICE
    elif dice == "d20":
        number = random.randint(1, 20)
        print(number)
        await context.bot.send_message(chat_id=update.effective_chat.id, text="You rolled the dice and scored: " + str(number))
        #await context.bot.send_message(chat_id=masterID, text="You rolled the dice and scored: " + str(number))
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Press continue and choose what to do now", reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True))
        return ROLL_DICE
    elif dice == "STOP ROLLING":
        kb = []
        kb.append(["BACK MENU"])
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Soon the master will tell you if the task has been completed", reply_markup = ReplyKeyboardMarkup(kb, one_time_keyboard=True) )


async def chooseCharToMod(update, context):
    print("hello")
    callback_data = update.callback_query.data
    if callback_data == "MODIFY_LEVEL":
        with open("database/campaignsDB.json", "r") as f:
            data = json.load(f)

        keyboard = []
        for campaign in data:
            if campaign["ID"] == current_campaign:
                players = campaign["players"]
        for player in players:
            for att in player["ID_char"]:
                if att == "name":
                    name = player["ID_char"]["name"]
                if att == "level":
                    level = player["ID_char"]["level"]
            if player["ID_char"] != "":
                keyboard.append([str(name) + " - level: " + str(level)])
                await context.bot.send_message(chat_id=update.effective_chat.id, text="Choose a player to modify his level", reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True))
                return MODIFY_LEVEL
            else:
                keyboard = [
                    [InlineKeyboardButton("Back menu", callback_data=str("GAME_START"))]
                ]  
                await context.bot.send_message(chat_id=update.effective_chat.id, text="No players available", reply_markup=InlineKeyboardMarkup(keyboard))
                ConversationHandler.END
        
    elif callback_data == "RETURN":
        keyboard = [
            [InlineKeyboardButton("Back to menu", callback_data=str("GAME_START"))]
            ]   
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Now you can return to the main menu", reply_markup=InlineKeyboardMarkup(keyboard))
        ConversationHandler.END

async def modifyLevel(update, context):
    chosen_player = update.message.text 
    player_name = chosen_player.split("-")[0]
    with open("database/campaignsDB.json", "r") as f:
            data = json.load(f)
    for campaign in data:
        if campaign["ID"] == current_campaign:
            players = campaign["players"]
    for player in players:
        for att in player["ID_char"]:
            if att == "level":
                player["ID_char"]["level"] += 1

    with open("database/campaignsDB.json", "w") as f:
        json.dump(data, f, indent=4)

    #keyboard = [
    #        [InlineKeyboardButton("Modify another player's level", callback_data=str("MODIFY_LEVEL"))],
    #        [InlineKeyboardButton("Back to main menu", callback_data=str("RETURN"))]]
    
    keyboard = [
        [InlineKeyboardButton("Back menu", callback_data=str("GAME_START"))]
    ]   
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Level increased! Now you can return to the main menu", reply_markup=InlineKeyboardMarkup(keyboard))
    #await context.bot.send_message(chat_id=playerID, text="Well done! You have just increased your level! Use the command /abil to improve your skills")
    ConversationHandler.END  

    
async def chooseNewHP(update, context):
    chosen_monster = update.message.text 
    global tmp_mon
    tmp_mon = chosen_monster
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Please insert the new HP value")
    return MODIFY_HP

async def modifyHP(update, context):
    hit_points = update.message.text
    if hit_points.isdigit():
        with open("database/campaignsDB.json", "r") as f:
            data = json.load(f)
        for campaign in data:
            if campaign["ID"] == current_campaign:
                events = campaign["events"]
        for event in events:
            for att in event:
                if att["Name"] == tmp_mon:
                    att["Hit Points"] = int(hit_points) 
                    print(att["Hit Points"]) 

        with open("database/campaignsDB.json", "w") as f:
            json.dump(data, f, indent = 4)
        await context.bot.send_message(chat_id=update.effective_chat.id, text= "Monster's HP has been modified")   
        keyboard = [
            [InlineKeyboardButton("Back menu", callback_data=str("GAME_START"))]
        ]   
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Now you can return to the main menu", reply_markup=InlineKeyboardMarkup(keyboard))
        ConversationHandler.END   
        #await startGameMenu(update, context)
        #return ConversationHandler.END
    
    else:
        message = "The value you chose is not valid, you must choose a number!"
        await context.bot.send_message(chat_id=update.effective_chat.id, text=message)
        return MODIFY_HP
    
async def HP(update, context):
    callback_data = update.callback_query.data
    if callback_data == "MODIFY_HP":
        message = "These are the monsters that you added to your campaign. Select which one you want to modify"
        with open("database/campaignsDB.json", "r") as f:
            data = json.load(f)
        keykey = []
        for campaign in data:
            if campaign["ID"] == current_campaign:
                events = campaign["events"]
        for event in events:
            for att in event:
                if att["Type"] == "Monster":
                    keykey.append([att["Name"]])
        reply_markup = ReplyKeyboardMarkup(keykey, one_time_keyboard=True)
        await context.bot.send_message(chat_id=update.effective_chat.id, text=message, reply_markup = reply_markup)
        return CHOOSE_NEWHP

async def startEvents(update, context):
    #Funzione che viene chiamata subito dopo che il master ha scelto quale azione intraprendere (corrisponde allo stato BEGINNING_CHOICE)
    callback_data = update.callback_query.data
    if callback_data == "MODIFY_EVENTS":
        print("modify event")
    elif callback_data == "MODIFY_HP":
        print("meglio ora 0")
    elif callback_data == "BEGIN_EVENTS":
        message = "What kind of event will the players interfaced with? "
        keyboard = [
            [InlineKeyboardButton("Event interaction", callback_data=str("EVENT_INT"))],
            [InlineKeyboardButton("Other info", callback_data=str("OTHER_INFO"))]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await context.bot.send_message(chat_id=update.effective_chat.id, text=message, reply_markup = reply_markup)
        return CREATE_SEND
    elif callback_data == "UPLOAD_MAP":
        with open("database/campaignsDB.json", "r") as f:
            data = json.load(f)
        for campaign in data:
            if campaign["ID"] == current_campaign:
                campaignName = campaign["name"]
        keyboard = []
        message = "Press the name of your campaign on the keyboard to upload the map"
        keyboard.append([campaignName])
        await context.bot.send_message(chat_id=update.effective_chat.id, text = message, reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True))
        return UPLOAD_MAP

async def createEventToSend(update, context):
    callback_data = update.callback_query.data
    message = ""
    if callback_data == "EVENT_INT":
        with open("database/campaignsDB.json", "r") as f:
            data = json.load(f)
        for campaigns in data:
            if current_campaign == campaigns["ID"]:
                campaign = campaigns
                break
        for events in campaign["events"]:
            if isinstance(events, list):
                for event in events:
                    for key, value in event.items():
                        message = message + f"{key}: {value}\n"
                    message = message + "\n"
                await context.bot.send_message(chat_id=update.effective_chat.id, text=message)
            else:
                for key, value in events.items():
                    message = message + f"{key}: {value}\n"
                await context.bot.send_message(chat_id=update.effective_chat.id, text=message)

    elif callback_data == "OTHER_INFO":
        print("other info")
    await context.bot.send_message(chat_id = update.effective_chat.id, text = "Now please write an event for the players. Explain what is about to happen: for example it could be a battle with a monster, a meeting with a NPC or a contagion. ")
    return SEND_EVENT

async def sendEvent(update, context):
    event = update.message.text
    with open("database/campaignsDB.json", "r") as f:
        data = json.load(f)
    for campaign in data:
        if campaign["ID"] == current_campaign:
            players = campaign["players"]  
    for player in players:
        playerID = player["ID"]
        #await context.bot.send_message(chat_id = playerID, text = event)
    await context.bot.send_message(chat_id = update.effective_chat.id, text = "Event sent!")
    keyboard = [
        [InlineKeyboardButton("Back to menu", callback_data=str("GAME_START"))]
        ]   
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Now you can return to the main menu", reply_markup=InlineKeyboardMarkup(keyboard))
    ConversationHandler.END
    #await startGameMenu(update, context)
    #return ConversationHandler.END

async def infoPlayers(update, context):
    callback_data = update.callback_query.data
    if callback_data == "INFO_PLAYERS":
        with open("database/campaignsDB.json", "r") as f:
            data = json.load(f)

        keyboard = []
        for campaign in data:
            if campaign["ID"] == current_campaign:
                players = campaign["players"]
        for player in players:
            for att in player["ID_char"]:
                if att == "name":
                    name = player["ID_char"]["name"]
            if player["ID_char"] != "":
                keyboard.append([str(name)])
        if keyboard:
            await context.bot.send_message(chat_id=update.effective_chat.id, text="Select a player to view its info", reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True))
            return PRINT_INFO
        else:
            await context.bot.send_message(chat_id=update.effective_chat.id, text="No players in this campaign")
            keyboard = [
            [InlineKeyboardButton("Back to menu", callback_data=str("GAME_START"))]
            ]   
            await context.bot.send_message(chat_id=update.effective_chat.id, text="Now you can return to the main menu", reply_markup=InlineKeyboardMarkup(keyboard))
            ConversationHandler.END
    
async def printInfo(update, context):
    choice = update.message.text
    message = "" 
    with open ("database/campaignsDB.json", "r") as fp:
        data = json.load(fp)
    for campaign in data:
        if campaign["ID"] == current_campaign:
                players = campaign["players"]
    for player in players:
        for att in player["ID_char"]:
            if player["ID_char"]["name"] == choice:
                event = att + ": " + str(player["ID_char"][att]) + "\n"
                message = message + event
    await context.bot.send_message(chat_id=update.effective_chat.id, text=message)

    keyboard = [
            [InlineKeyboardButton("Back to menu", callback_data=str("GAME_START"))]
            ]   
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Now you can return to the main menu", reply_markup=InlineKeyboardMarkup(keyboard))
    ConversationHandler.END

# ---------------------------------- CLASS SPECIFIC FEATURES ----------------------------------
async def checkForClassFeatures(update, context):
    """This function is called each time a character gains a level. It checks if the character has gained any new class abilities and, if so, it prompts the user the necessary information to add them to the character sheet."""

    global current_campaign
    with open("database/campaignsDB.json", "r") as fp:
        data = json.load(fp)
    playerCharacter = {}
    for campaign in data:
        if campaign["ID"] == current_campaign:
            for player in campaign["players"]:
                if str(player["ID"]) == str(update.effective_chat.id):
                    playerCharacter = player["ID_char"]
                    break
            break

    char_level = playerCharacter["level"]
    char_abilities = {}
    char_abilities = playerCharacter["ability_scores"]
    char_class = playerCharacter["class"]
    #check if the character has gained any new class features
    with open("5eDefaults/classes.json", "r") as fp:
        classData = json.load(fp)
    if str(char_level) in classData[char_class]["levels"]:
        level_data = classData[char_class]["levels"][str(char_level)]
    if "features" in level_data and isinstance(level_data["features"], list):
        for feature in level_data["features"]:
            if str(feature["id"]) == "asi": #Ability score improvement (ASI) requires further action different from the other abilities
                message = "With the level up you gained an Ability Score Improvement!" + "\nYou can choose to increase one ability score of your choice by 2 or two ability scores of your choice by 1." + "\nWhich one do you want to choose?"
                keyboard = []
                for abilita, valore in char_abilities.items():
                    row = []
                    row.append(InlineKeyboardButton(f"{abilita} - {valore}", callback_data=f"{abilita}:{valore}"))
                    row.append(InlineKeyboardButton("+", callback_data="increase-" + f"{abilita}"))
                    keyboard.append(row)
                reply_markup = InlineKeyboardMarkup(keyboard)
                await context.bot.send_message(chat_id=update.effective_chat.id, text=message, reply_markup=reply_markup)
                return ASI	
            elif "options" not in feature or feature["options"] is None: #The feature does not require any further action
                check = await saveFeature(update, context, feature)
                if not check:
                    print("Error while saving the feature")
                message = "You gained a new feature!" + "\nName: " + feature["display_name"] + "\nDescription: " + feature["description"]
                await context.bot.send_message(chat_id=update.effective_chat.id, text=message)	
            else:
                message = "You gained a new feature!" + "\nName: " + feature["display_name"] + "\nDescription: " + feature["description"]
                keyboard = []
                for option in feature["options"]:
                    message += "\n- " + option["display_name"] + ": " + option["description"]
                    keyboard.append([InlineKeyboardButton(option["display_name"], callback_data=feature["display_name"]+"-"+option["display_name"])])
                await context.bot.send_message(chat_id=update.effective_chat.id, text=message, reply_markup=InlineKeyboardMarkup(keyboard))
                return FEATURE_CHOOSE_OPTION
                
async def asiKB(update, context):
    """This function is called when the user has to choose which ability score to increase with the Ability Score Improvements."""
    query = update.callback_query
    data = query.data
    secondPoint = False
    global current_campaign

    if data.split("-")[1].split(".")[0] == "X":
        data = "increase-" + data.split("-")[1].split(".")[1]	
        secondPoint = True

    if data.split("-")[0] == "increase":
        ability = data.split("-")[1]
        with open("database/campaignsDB.json", "r") as fp:
            campaignData = json.load(fp)
        for campaign in campaignData:
            
            if int(campaign["ID"]) == int(current_campaign):
                for player in campaign["players"]:
                    if str(player["ID"]) == str(update.effective_chat.id):
                        playerCharacter = {}
                        playerCharacter = player["ID_char"]
                        break
                break
        
        char_abilities = {}
        char_abilities = playerCharacter["ability_scores"]
        valore = char_abilities[ability]
        if valore >= 20:
            remainingPoints = 2
            if secondPoint:
                remainingPoints = 1
            message = "Adventurer, you cannot increase " + ability + " ability score any further!" + "\nYou still have " + str(remainingPoints) + " points to spend."
            keyboard = []
            for abilita, valore in char_abilities.items():
                row = []
                row.append(InlineKeyboardButton(f"{abilita} - {valore}", callback_data=f"X.{abilita}:{valore}")) #This is the only difference from the previous keyboard
                row.append(InlineKeyboardButton("+", callback_data="increase-" + f"X.{abilita}"))
                keyboard.append(row)
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.answer()
            await query.edit_message_text(text=message, reply_markup=reply_markup)
            return ASI
        
        valore += 1
        char_abilities[ability] = valore
        
        if not secondPoint:
            with open("database/campaignsDB.json", "w") as fp:
                json.dump(campaignData, fp)
            message = "With the level up you gained an Ability Score Improvement!" + "\nYou can choose to increase one ability score of your choice by 2 or two ability scores of your choice by 1." + "\nWhich one do you want to choose?"
            keyboard = []
            for abilita, valore in char_abilities.items():
                row = []
                row.append(InlineKeyboardButton(f"{abilita} - {valore}", callback_data=f"X.{abilita}:{valore}")) #This is the only difference from the previous keyboard
                row.append(InlineKeyboardButton("+", callback_data="increase-" + f"X.{abilita}"))
                keyboard.append(row)
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.answer()
            await query.edit_message_text(text=message, reply_markup=reply_markup)
        else:
            message = "You updated your Abilities!"
            #Recalculate the modifiers
            ability_modifiers = {
                ability: (score - 10) // 2 for ability, score in char_abilities.items()
            }
            playerCharacter["ability_modifiers"] = ability_modifiers
            with open("database/campaignsDB.json", "w") as fp:
                json.dump(campaignData, fp)
            await query.edit_message_text(text=message)
    else:
        pass
    return ASI

async def featureChooseOption(update, context):
    """This function is called when the user has to choose an option for a feature."""
    query = update.callback_query
    feature = query.data.split("-")[0]
    option = query.data.split("-")[1]
    check = await saveFeature(update, context, feature, option)
    if not check:
        print("Error while saving the feature")
    message = "You chose: " + option     
    await context.bot.send_message(chat_id=update.effective_chat.id, text=message)
    return ConversationHandler.END	#TODO:non sono sicuro che funzioni benissimo se c'è un'altra feature da scegliere

async def saveFeature(update, context, feature, option=None):
    """This function saves the feature in the database."""
    with open("database/campaignsDB.json", "r") as fp:
        data = json.load(fp)

    for campaign in data:
        if campaign["ID"] == current_campaign:
            for player in campaign["players"]:
                if str(player["ID"]) == str(update.effective_chat.id):
                    if "features" not in player["ID_char"]:
                        player["ID_char"]["features"] = []
                    if option is not None:
                        player["ID_char"]["features"].append({"name": feature, "option": option})
                    else:
                        player["ID_char"]["features"].append({"name": feature["display_name"]})
                    break
            break
   
    with open("database/campaignsDB.json", "w") as fp:
        json.dump(data, fp)
    return True

if __name__ == "__main__":
    botSetup()

